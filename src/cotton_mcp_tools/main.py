"""MCP Server entry point.

This module initializes and runs the MCP server with all registered tools.
"""

from mcp.server.fastmcp import FastMCP

from cotton_mcp_tools.tools import register_all_tools


def create_server() -> FastMCP:
    """Create and configure the MCP server instance."""
    server = FastMCP(
        name="cotton-mcp-tools",
        version="0.1.0",
    )
    register_all_tools(server)
    return server


def main() -> None:
    """Run the MCP server."""
    server = create_server()
    server.run()


if __name__ == "__main__":
    main()
