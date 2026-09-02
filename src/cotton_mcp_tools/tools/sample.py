"""Sample tools - example MCP tool implementations.

Replace this with your actual tool implementations.
"""

from mcp.server.fastmcp import FastMCP


def add(a: int, b: int) -> int:
    """Add two numbers together.

    Args:
        a: First number
        b: Second number

    Returns:
        The sum of a and b
    """
    return a + b


def greet(name: str) -> str:
    """Generate a greeting message.

    Args:
        name: Name to greet

    Returns:
        A greeting string
    """
    return f"Hello, {name}! Welcome to Cotton MCP Tools."


def register_sample_tools(server: FastMCP) -> None:
    """Register sample tools with the MCP server."""
    server.tool()(add)
    server.tool()(greet)
