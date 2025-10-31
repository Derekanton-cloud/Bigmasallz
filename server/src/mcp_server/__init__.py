"""MCP Server module initialization."""

from src.mcp_server.server import app, main
from src.mcp_server.copilot_fastmcp import app as copilot_app
from src.mcp_server.copilot_fastmcp import main as copilot_main

__all__ = ["app", "main", "copilot_app", "copilot_main"]
