"""
Response builder — assembles source attribution metadata from tool results.
"""

import json
from typing import Any

from app.agent.schemas import AgentSource
from app.agent.tool_registry import get_tool


def build_sources(tool_results: list[dict[str, Any]]) -> list[dict]:
    """
    Build a list of source attributions from tool call results.

    Returns list of dicts safe to send to the frontend.
    Never includes secrets, PATs, or internal URLs.
    """
    sources = []
    seen = set()

    for tr in tool_results:
        if not tr.get("success"):
            continue

        tool_name = tr.get("tool_name", "")
        if tool_name in seen:
            continue
        seen.add(tool_name)

        tool_def = get_tool(tool_name)
        label = tool_def["ui_label"] if tool_def else f"GitHub ({tool_name})"

        # Try to extract a repo name from result for detail
        result = tr.get("result")
        detail = _extract_detail(result, tool_name)

        source = {
            "label": label,
            "detail": detail,
            "tool": tool_name,
        }
        sources.append(source)

    return sources


def _extract_detail(result: Any, tool_name: str) -> str | None:
    """Try to extract a meaningful detail string from a tool result."""
    if not result:
        return None

    if isinstance(result, dict):
        # Repository detail
        for field in ("full_name", "name"):
            val = result.get(field)
            if val and isinstance(val, str):
                return val

        # List result
        items = result.get("items") or result.get("repositories") or result.get("issues") or result.get("pull_requests")
        if isinstance(items, list):
            return f"{len(items)} result(s)"

    if isinstance(result, list):
        return f"{len(result)} result(s)"

    return None
