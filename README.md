# Outris Identity MCP Server

Outris is an MCP server that lets AI agents investigate phone numbers and emails - find linked identities, check platform registrations, and detect data breaches.

## Features

- 🔍 **Identity Resolution:** Find names, emails, addresses linked to phone numbers
- 🌐 **Platform Checks:** Detect registration on 31+ platforms (India) + 3 global
- 🛒 **Commerce Activity:** Check ecommerce, travel, quick-commerce activity
- 🚨 **Breach Detection:** Check if phone/email appears in known breaches
- 🌍 **Global + India:** Full India coverage, partial global support

## Quick Start

1. **Get an API Key:** [Generate key from Outris Dashboard](https://portal.outris.com)

2. **Claude Desktop Setup:**
   ```json
   {
     "mcpServers": {
       "outris-identity": {
         "command": "npx",
         "args": ["-y", "mcp-remote", "https://mcp-server.outris.com/sse", "--transport", "sse-only", "--header", "Authorization=Bearer YOUR_KEY"]
       }
     }
   }
   ```

3. **Start using in Claude:**
   Ask Claude to "investigate 9876543210" or similar queries.

## Available Tools

| Tool | Credits | What It Does |
|------|---------|--------------|
| get_identity_profile | 3 | Complete identity profile (names, emails, addresses, documents) |
| get_name | 2 | Names linked to phone number |
| get_email | 2 | Email addresses linked to phone |
| get_address | 2 | Physical addresses (with category: ecommerce, banking, etc) |
| get_alternate_phones | 2 | Other phone numbers for same person |
| check_online_platforms | 1 | Registration on social media / apps |
| check_digital_commerce_activity | 1 | Ecommerce / quick-commerce activity |
| check_breaches | 1 | Breach database exposure |

## Documentation

- [Setup Guide](SETUP.md)
- [Tool Reference](TOOLS.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Credit System](docs/CREDIT_SYSTEM.md)

## License

MIT - See LICENSE file

## Support

- Issues: [GitHub Issues](https://github.com/outris/outris-identity-mcp/issues)
- Docs: [docs.outris.com](https://docs.outris.com)
