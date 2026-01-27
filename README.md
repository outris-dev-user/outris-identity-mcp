# Outris Identity MCP Server

Outris Identity is a Model Context Protocol (MCP) server that lets AI agents investigate phone numbers and emails - find linked identities, check platform registrations, and detect data breaches.

**Version 2.0** - Now with Streamable HTTP, SSE, and STDIO support! 🚀

## Features

- 🔍 **Identity Resolution:** Find names, emails, addresses linked to phone numbers
- 🌐 **Platform Checks:** Detect registration on 31+ platforms (India) + 3 global
- 🛒 **Commerce Activity:** Check ecommerce, travel, quick-commerce activity
- 🚨 **Breach Detection:** Check if phone/email appears in known breaches
- 🌍 **Global + India:** Full India coverage, partial global support
- 📡 **Multiple Transports:** Streamable HTTP (new), SSE (legacy), STDIO (local)
- 🔐 **Secure:** API key authentication, credit-based rate limiting
- 🚀 **Ready for Registry:** Meet all MCP official registry requirements

## Quick Start

### Option 1: Cloud Deployment (Fastest) ☁️

**Step 1:** Get API Key from [Outris Portal](https://portal.outris.com)

**Step 2:** Configure Claude Desktop

Edit `claude_desktop_config.json`:

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
        "https://mcp-server.outris.com/http",
        "--transport", 
        "streamable-http",
        "--header", 
        "Authorization=Bearer YOUR_API_KEY"
      ]
    }
  }
}
```

**Step 3:** Restart Claude and start investigating!

### Option 2: Local Installation 🏠

```bash
git clone https://github.com/outris/outris-identity-mcp.git
cd outris-identity-mcp

pip install -r requirements.txt
python -m mcp_server --http
# Server runs on http://localhost:8000
```

### Option 3: Docker 🐳

```bash
docker build -t outris-identity .
docker run -e OUTRIS_API_KEY="your_key" -p 8000:8000 outris-identity
```

See [SETUP.md](SETUP.md) for detailed configuration instructions.

## Available Tools

| Tool | Credits | Use Case |
|------|---------|----------|
| **get_identity_profile** | 3 | Complete profile: names, emails, addresses, documents |
| **get_name** | 2 | Names linked to phone |
| **get_email** | 2 | Emails linked to phone |
| **get_address** | 2 | Addresses (ecommerce, banking, etc.) |
| **get_alternate_phones** | 2 | Other phones for same person |
| **check_online_platforms** | 1 | Social media/app registrations |
| **check_digital_commerce_activity** | 1 | Ecommerce/quick-commerce activity |
| **check_breaches** | 1 | Data breach detection |

## Transports

| Transport | URL | Use Case | Status |
|-----------|-----|----------|--------|
| **Streamable HTTP** | `POST /http` | Cloud, Claude Desktop | ✅ PRIMARY |
| **SSE** | `GET /sse` | Legacy clients, proxies | ⚠️ Supported |
| **STDIO** | `python -m mcp_server` | Local CLI, direct integration | 🟢 Native |

## Documentation

- 📖 [Setup Guide](SETUP.md) - Installation & configuration
- 🔧 [Tool Reference](TOOLS.md) - Complete tool documentation
- 🏗️ [Architecture](docs/ARCHITECTURE.md) - System design & transports
- 💳 [Credit System](docs/CREDIT_SYSTEM.md) - Pricing & quotas

## Example Usage

```bash
# Test the server
curl https://mcp-server.outris.com/health

# List available tools
curl https://mcp-server.outris.com/tools

# Execute a tool
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

## MCP Registry Listing

This server is registered on the official MCP registry: https://registry.modelcontextprotocol.io/

- **Type:** Streamable HTTP + SSE + STDIO
- **Auth:** Bearer token (API key)
- **Region:** Global + India optimized

## License

MIT - See [LICENSE](LICENSE) file for details

## Support & Community

- 📝 [Issues](https://github.com/outris/outris-identity-mcp/issues)
- 💬 [Discussions](https://github.com/outris/outris-identity-mcp/discussions)
- 📧 [Email Support](mailto:support@outris.com)
- 🌐 [Documentation](https://docs.outris.com)

## Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

**Built with:** Official MCP SDK • FastAPI • PostgreSQL • Neon

**Maintained by:** Outris Technologies
