"""
In-memory MCP tool cache.
Exact port of mcp/mcpToolsCache.js.

Stores the list of available MCP tools fetched at startup
so that tools/list is not called on every chat request.
"""

import threading
from typing import Any

_lock = threading.Lock()
_tools_cache: list[dict[str, Any]] = []


def set_tools_cache(tools: list[dict[str, Any]]) -> None:
    """
    Replace the cached tool list.

    Args:
        tools: List of tool dicts with name, description, inputSchema.

    Raises:
        TypeError: If tools is not a list.
    """
    if not isinstance(tools, list):
        raise TypeError("tools_cache must be a list.")

    global _tools_cache
    with _lock:
        _tools_cache = list(tools)


def get_tools_cache() -> list[dict[str, Any]]:
    """Returns a copy of the cached tool list."""
    with _lock:
        return list(_tools_cache)


def clear_tools_cache() -> None:
    """Clears all cached tools."""
    global _tools_cache
    with _lock:
        _tools_cache = []


def has_tools_cache() -> bool:
    """Returns True if there are cached tools."""
    with _lock:
        return len(_tools_cache) > 0
