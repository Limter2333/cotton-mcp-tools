"""Tools package - register all MCP tools here."""

from mcp.server.fastmcp import FastMCP

from cotton_mcp_tools.tools.sample import register_sample_tools


def register_all_tools(server: FastMCP) -> None:
    """Register all tool modules with the MCP server."""
    register_sample_tools(server)
    # Add more tool registrations here:
    # register_other_tools(server)
