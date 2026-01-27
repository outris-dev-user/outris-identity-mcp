# System Architecture

The Outris Identity MCP Server follows a modular architecture designed for security, scalability, and ease of integration.

## High-Level Overview

```mermaid
graph TD
    subgraph Clients "MCP Clients"
        Claude[Claude Desktop]
        Cursor[Cursor/Windsurf]
        CLI[CLI Tools]
    end
    
    subgraph Transports "Transport Layer"
        HTTP["Streamable HTTP<br/>(POST /http)"]
        SSE["SSE Legacy<br/>(GET /sse)"]
        STDIO["STDIO Local<br/>(--stdio)"]
    end
    
    subgraph Server "MCP Server"
        MCPServer[Protocol Handler]
        AuthModule[Authentication]
        ToolRegistry[Tool Registry]
        Credits[Credit System]
    end
    
    subgraph Backend "Backend APIs"
        OutrisAPI[Outris Identity API]
    end
    
    Claude -->|HTTP/JSON-RPC| HTTP
    Cursor -->|HTTP/JSON-RPC| HTTP
    Claude -->|SSE Stream| SSE
    CLI -->|STDIO| STDIO
    
    HTTP --> MCPServer
    SSE --> MCPServer
    STDIO --> MCPServer
    
    MCPServer -->|Auth| AuthModule
    MCPServer -->|Execute| ToolRegistry
    AuthModule -->|Validate| OutrisAPI
    ToolRegistry -->|API Call| OutrisAPI
    MCPServer -->|Track| Credits
    
    style HTTP fill:#90EE90
    style STDIO fill:#87CEEB
    style SSE fill:#FFD700
```

## Components

### 1. Transport Layer (Multiple Implementations)

#### **Streamable HTTP** (`server_streamable.py`) - PRIMARY
- Built on **FastAPI** (modern, stateless)
- Implements new MCP specification standard
- Each request is independent (no connection affinity)
- Better for load-balanced, cloud deployments
- Endpoints:
  - `POST /http` - JSON-RPC requests (authentication optional)
  - `GET /health` - Health check (no auth)
  - `GET /tools` - List available tools (no auth)
  - `GET /` - Server info

#### **SSE** (`server_sse.py`) - LEGACY
- Built on **FastAPI** and **sse-starlette**
- Backward compatibility for existing clients
- Maintains persistent connection
- Endpoints:
  - `GET /sse` - Server-Sent Events stream (authentication required)

#### **STDIO** (`__main__.py`) - LOCAL
- Uses official `mcp.server.stdio` module
- Perfect for local CLI execution
- Direct pipe connection (no HTTP overhead)
- Enabled via: `python -m mcp_server --stdio`

### 2. Protocol Layer (`mcp_server.py`)
- Uses the official `mcp` Python SDK v1.0+
- Implements `OutrisMCPServer` class
- Manages tool listing and execution requests
- Handles guest mode vs. authenticated mode logic
- Protocol: JSON-RPC 2.0

### 3. Core Modules (`core/`)
- **Auth**: Validates API keys against the database via Authorization header
- **Credits**: Manages atomic credit deduction and transaction logging
- **Database**: Async PostgreSQL connection pool (Neon compatible)
- **Config**: Environment-based configuration (Pydantic)

### 4. Tool Registry (`tools/`)
- Decorator-based registration system (`@tool`)
- Supports categorization and dynamic enabling/disabling
- Auto-generates MCP tool schemas (inputSchema, description)
- 8 tools total:
  - `get_name` - Find linked names for phone/email
  - `get_email` - Find linked emails for phone
  - `get_address` - Find linked addresses
  - `get_alternate_phones` - Find alternate phone numbers
  - `get_identity_profile` - Complete identity profile
  - `check_online_platforms` - Check social media registrations
  - `check_digital_commerce_activity` - Check e-commerce activity
  - `check_breaches` - Detect data breaches

## Transport Layer Comparison

| Feature | Streamable HTTP | SSE | STDIO |
|---------|---|---|---|
| **Protocol** | HTTP POST (stateless) | Server-Sent Events | Standard I/O pipes |
| **Use Case** | Cloud, web servers | Legacy, persistent | Local CLI tools |
| **Status** | ✅ PRIMARY (new MCP spec) | ⚠️ LEGACY | 🟢 NATIVE |
| **Scalability** | ⭐⭐⭐⭐⭐ High | ⭐⭐⭐ Medium | ⭐⭐⭐ Medium |
| **Load Balancing** | ✅ Easy | ❌ Requires sticky sessions | ✅ Yes (local) |
| **Connection Overhead** | Low (per-request) | High (persistent) | None |
| **Typical Clients** | Streaming API, web | Claude older, proxies | Local CLI |

## Deployment Modes

### Mode 1: HTTP Server (Cloud Deployment)
```bash
# Railway / Docker deployment
python -m mcp_server --http
# Exposes:
#   - POST /http (Streamable HTTP)
#   - GET /sse (SSE legacy)
#   - GET /health
#   - GET /tools
# URL: https://mcp-server.outris.com/http
```

### Mode 2: STDIO (Local Installation)
```bash
# Local CLI / pip package
python -m mcp_server --stdio
# Perfect for: npm install -g outris-identity-mcp
```

### Mode 3: Auto-detect (Smart Default)
```bash
# Automatically choose based on environment
python -m mcp_server
# If TTY: runs HTTP mode
# If non-TTY stdin: runs STDIO mode
```

## Security

- **secrets**: No secrets stored in code. Environment variables used for all credentials.
- **Authentication**: Bearer token (API Key) validation required for most tools
  - Header: `Authorization: Bearer <api_key>`
  - Demo tools (platform_check, check_whatsapp) available without auth
- **Rate Limiting**: Per-API-key rate limits enforced by auth layer
- **Credit System**: Tools consume credits from account balance
- **Isolation**: Tools run within server process but make external API calls; no direct database access from tools
- **Encryption**: PostgreSQL connection uses SSL (Neon required)
