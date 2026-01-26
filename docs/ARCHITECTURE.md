# System Architecture

The Outris Identity MCP Server follows a modular architecture designed for security, scalability, and ease of integration.

## High-Level Overview

```mermaid
graph TD
    Client[Claude / Cursor] -->|SSE| Server[FastAPI / SSE Transport]
    Server -->|Protocol| MCPServer[MCP Protocol Handler]
    MCPServer -->|Auth| AuthModule[Authentication]
    MCPServer -->|Tool Execution| ToolRegistry[Tool Registry]
    ToolRegistry -->|Execute| Handler[Tool Handler]
    Handler -->|API Call| OutrisAPI[Outris Backend]
    
    subgraph Core "MCP Server Core"
        MCPServer
        AuthModule
        Credits[Credit System]
    end
```

## Components

### 1. Transport Layer (`server_sse.py`)
- Built on **FastAPI** and **sse-starlette**.
- Handles the HTTP/SSE connection lifecycle.
- Validates Authorization headers.

### 2. Protocol Layer (`mcp_server.py`)
- Uses the official `mcp` Python SDK.
- Implements `OutrisMCPServer` class.
- Manages tool listing and execution requests.
- Handles guest mode vs. authenticated mode logic.

### 3. Core Modules (`core/`)
- **Auth**: Validates API keys against the database.
- **Credits**: Manages atomic credit deduction and transaction logging.
- **Database**: Async PostgreSQL connection pool.

### 4. Tool Registry (`tools/`)
- Decorator-based registration system (`@tool`).
- Supports categorization and dynamic enabling/disabling of tools.
- Auto-generates MCP tool schemas.

## Security

- **secrets**: No secrets stored in code. Environment variables used for all credentials.
- **Authentication**: Bearer token (API Key) validation required for full access.
- **Isolation**: Tools run within the server process but make external API calls; no direct database access to sensitive user data from tools.
