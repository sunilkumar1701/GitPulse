"""
GitHub Remote MCP Server client using httpx.AsyncClient.
Communicates via JSON-RPC 2.0 over HTTP.
Mirrors the axios-based MCP client in services/mcp.service.js.
"""

import logging
import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

MCP_URL = "https://api.githubcopilot.com/mcp/"

_client: httpx.AsyncClient | None = None


def get_mcp_client() -> httpx.AsyncClient:
    """
    Returns the singleton MCP httpx.AsyncClient.
    Must be initialized via init_mcp_client() at startup.
    """
    global _client
    if _client is None:
        _client = _create_client()
    return _client


def _create_client() -> httpx.AsyncClient:
    """Creates a new httpx.AsyncClient configured for the GitHub Remote MCP Server."""
    settings = get_settings()

    if not settings.GITHUB_MCP_PAT:
        raise RuntimeError("GITHUB_MCP_PAT is missing in environment variables.")

    return httpx.AsyncClient(
        base_url=MCP_URL,
        timeout=httpx.Timeout(30.0),
        headers={
            "Authorization": f"Bearer {settings.GITHUB_MCP_PAT}",
            "Content-Type": "application/json",
        },
    )


async def init_mcp_client() -> None:
    """Initialize the MCP client at application startup."""
    global _client
    _client = _create_client()
    logger.info("MCP client initialized")


async def close_mcp_client() -> None:
    """Close the MCP client at application shutdown."""
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
        logger.info("MCP client closed")


async def mcp_request(method: str, params: dict | None = None) -> dict:
    """
    Send a JSON-RPC 2.0 request to the GitHub Remote MCP Server.

    Args:
        method: The JSON-RPC method (e.g., "tools/list", "tools/call")
        params: Optional parameters for the method

    Returns:
        Parsed JSON response

    Raises:
        httpx.HTTPStatusError: On HTTP errors
    """
    client = get_mcp_client()

    payload: dict = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
    }

    if params is not None:
        payload["params"] = params

    try:
        response = await client.post("", json=payload)
        response.raise_for_status()
        return response.text
    except httpx.TimeoutException:
        logger.error("MCP request timed out for method %s", method)
        raise RuntimeError("GitHub MCP connection timed out. Please try again.")
    except httpx.HTTPStatusError as e:
        logger.error("MCP HTTP error: %s", str(e))
        raise RuntimeError(f"GitHub MCP connection error: {e.response.status_code}")
