"""Tests for sample tools."""

from cotton_mcp_tools.tools.sample import add, greet


def test_add():
    assert add(1, 2) == 3
    assert add(-1, 1) == 0
    assert add(0, 0) == 0


def test_greet():
    result = greet("World")
    assert "World" in result
    assert "Hello" in result
