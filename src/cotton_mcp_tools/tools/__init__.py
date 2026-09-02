"""Tools package - register all MCP tools here."""

from mcp.server.fastmcp import FastMCP

from cotton_mcp_tools.tools.sample import register_sample_tools
from cotton_mcp_tools.tools.ui_analyzer import register_ui_analyzer_tools


def register_all_tools(server: FastMCP) -> None:
    """Register all tool modules with the MCP server."""
    register_sample_tools(server)
    register_ui_analyzer_tools(server)
