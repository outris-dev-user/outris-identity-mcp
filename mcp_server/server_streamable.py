"""
FastAPI Streamable HTTP + SSE Transport for Outris MCP Server

Implements both:
1. Streamable HTTP (stateless, new MCP spec standard)
2. SSE (backward compatibility)
3. Tool list endpoint (public discovery)
"""
import logging
import json
import asyncio
from typing import Any, Callable, AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from mcp.server.sse import SseServerTransport
from mcp.server import Server
from mcp.types import Tool, TextContent

from .core.config import get_settings
from .core.database import Database
from .core.auth import validate_api_key, AuthError
from .mcp_server import OutrisMCPServer
from .tools.registry import ToolRegistry, execute_tool

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

settings = get_settings()

# Import tools to register them
if settings.enable_kyc_tools:
    from .tools import kyc
from .tools import platforms, commerce, investigation


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info("Starting Outris MCP Server (Streamable HTTP + SSE)...")
    await Database.connect()
    logger.info(f"Registered tools: {list(ToolRegistry.get_all().keys())}")

    yield

    logger.info("Shutting down...")
    await Database.disconnect()
    from .tools.helpers import close_http_client
    await close_http_client()


# Create FastAPI app
app = FastAPI(
    title="Outris MCP Server",
    description="Model Context Protocol server for identity verification (Streamable HTTP + SSE)",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Public Endpoints (No Auth)
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint - server info."""
    return {
        "server": "outris-mcp-server",
        "version": "2.0.0",
        "mcp_version": "2024-11-05",
        "status": "ready",
        "transports": {
            "streamable_http": "/http",
            "sse": "/sse",
            "stdio": "python -m mcp_server"
        },
        "endpoints": {
            "health": "/health",
            "tools": "/tools"
        },
        "docs": "https://portal.outris.com/mcp"
    }


@app.get("/health")
async def health():
    """Health check - no auth required."""
    return {
        "status": "healthy",
        "server": "outris-mcp-server",
        "version": "2.0.0",
        "transport": "streamable-http+sse",
        "tools_count": len(ToolRegistry.get_enabled())
    }


@app.get("/tools")
async def list_tools():
    """List available tools - no auth required (public discovery)."""
    tools = {}
    for name, tool_def in ToolRegistry.get_all().items():
        tools[name] = {
            "description": tool_def.description,
            "input_schema": tool_def.inputSchema,
            "requires_auth": name not in ["platform_check", "check_whatsapp"]
        }
    return {
        "total": len(tools),
        "tools": tools,
        "public_tools": ["platform_check", "check_whatsapp"],
        "note": "Use /http or /sse for tool execution"
    }


# ============================================================================
# Streamable HTTP Transport (NEW - Primary Transport)
# ============================================================================

@app.get("/http")
async def streamable_http_discovery():
    """
    Discovery/Probe endpoint for Streamable HTTP.
    
    Some clients (like mcp-remote) may probe the endpoint with GET 
    to verify it exists and is accessible.
    """
    return {
        "status": "active",
        "transport": "streamable-http",
        "message": "Use POST requests for JSON-RPC tool execution."
    }


@app.post("/http")
async def streamable_http_transport(
    request: Request,
    authorization: str | None = Header(None)
):
    """
    Streamable HTTP transport endpoint (stateless).
    
    This is the new MCP spec standard transport for cloud deployments.
    Each request is independent (no persistent connection needed).
    
    Request format (JSON-RPC 2.0):
    {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/list" | "tools/call",
        "params": {...}
    }
    
    Response format (newline-delimited JSON):
    {"jsonrpc":"2.0","id":1,"result":{...}}
    """
    
    async def response_generator() -> AsyncIterator[bytes]:
        """Generate streaming JSON-RPC responses."""
        try:
            # Parse request body
            try:
                body = await request.json()
            except Exception as e:
                logger.error(f"Invalid JSON: {e}")
                yield json.dumps({
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32700,
                        "message": "Parse error",
                        "data": str(e)
                    }
                }).encode() + b"\n"
                return

            request_id = body.get("id")
            method = body.get("method")
            params = body.get("params", {})

            logger.info(f"[HTTP] Method: {method}, ID: {request_id}")

            # ====================================================================
            # Method: initialize (Handshake)
            # ====================================================================
            if method == "initialize":
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {
                            "tools": {} # We expose tools
                        },
                        "serverInfo": {
                            "name": "outris-mcp-server",
                            "version": "2.0.0"
                        }
                    }
                }
                logger.info(f"[HTTP] Initialized")
                yield json.dumps(response).encode() + b"\n"

            # ====================================================================
            # Method: notifications/initialized
            # ====================================================================
            elif method == "notifications/initialized":
                # client acknowledging initialization
                logger.info(f"[HTTP] Client initialized notification")
                # No response needed for notifications, but if client sends ID, sending empty result is safe/polite
                if request_id is not None:
                     yield json.dumps({
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {}
                    }).encode() + b"\n"

            # ====================================================================
            # Method: ping
            # ====================================================================
            elif method == "ping":
                yield json.dumps({
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {}
                }).encode() + b"\n"

            # ====================================================================
            # Method: tools/list (Public - no auth)
            # ====================================================================
            elif method == "tools/list":
                try:
                    tools = []
                    for name, tool_def in ToolRegistry.get_enabled().items():
                        tools.append({
                            "name": name,
                            "description": tool_def.description,
                            "inputSchema": tool_def.inputSchema
                        })

                    response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {"tools": tools}
                    }
                    logger.info(f"[HTTP] tools/list: {len(tools)} tools returned")
                    yield json.dumps(response).encode() + b"\n"

                except Exception as e:
                    logger.error(f"tools/list error: {e}", exc_info=True)
                    response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {
                            "code": -32603,
                            "message": "Internal error",
                            "data": str(e)
                        }
                    }
                    yield json.dumps(response).encode() + b"\n"

            # ====================================================================
            # Method: tools/call (Requires auth)
            # ====================================================================
            elif method == "tools/call":
                try:
                    # Extract tool name and arguments
                    tool_name = params.get("name")
                    arguments = params.get("arguments", {})

                    if not tool_name:
                        raise ValueError("Tool name required in params.name")

                    # Validate API key from header
                    if not authorization:
                        logger.warning(f"[HTTP] Unauthorized tools/call attempt (no auth)")
                        response = {
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "error": {
                                "code": 401,
                                "message": "Unauthorized",
                                "data": "Authorization header required (Bearer <api_key>)"
                            }
                        }
                        yield json.dumps(response).encode() + b"\n"
                        return

                    # Parse Bearer token
                    if not authorization.startswith("Bearer "):
                        raise AuthError("Invalid Authorization header format")

                    api_key = authorization.replace("Bearer ", "")

                    # Validate and get account
                    account = await validate_api_key(api_key)
                    logger.info(f"[HTTP] Authenticated as: {account.client_name}")

                    # Execute tool
                    logger.info(f"[HTTP] Executing tool: {tool_name}")
                    result = await execute_tool(
                        tool_name=tool_name,
                        arguments=arguments,
                        account=account,
                        request_id=str(request_id)
                    )

                    response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": result
                    }
                    logger.info(f"[HTTP] {tool_name} executed successfully")
                    yield json.dumps(response).encode() + b"\n"

                except AuthError as e:
                    logger.warning(f"[HTTP] Auth error: {e}")
                    response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {
                            "code": 401,
                            "message": "Unauthorized",
                            "data": str(e)
                        }
                    }
                    yield json.dumps(response).encode() + b"\n"

                except ValueError as e:
                    logger.error(f"[HTTP] Validation error: {e}")
                    response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {
                            "code": -32602,
                            "message": "Invalid params",
                            "data": str(e)
                        }
                    }
                    yield json.dumps(response).encode() + b"\n"

                except Exception as e:
                    logger.error(f"[HTTP] Execution error: {e}", exc_info=True)
                    response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {
                            "code": -32603,
                            "message": "Internal error",
                            "data": str(e)
                        }
                    }
                    yield json.dumps(response).encode() + b"\n"

            # ====================================================================
            # Unknown method
            # ====================================================================
            else:
                logger.warning(f"[HTTP] Unknown method: {method}")
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32601,
                        "message": "Method not found"
                    }
                }
                yield json.dumps(response).encode() + b"\n"

        except Exception as e:
            logger.error(f"[HTTP] Unexpected error: {e}", exc_info=True)
            yield json.dumps({
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": "Internal error",
                    "data": str(e)
                }
            }).encode() + b"\n"

    return StreamingResponse(
        response_generator(),
        media_type="application/json"
    )


# ============================================================================
# SSE Transport (OPTIONAL - Backward Compatibility)
# ============================================================================

@app.get("/sse")
async def sse_transport(request: Request, authorization: str | None = Header(None)):
    """
    SSE transport endpoint (legacy - backward compatibility).
    
    This maintains a persistent connection using Server-Sent Events.
    Kept for backward compatibility with existing clients.
    New clients should use /http (Streamable HTTP).
    """
    try:
        # Validate API key if provided
        account = None
        if authorization:
            if not authorization.startswith("Bearer "):
                raise AuthError("Invalid Authorization header format")
            api_key = authorization.replace("Bearer ", "")
            account = await validate_api_key(api_key)

        logger.info(f"SSE connection established")

        # Create MCP server instance
        mcp_server = OutrisMCPServer()
        mcp_server.current_account = account

        # Create SSE transport
        sse = SseServerTransport(request.url.path)

        async def handle_sse() -> AsyncIterator[bytes]:
            """Handle SSE connection (async generator)."""
            try:
                async with sse.lifespan() as streams:
                    logger.info("SSE transport lifespan started")
                    await mcp_server.server.run(
                        streams[0],
                        streams[1],
                        mcp_server.server.create_initialization_options()
                    )
            except Exception as e:
                logger.error(f"SSE error: {e}", exc_info=True)
                yield b"event: error\n"
                yield f"data: {json.dumps({'error': str(e)})}\n\n".encode()

        return StreamingResponse(
            handle_sse(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )

    except AuthError as e:
        logger.warning(f"SSE auth error: {e}")
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        logger.error(f"SSE setup error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to establish SSE connection")


# ============================================================================
# Startup/Shutdown
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
