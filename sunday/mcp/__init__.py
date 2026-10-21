"""MCP (Model Context Protocol) client module for Sunday."""

from .client import MCPClient
from .servers import MCPServerRegistry

__all__ = ["MCPClient", "MCPServerRegistry"]
