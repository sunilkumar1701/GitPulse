"""
GitHub REST API client using httpx.AsyncClient.
Mirrors the axios instance in config/github.config.js.
"""

import logging
import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_client: httpx.AsyncClient | None = None


def get_github_client() -> httpx.AsyncClient:
    """
    Returns the singleton GitHub API httpx.AsyncClient.
    Must be initialized via init_github_client() at startup.
    """
    global _client
    if _client is None:
        _client = _create_client()
    return _client


def _create_client() -> httpx.AsyncClient:
    """Creates a new httpx.AsyncClient configured for the GitHub REST API."""
    settings = get_settings()

    if not settings.GITHUB_TOKEN:
        raise RuntimeError("GITHUB_TOKEN is missing in environment variables.")

    return httpx.AsyncClient(
        base_url=settings.GITHUB_API,
        timeout=httpx.Timeout(10.0),
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {settings.GITHUB_TOKEN}",
            "User-Agent": "GitHub-Talent-Analyzer",
        },
    )


async def init_github_client() -> None:
    """Initialize the GitHub API client at application startup."""
    global _client
    _client = _create_client()
    logger.info("GitHub API client initialized")


async def close_github_client() -> None:
    """Close the GitHub API client at application shutdown."""
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
        logger.info("GitHub API client closed")


from app.utils.cache import async_ttl_cache

@async_ttl_cache(ttl_seconds=300) # Cache responses for 5 minutes
async def github_get(path: str, params: dict | None = None) -> dict | list:
    """
    Perform a GET request to the GitHub REST API.

    Args:
        path: API path (e.g., "/users/octocat")
        params: Optional query parameters

    Returns:
        Parsed JSON response

    Raises:
        httpx.HTTPStatusError: On 4xx/5xx responses
    """
    client = get_github_client()
    response = await client.get(path, params=params)
    response.raise_for_status()
    return response.json()
