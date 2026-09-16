"""
Repository Resolver — authoritatively resolves a repository identifier to canonical owner/repo.

Resolution states:
  FOUND      → MCP confirmed the repository exists
  NOT_FOUND  → MCP explicitly confirmed the repository does not exist (404)
  AMBIGUOUS  → multiple repositories match; cannot safely choose one
  ERROR      → MCP/network/auth/execution failure — NEVER treat as NOT_FOUND

Critical contract:
  - mcp_request_func must be called as: await mcp_request_func(tool_name, arguments)
  - ERROR must NEVER be propagated as NOT_FOUND
  - NOT_FOUND must NEVER be propagated as zero counts/zero items

Runtime MCP schema (verified 2026-09-14):
  - get_repository does NOT exist in the connected GitHub MCP server.
  - Repository resolution uses search_repositories(query=...) only.
  - get_file_contents uses 'repo' (not 'name') as the repository parameter.
"""

import logging
import re
from typing import Literal
from pydantic import BaseModel

logger = logging.getLogger(__name__)

RepoState = Literal["FOUND", "NOT_FOUND", "AMBIGUOUS", "ACCESS_DENIED", "ERROR"]


class ResolvedRepository(BaseModel):
    state: RepoState
    owner: str | None = None
    name: str | None = None
    full_name: str | None = None
    url: str | None = None
    default_branch: str | None = None
    message: str | None = None


def _parse_not_found(error_msg: str) -> bool:
    """Return True if the error message indicates a genuine GitHub 404/not-found."""
    msg = error_msg.lower()
    return "not found" in msg or "404" in msg or "does not exist" in msg or "no such" in msg


def _parse_access_denied(error_msg: str) -> bool:
    """Return True if the error message indicates an access/auth failure."""
    msg = error_msg.lower()
    return "access" in msg or "403" in msg or "forbidden" in msg or "unauthorized" in msg or "401" in msg


async def resolve_repository(query: str, mcp_request_func, username: str | None = None) -> ResolvedRepository:
    """
    Authoritatively resolve a repository based on user query (owner/repo or just repo name).

    Args:
        query: A repository identifier, e.g. "sunilkumar1701/github-project-analyzer" or "github-project-analyzer".
        mcp_request_func: Must be called as await mcp_request_func(tool_name, arguments_dict).
                          This matches the _execute_mcp_direct(tool_name, arguments) signature in tool_executor.py.
        username: The authenticated GitHub username to use as context for name-only queries.

    Returns:
        ResolvedRepository with explicit state.
    """
    query = query.strip()
    logger.info("[REPO RESOLUTION] input=%s", query)

    try:
        if "/" in query:
            # Exact owner/repo format — search with full_name query to verify existence
            # NOTE: get_repository does NOT exist in the connected GitHub MCP server.
            # We use search_repositories with the full name as query instead.
            parts = query.split("/", 1)
            owner = parts[0].strip()
            repo = parts[1].strip()

            try:
                data = await mcp_request_func(
                    "search_repositories",
                    {"query": f"repo:{owner}/{repo}"},
                )
                items = _extract_search_items(data)
                if items is None:
                    logger.error("[REPO RESOLUTION] status=ERROR error=unexpected_search_response")
                    return ResolvedRepository(
                        state="ERROR",
                        message="Unexpected repository search response from MCP.",
                    )

                if len(items) == 0:
                    logger.info("[REPO RESOLUTION] status=NOT_FOUND input=%s", query)
                    return ResolvedRepository(
                        state="NOT_FOUND",
                        message=f"Repository '{query}' was not found on GitHub.",
                    )

                # Find exact full_name match
                exact = [
                    r for r in items
                    if isinstance(r, dict) and
                    (r.get("full_name") or r.get("name", "")).lower() == f"{owner}/{repo}".lower()
                ]
                repo_data = exact[0] if exact else items[0]
                result = _build_resolved_from_dict(repo_data)
                if result:
                    logger.info("[REPO RESOLUTION] status=FOUND full_name=%s", result.full_name)
                    return result

                logger.error("[REPO RESOLUTION] status=ERROR error=malformed_search_item")
                return ResolvedRepository(
                    state="ERROR",
                    message="Malformed repository data in search response.",
                )

            except RuntimeError as e:
                err = str(e)
                if _parse_not_found(err):
                    logger.info("[REPO RESOLUTION] status=NOT_FOUND input=%s", query)
                    return ResolvedRepository(
                        state="NOT_FOUND",
                        message=f"Repository '{query}' was not found on GitHub.",
                    )
                if _parse_access_denied(err):
                    logger.info("[REPO RESOLUTION] status=ACCESS_DENIED input=%s", query)
                    return ResolvedRepository(
                        state="ACCESS_DENIED",
                        message=f"Access denied to repository '{query}'.",
                    )
                logger.error("[REPO RESOLUTION] status=ERROR error=%s", err)
                return ResolvedRepository(
                    state="ERROR",
                    message=f"MCP execution error during repository resolution: {err}",
                )

        else:
            # Name-only — use strict user-scoped search
            try:
                import json
                search_query = f"user:{username} {query} in:name" if username else f"{query} in:name"
                data = await mcp_request_func(
                    "search_repositories",
                    {"query": search_query},
                )
                items = _extract_search_items(data)

                if items is None:
                    logger.error("[REPO RESOLUTION] status=ERROR error=unexpected_search_response")
                    return ResolvedRepository(
                        state="ERROR",
                        message="Unexpected search response format from MCP.",
                    )

                if len(items) == 0:
                    logger.info("[REPO RESOLUTION] status=NOT_FOUND input=%s", query)
                    return ResolvedRepository(
                        state="NOT_FOUND",
                        message=f"No repositories found matching '{query}' for user '{username}'.",
                    )

                # Exact name match wins
                exact = [r for r in items if isinstance(r, dict) and r.get("name", "").lower() == query.lower()]
                if len(exact) == 1:
                    repo_data = exact[0]
                elif len(items) == 1:
                    repo_data = items[0]
                else:
                    logger.info("[REPO RESOLUTION] status=AMBIGUOUS input=%s count=%d", query, len(items))
                    return ResolvedRepository(
                        state="AMBIGUOUS",
                        message=(
                            f"Multiple repositories found for '{query}'. "
                            "Please specify as owner/repo (e.g. username/repo-name)."
                        ),
                    )

                result = _build_resolved_from_dict(repo_data)
                if result:
                    logger.info("[REPO RESOLUTION] status=FOUND full_name=%s", result.full_name)
                    return result

                logger.error("[REPO RESOLUTION] status=ERROR error=malformed_search_item")
                return ResolvedRepository(
                    state="ERROR",
                    message="Malformed repository data in search response.",
                )

            except RuntimeError as e:
                err = str(e)
                if _parse_not_found(err):
                    logger.info("[REPO RESOLUTION] status=NOT_FOUND input=%s", query)
                    return ResolvedRepository(
                        state="NOT_FOUND",
                        message=f"Repository '{query}' was not found on GitHub.",
                    )
                logger.error("[REPO RESOLUTION] status=ERROR error=%s", err)
                return ResolvedRepository(
                    state="ERROR",
                    message=f"MCP execution error during repository search: {err}",
                )

    except Exception as e:
        # Catch-all: any unexpected exception is an ERROR, never NOT_FOUND
        logger.error("[REPO RESOLUTION] status=ERROR error=%s", str(e), exc_info=True)
        return ResolvedRepository(
            state="ERROR",
            message=f"Unexpected resolution error: {str(e)}",
        )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _extract_repo_data(data) -> "ResolvedRepository | None":
    """
    Parse a get_repository MCP result (already normalized by _execute_mcp_direct)
    into a ResolvedRepository.

    _execute_mcp_direct returns the normalized/extracted content, which after
    _normalize_obj may be a compact repo dict with keys: name, description, stars, forks, language, updatedAt, url.
    The original raw dict from GitHub has: full_name, owner.login, name, html_url, default_branch.
    We handle both.
    """
    import json

    if data is None:
        return None

    # If data is a string (already serialized JSON), try parsing it
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except Exception:
            return None

    if isinstance(data, dict):
        # After _normalize_obj, repo objects may be compact.
        # The normalization heuristic preserves full_name as the 'name' field.
        full_name = data.get("full_name") or data.get("name")
        if full_name and "/" in str(full_name):
            parts = str(full_name).split("/", 1)
            return ResolvedRepository(
                state="FOUND",
                owner=parts[0],
                name=parts[1],
                full_name=full_name,
                url=data.get("url") or data.get("html_url"),
                default_branch=data.get("default_branch", "main"),
            )

        # Try owner sub-object (raw GitHub format, bypassing normalizer)
        owner_obj = data.get("owner")
        name = data.get("name")
        if isinstance(owner_obj, dict) and name:
            owner_login = owner_obj.get("login")
            fn = f"{owner_login}/{name}" if owner_login else name
            return ResolvedRepository(
                state="FOUND",
                owner=owner_login,
                name=name,
                full_name=fn,
                url=data.get("html_url"),
                default_branch=data.get("default_branch", "main"),
            )

    return None


def _extract_search_items(data) -> "list | None":
    """Extract items list from a search_repositories MCP result.
    
    Returns:
        list: The extracted items (may be empty for zero-match searches).
        None: Only for truly unrecognizable response shapes.
    """
    if data is None:
        return None

    # String data — try JSON parsing (MCP may return serialized JSON)
    if isinstance(data, str):
        import json as _json
        try:
            data = _json.loads(data)
        except Exception:
            # GitHub search validation errors (e.g., "resources do not exist") are returned as strings by MCP
            if "do not exist" in data.lower() or "not found" in data.lower() or "validation failed" in data.lower():
                logger.info("[REPO RESOLUTION] _extract_search_items: received validation error string — treating as empty")
                return []
            logger.warning("[REPO RESOLUTION] _extract_search_items: received string data, not JSON-parseable")
            return None

    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        # Standard search result: {"items": [...], "total_count": N}
        if "items" in data:
            return data["items"]
        if "results" in data:
            return data["results"]
        # Dict with total_count but no items key — this means zero results
        if "total_count" in data:
            logger.info("[REPO RESOLUTION] _extract_search_items: dict with total_count=%s but no items key — treating as empty", data.get("total_count"))
            return []
        # Dict with note (from _apply_reduction wrapping) but no items
        if "note" in data and "partial_count" in data:
            return []
        # Compact single-repo dict (has name/full_name) — wrap in list
        if data.get("name") or data.get("full_name"):
            return [data]
        # Unrecognized dict shape — log and return None
        logger.warning("[REPO RESOLUTION] _extract_search_items: unrecognized dict keys=%s", list(data.keys())[:10])
        return None

    logger.warning("[REPO RESOLUTION] _extract_search_items: unexpected data type=%s", type(data).__name__)
    return None


def _build_resolved_from_dict(repo_data: dict) -> "ResolvedRepository | None":
    """Build ResolvedRepository from a single repo dict (search result item)."""
    if not isinstance(repo_data, dict):
        return None

    full_name = repo_data.get("full_name") or repo_data.get("name")
    if not full_name:
        return None

    if "/" in str(full_name):
        parts = str(full_name).split("/", 1)
        owner_login = parts[0]
        repo_name = parts[1]
    else:
        owner_obj = repo_data.get("owner")
        owner_login = owner_obj.get("login") if isinstance(owner_obj, dict) else None
        repo_name = full_name
        full_name = f"{owner_login}/{repo_name}" if owner_login else repo_name

    return ResolvedRepository(
        state="FOUND",
        owner=owner_login,
        name=repo_name,
        full_name=full_name,
        url=repo_data.get("url") or repo_data.get("html_url"),
        default_branch=repo_data.get("default_branch", "main"),
    )
