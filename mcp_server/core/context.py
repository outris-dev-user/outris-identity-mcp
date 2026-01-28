from contextvars import ContextVar
from typing import Optional
from .auth import MCPAccount

# Context variable to hold the current MCP account during request processing
current_account: ContextVar[Optional[MCPAccount]] = ContextVar("current_account", default=None)
