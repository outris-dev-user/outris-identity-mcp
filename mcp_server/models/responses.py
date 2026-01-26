"""
Response models for MCP Server.
"""
from typing import Any, Optional
from pydantic import BaseModel, Field


class ToolCallResponse(BaseModel):
    """Response from a tool call."""
    success: bool
    result: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    credits_used: int = 0
    credits_remaining: int = 0
    execution_time_ms: float = 0


class MCPMessage(BaseModel):
    """Generic MCP message for SSE."""
    jsonrpc: str = "2.0"
    id: Optional[int | str] = None
    method: Optional[str] = None
    result: Optional[Any] = None
    error: Optional[dict] = None


class ServerInfo(BaseModel):
    """Server information for initialize response."""
    name: str = "outris-mcp-server"
    version: str = "1.0.0"


class InitializeResult(BaseModel):
    """Result of initialize request."""
    protocolVersion: str = "2025-03-26"
    serverInfo: ServerInfo = Field(default_factory=ServerInfo)
    capabilities: dict = Field(default_factory=lambda: {
        "tools": {"listChanged": True}
    })


class ToolInfo(BaseModel):
    """Tool information for tools/list response."""
    name: str
    description: str
    inputSchema: dict


class ToolsListResult(BaseModel):
    """Result of tools/list request."""
    tools: list[ToolInfo]


class ContentItem(BaseModel):
    """Content item in tool call result."""
    type: str = "text"
    text: str


class ToolCallResult(BaseModel):
    """Result of tools/call request."""
    content: list[ContentItem]
    isError: bool = False


class CreditInfo(BaseModel):
    """Credit information for responses."""
    balance: int
    used: int
    tier: str
