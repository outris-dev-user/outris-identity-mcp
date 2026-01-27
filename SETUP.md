# Setup Guide

## 1. Get an API Key
Visit [Outris Portal](https://portal.outris.com), sign up, and generate an MCP API Key.

## 2. Claude Desktop Integration

Add the following to your `claude_desktop_config.json`:

**Mac:** `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

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
        "sse-only", 
        "--header", 
        "Authorization=Bearer YOUR_OUTRIS_API_KEY"
      ]
    }
  }
}
```

## 3. Cursor Integration

1. Open **Cursor Settings** > **Features** > **MCP**.
2. Click **+ Add New MCP Server**.
3. Select **SSE** type.
4. **URL**: `https://mcp-server.outris.com/sse`
5. **Additional Header**: `Authorization: Bearer YOUR_OUTRIS_API_KEY` (Wait for cursor to support header config if not available, or use the local proxy method below).

### Local Proxy for Cursor (Alternative)
If your Cursor version doesn't support headers yet, run the local proxy:

```bash
# Clone this repo
git clone https://github.com/outris/outris-identity-mcp.git
cd outris-identity-mcp

# Install dependencies
pip install -r requirements.txt

# Run the proxy
python -m mcp_server.server_sse
```
Then point Cursor to `http://localhost:8000/sse`.
