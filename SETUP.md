# Setup Guide - Three Ways to Use Outris Identity MCP

> **New in v2.0:** Streamable HTTP (primary), SSE (legacy), and STDIO (local) transports available!

## Prerequisites
- **API Key**: Visit [Outris Portal](https://portal.outris.com), sign up, and generate an MCP API Key
- **Python 3.11+** (for local setup)

---

## Option 1: Cloud Deployment (Recommended) 🚀

Use the official Outris Identity MCP server hosted on Railway. No installation needed!

### 1.1 Claude Desktop Configuration

Edit your Claude Desktop config:

**Mac:** `~/Library/Application Support/Claude/claude_desktop_config.json`  
**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

#### Method A: Streamable HTTP (New - Recommended)
```json
{
  "mcpServers": {
    "outris-identity": {
      "command": "npx",
      "args": [
        "-y", 
        "mcp-remote", 
        "https://mcp-server.outris.com/http",
        "--transport", 
        "http-first",
        "--header", 
        "Authorization: Bearer YOUR_OUTRIS_API_KEY"
      ]
    }
  }
}
```

#### Method B: SSE (Legacy - Still Works)
```json
{
  "mcpServers": {
    "outris-identity": {
      "command": "npx",
      "args": [
        "-y", 
        "mcp-remote", 
        "https://mcp-server.outris.com/sse", 
        "--transport", 
        "sse-first", 
        "--header", 
        "Authorization: Bearer YOUR_OUTRIS_API_KEY"
      ]
    }
  }
}
```

### 1.2 Cursor / Windsurf Configuration

In **Cursor Settings** > **Features** > **MCP**:

1. Click **+ Add New MCP Server**
2. **Name**: `outris-identity`
3. **URL**: `https://mcp-server.outris.com/http` (Streamable HTTP recommended)
4. **Transport**: Select from dropdown
5. **Headers**: Add custom header
   - **Key**: `Authorization`
   - **Value**: `Bearer YOUR_OUTRIS_API_KEY`

---

## Option 2: Local Installation (Self-Hosted) 🏠

Install Outris Identity locally for offline use or custom deployments.

### 2.1 Installation

```bash
# Clone repository
git clone https://github.com/outris/outris-identity-mcp.git
cd outris-identity-mcp

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env

# Edit .env with your settings
nano .env
```

### 2.2 Run Locally

#### Option A: HTTP Server (Claude Desktop/Cursor)
```bash
python -m mcp_server --http
# Server runs on http://localhost:8000
# Endpoints:
#   - POST /http (Streamable HTTP)
#   - GET /sse (SSE legacy)
#   - GET /health
#   - GET /tools
```

Then configure Claude/Cursor to use `http://localhost:8000/http` or `http://localhost:8000/sse`

#### Option B: STDIO Mode (CLI / Direct Integration)
```bash
python -m mcp_server --stdio
# Connects via standard input/output
# Perfect for direct tool integration
```

#### Option C: Auto-detect (Smart)
```bash
python -m mcp_server
# Automatically selects based on environment:
# - If interactive terminal: runs HTTP server
# - If piped input: runs STDIO mode
```

### 2.3 Docker Deployment

```bash
# Build Docker image
docker build -t outris-identity-mcp .

# Run container (HTTP mode)
docker run -e OUTRIS_API_KEY="your_key" \
           -p 8000:8000 \
           outris-identity-mcp

# Run container (STDIO mode)
docker run -it -e OUTRIS_API_KEY="your_key" \
           outris-identity-mcp \
           python -m mcp_server --stdio
```

---

## Option 3: From Source (Development) 👨‍💻

For contributing or debugging.

```bash
# Clone and install in development mode
git clone https://github.com/outris/outris-identity-mcp.git
cd outris-identity-mcp

# Install with development dependencies
pip install -r requirements.txt
pip install pytest pytest-asyncio black flake8

# Run tests
pytest tests/

# Start development server with hot reload
python -m mcp_server --http
```

---

## Configuration

### Environment Variables (.env)

Create `.env` file from template:
```bash
cp .env.example .env
```

**Key variables:**

```bash
# API Configuration
OUTRIS_API_KEY=your_default_key_here      # Default API key

# Database
DATABASE_URL=postgresql://user:pass@host/db  # Neon PostgreSQL

# Server
LOG_LEVEL=INFO                            # DEBUG, INFO, WARNING, ERROR

# Features
ENABLE_KYC_TOOLS=true                     # Enable KYC verification tools
```

---

## Testing Your Setup

### Test 1: Server Health Check
```bash
curl https://mcp-server.outris.com/health
# Response: {"status":"healthy","server":"outris-mcp-server",...}
```

### Test 2: List Available Tools
```bash
curl https://mcp-server.outris.com/tools
# Response: {"total":8,"tools":{...}}
```

### Test 3: Execute Tool (with auth)
```bash
curl -X POST "https://mcp-server.outris.com/http" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "jsonrpc":"2.0",
    "id":1,
    "method":"tools/call",
    "params":{
      "name":"check_online_platforms",
      "arguments":{"identifier":"+919876543210"}
    }
  }'
```

### Test 4: Local STDIO Mode
```bash
# Start server in STDIO mode
python -m mcp_server --stdio

# In another terminal, send JSON-RPC:
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | \
  python -c "
import sys; 
import json
from mcp_server.mcp_server import OutrisMCPServer
import asyncio
"
```

---

## Transport Comparison

| Use Case | Recommended | Configuration |
|----------|------------|---|
| **Cloud Integration** | Streamable HTTP | `https://mcp-server.outris.com/http` |
| **Claude Desktop** | Streamable HTTP | Use `http-first` transport |
| **Cursor / Windsurf** | Streamable HTTP | HTTP endpoint with headers |
| **Local Development** | STDIO | `python -m mcp_server --stdio` |
| **Self-Hosted Web** | HTTP Server | `python -m mcp_server --http` |
| **Legacy Clients** | SSE | `https://mcp-server.outris.com/sse` |

---

## Troubleshooting

### Issue: Connection refused to localhost:8000
```bash
# Check if port is in use
lsof -i :8000

# Use different port
python -m mcp_server --http --port 8001
```

### Issue: Authentication error
```
error: "code": 401, "message": "Unauthorized"
```
- Verify API key is correct
- Check header format: `Authorization: Bearer <key>`
- Ensure key is active in Outris Portal

### Issue: Tools not appearing
- Run `/tools` endpoint to list available tools
- Check `ENABLE_KYC_TOOLS` setting in .env
- Verify authentication for non-demo tools

### Issue: Database connection error
- Check `DATABASE_URL` in .env
- Verify PostgreSQL is running (if local)
- Ensure Neon credentials are correct

---

## Support

- **Documentation**: https://github.com/outris/outris-identity-mcp/docs
- **Issues**: https://github.com/outris/outris-identity-mcp/issues
- **Email**: support@outris.com
