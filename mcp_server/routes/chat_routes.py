"""
MCP AI Chat Routes - Integrated Implementation

Uses standard Anthropic tool use with agentic loop.
Claude selects tools, we execute them using the LOCAL Tool Registry.
"""
import os
import json
import logging
import httpx
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ..core.database import Database
from ..core.config import get_settings
from ..tools.registry import ToolRegistry, execute_tool

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/ai-chat", tags=["AI Chat"])

# Anthropic client
_anthropic_client = None

def get_anthropic_client():
    """Get or create Anthropic client."""
    global _anthropic_client
    if _anthropic_client is None:
        try:
            from anthropic import Anthropic
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY not configured")
            _anthropic_client = Anthropic(api_key=api_key)
        except ImportError:
            raise HTTPException(500, "Anthropic SDK not installed or configured")
        except Exception as e:
            raise HTTPException(500, f"Anthropic client error: {e}")
    return _anthropic_client


# ============================================================================
# Tool Handlers
# ============================================================================

def get_anthropic_tools():
    """Get tools in Anthropic format."""
    mcp_tools = ToolRegistry.to_mcp_format()
    # Convert 'inputSchema' to 'input_schema' for Anthropic
    anthropic_tools = []
    for t in mcp_tools:
        tool = t.copy()
        if "inputSchema" in tool:
            tool["input_schema"] = tool.pop("inputSchema")
        anthropic_tools.append(tool)
    return anthropic_tools


# ============================================================================
# Agentic Loop
# ============================================================================

async def run_agentic_loop(
    user_message: str,
    api_key: str = None, # Not used for local execution but kept for signature compat
    max_iterations: int = 5
) -> tuple[str, List[str], int]:
    """
    Run the agentic tool-use loop.
    
    Returns: (final_response, tools_used, total_credits)
    """
    client = get_anthropic_client()
    tools = get_anthropic_tools()
    
    messages = [{"role": "user", "content": user_message}]
    tools_used = []
    total_credits = 0
    
    system_prompt = """You are an identity verification and fraud investigation assistant powered by Outris.

You help users verify identities, check phone numbers for fraud signals, and investigate digital footprints.

When investigating:
1. Use the available tools to gather information
2. Be thorough but efficient - don't call unnecessary tools
3. Explain what you found clearly in plain language
4. Highlight any fraud signals or risk indicators
5. Provide actionable insights

If the user asks about a phone number or identity, USE THE TOOLS to get real data. Don't make up information."""

    for iteration in range(max_iterations):
        logger.info(f"Agentic loop iteration {iteration + 1}")
        
        response = client.messages.create(
            model="claude-sonnet-4-latest", # Updated to valid model name
            max_tokens=2048,
            system=system_prompt,
            tools=tools,
            messages=messages
        )
        
        # Check if we need to process tool calls
        if response.stop_reason == "tool_use":
            # Process each tool use block
            tool_results = []
            
            for block in response.content:
                if block.type == "tool_use":
                    tool_name = block.name
                    tool_input = block.input
                    tool_use_id = block.id
                    
                    logger.info(f"Executing tool: {tool_name} with input: {tool_input}")
                    
                    try:
                        # Execute the tool LOCALLY using Registry
                        result, _ = await execute_tool(tool_name, tool_input)
                        
                        # Calculate credits (from Registry definition)
                        tool_def = ToolRegistry.get(tool_name)
                        credits = tool_def.credits if tool_def else 1
                        
                        # Track usage
                        tools_used.append(tool_name)
                        total_credits += credits
                        
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_use_id,
                            "content": json.dumps(result, default=str)
                        })
                    except Exception as e:
                        logger.error(f"Tool execution error: {e}")
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_use_id,
                            "content": json.dumps({"error": str(e)})
                        })

            # Add assistant response and tool results to messages
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})
            
        else:
            # No more tool calls, extract final text response
            final_text = ""
            for block in response.content:
                if hasattr(block, "text"):
                    final_text += block.text
            
            return final_text, tools_used, total_credits
    
    # Max iterations reached
    return "I wasn't able to complete the investigation. Please try a more specific query.", tools_used, total_credits


# ============================================================================
# Request/Response Models
# ============================================================================

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    tools_used: List[str]
    credits_used: int
    credits_remaining: int


# ============================================================================
# JWT Auth
# ============================================================================

async def get_current_user(authorization: str = None) -> dict:
    """Validate JWT token and return user info."""
    import jwt
    
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid Authorization header format")
    
    token = authorization[7:]
    settings = get_settings()
    jwt_secret = settings.jwt_secret_key
    
    if not jwt_secret:
        raise HTTPException(status_code=500, detail="Authentication not configured")
    
    try:
        payload = jwt.decode(token, jwt_secret, algorithms=["HS256"])
        email = payload.get("email") or payload.get("sub")
        if not email:
            raise HTTPException(status_code=401, detail="Invalid token: missing email")
        
        return {"email": email.lower()}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail="Invalid token")


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/chat", response_model=ChatResponse)
async def chat(request: Request, body: ChatRequest):
    """
    AI Chat endpoint with tool use.
    
    Claude selects and uses tools, we execute them against local registry.
    """
    auth_header = request.headers.get("Authorization", "")
    user = await get_current_user(auth_header)
    
    # Get user's MCP account and credits
    mcp_info = await Database.fetchrow(
        """
        SELECT id, credits_balance
        FROM mcp.user_accounts
        WHERE user_email = $1 AND is_active = true
        """,
        user["email"]
    )
    
    if not mcp_info:
        raise HTTPException(400, "MCP not enabled. Please enable MCP access first.")
    
    if mcp_info["credits_balance"] <= 0:
        raise HTTPException(400, "Insufficient credits.")
    
    try:
        # Run the agentic loop
        response_text, tools_used, credits_used = await run_agentic_loop(
            user_message=body.message
        )
        
        # Deduct credits
        if credits_used > 0:
            await Database.execute(
                """
                UPDATE mcp.user_accounts 
                SET credits_balance = credits_balance - $1
                WHERE user_email = $2
                """,
                credits_used, user["email"]
            )
        
        # Get updated balance
        new_balance = await Database.fetchval(
            "SELECT credits_balance FROM mcp.user_accounts WHERE user_email = $1",
            user["email"]
        )
        
        return ChatResponse(
            response=response_text,
            tools_used=tools_used,
            credits_used=credits_used,
            credits_remaining=new_balance or 0
        )
        
    except Exception as e:
        logger.error(f"AI Chat error: {e}")
        raise HTTPException(500, f"AI Chat error: {str(e)}")


@router.post("/stream")
async def chat_stream(request: Request, body: ChatRequest):
    """
    Streaming version - streams the final response after tool execution.
    """
    auth_header = request.headers.get("Authorization", "")
    user = await get_current_user(auth_header)
    
    mcp_info = await Database.fetchrow(
        """
        SELECT id, credits_balance
        FROM mcp.user_accounts
        WHERE user_email = $1 AND is_active = true
        """,
        user["email"]
    )
    
    if not mcp_info:
        raise HTTPException(400, "MCP not enabled.")
    
    if mcp_info["credits_balance"] <= 0:
        raise HTTPException(400, "Insufficient credits.")
    
    async def generate():
        try:
            # Send "thinking" status
            yield f"data: {json.dumps({'type': 'status', 'message': 'Analyzing your request...'})}\n\n"
            
            response_text, tools_used, credits_used = await run_agentic_loop(
                user_message=body.message
            )
            
            # Send tools used
            if tools_used:
                yield f"data: {json.dumps({'type': 'tools', 'tools': tools_used})}\n\n"
            
            # Stream the response text
            chunk_size = 50
            for i in range(0, len(response_text), chunk_size):
                chunk = response_text[i:i + chunk_size]
                yield f"data: {json.dumps({'type': 'text', 'content': chunk})}\n\n"
            
            # Deduct credits
            if credits_used > 0:
                await Database.execute(
                    "UPDATE mcp.user_accounts SET credits_balance = credits_balance - $1 WHERE user_email = $2",
                    credits_used, user["email"]
                )
            
            new_balance = await Database.fetchval(
                "SELECT credits_balance FROM mcp.user_accounts WHERE user_email = $1",
                user["email"]
            )
            
            yield f"data: {json.dumps({'type': 'done', 'credits_used': credits_used, 'credits_remaining': new_balance})}\n\n"
            
        except Exception as e:
            logger.error(f"Stream error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")


@router.get("/status")
async def chat_status():
    """Check if AI Chat is available."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    tools = get_anthropic_tools()
    return {
        "available": bool(api_key),
        "tools_enabled": True,
        "tools_count": len(tools),
        "model": "claude-3-5-sonnet-20240620"
    }
