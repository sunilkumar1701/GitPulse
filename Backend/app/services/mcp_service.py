"""
MCP service — handles communication with the GitHub Remote MCP Server.
Port of services/mcp.service.js.
"""

import json
import logging

from app.clients.mcp_client import mcp_request
from app.core.config import get_settings

logger = logging.getLogger(__name__)


def parse_mcp_response(raw_response) -> dict:
    """
    Parse an MCP response which may be either a JSON object
    or an SSE-formatted string with 'event: message\\ndata: {...}'.

    Exact port of parseMcpResponse() from mcp.service.js.

    Args:
        raw_response: The raw MCP response (dict or string).

    Returns:
        Parsed dict.
    """
    try:
        if not raw_response:
            raise ValueError("Empty MCP response")

        if isinstance(raw_response, dict):
            return raw_response

        # Handle SSE format safely
        text = str(raw_response).strip()
        if text.startswith("event:"):
            for line in text.splitlines():
                if line.startswith("data: "):
                    return json.loads(line[6:])
                elif line.startswith("data:"):
                    return json.loads(line[5:])
        
        return json.loads(text)
    except Exception as e:
        logger.error("MCP Response Parse Error: %s", str(e))
        return {
            "error": True,
            "message": "Unable to parse MCP response.",
            "raw": str(raw_response),
        }


async def execute_mcp_tool(tool_name: str, args: dict | None = None) -> dict:
    """
    Execute an MCP tool via the Remote MCP Server.

    Args:
        tool_name: The name of the MCP tool to execute.
        args: Arguments for the tool.

    Returns:
        Parsed MCP response.

    Raises:
        Exception: On MCP errors.
    """
    try:
        settings = get_settings()
        if not settings.GITHUB_MCP_PAT:
            raise RuntimeError("GITHUB_MCP_PAT is missing.")

        response = await mcp_request(
            method="tools/call",
            params={
                "name": tool_name,
                "arguments": args or {},
            },
        )

        parsed = parse_mcp_response(response)

        if parsed.get("error"):
            raise RuntimeError(
                parsed.get("message", "Tool execution failed.")
            )

        return parsed

    except Exception as error:
        logger.error("\n========== MCP ERROR ==========\n")
        logger.error(str(error))
        logger.error("\n===============================\n")

        raise RuntimeError(
            str(error) or "Failed to execute MCP tool."
        )


async def get_available_tools() -> dict | None:
    """
    Fetch the list of available MCP tools from the Remote MCP Server.

    Returns:
        Parsed MCP response with result.tools, or None on failure.
    """
    try:
        settings = get_settings()
        if not settings.GITHUB_MCP_PAT:
            raise RuntimeError("GITHUB_MCP_PAT is missing.")

        response = await mcp_request(method="tools/list")

        parsed = parse_mcp_response(response)

        tools = parsed.get("result", {}).get("tools", [])
        total_tools = len(tools) if isinstance(tools, list) else 0

        logger.info("\n========== TOOLS RESPONSE ==========\n")
        logger.info("Loaded %d tools", total_tools)
        logger.info("\n====================================\n")

        return parsed

    except Exception as error:
        logger.error("\n========== TOOLS ERROR ==========\n")
        logger.error(str(error))
        logger.error("\n=================================\n")
        return None
