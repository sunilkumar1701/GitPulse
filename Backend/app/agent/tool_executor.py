"""
Tool executor — FastAPI-owned MCP tool executor.

The LLM requests tool_name + arguments.
FastAPI validates, allow-lists, and executes.
The LLM NEVER connects directly to GitHub MCP.

Security:
- Tool must be in the allow-list
- Tool must be read-only
- Arguments validated against input_schema required fields
- MCP result normalized (remove huge irrelevant fields)
- GITHUB_MCP_PAT never sent to the LLM

Capability Resolver:
- If the LLM requests a blocked tool (e.g., list_repositories), the resolver
  deterministically maps it to an available equivalent workflow.
- If no equivalent exists, returns capability_unavailable immediately.
- This prevents infinite retry loops without ever exposing blocked tools.

Evidence State:
- Every MCP result carries a compact evidence state dict.
- The LLM must not fabricate data; it must base its answer only on evidence.
"""

import json
import logging
from typing import Any

from app.agent.tool_registry import get_tool, is_tool_allowed
from app.clients.mcp_client import mcp_request
from app.services.mcp_service import parse_mcp_response
from app.agent.semantic_router import Capability
from app.agent.capability_contract import validate_contract

logger = logging.getLogger(__name__)

# Max size of a tool result (characters) to prevent massive context injection
MAX_RESULT_CHARS = 6000

# Max content length for README results before truncation
MAX_README_CHARS = 3000

# Fields to remove from MCP results to reduce token usage
_STRIP_FIELDS = {
    "node_id",
    "gravatar_id",
    "events_url",
    "followers_url",
    "following_url",
    "gists_url",
    "starred_url",
    "subscriptions_url",
    "organizations_url",
    "repos_url",
    "received_events_url",
    "type",
    "site_admin",
    "hooks_url",
    "issue_events_url",
    "notifications_url",
    "keys_url",
    "teams_url",
    "git_refs_url",
    "git_tags_url",
    "contents_url",
    "compare_url",
    "merges_url",
    "archive_url",
    "downloads_url",
    "deployments_url",
    "git_commits_url",
    "git_url",
    "mirror_url",
    "ssh_url",
    "clone_url",
    "svn_url",
    "statuses_url",
    "languages_url",
    "stargazers_url",
    "contributors_url",
    "subscribers_url",
    "subscription_url",
    "commits_url",
    "blobs_url",
    "trees_url",
    "pulls_url",
    "milestones_url",
    "assignees_url",
    "branches_url",
    "tags_url",
    "collaborators_url",
    "issue_comment_url",
    "issues_url",
    "releases_url",
    "labels_url",
    "comments_url",
}


def _normalize_obj(obj: Any, depth: int = 0) -> Any:
    """Recursively remove noisy URL template fields and aggressively normalize entities."""
    if depth > 5:
        return obj

    if isinstance(obj, dict):
        # Repository heuristic
        if "stargazers_count" in obj and "full_name" in obj:
            return {
                "name": obj.get("full_name") or obj.get("name"),
                "description": obj.get("description"),
                "stars": obj.get("stargazers_count"),
                "forks": obj.get("forks_count"),
                "language": obj.get("language"),
                "updatedAt": obj.get("updated_at"),
                "url": obj.get("html_url"),
                "fork": obj.get("fork", False),
                "default_branch": obj.get("default_branch", "main"),
            }

        # Issue / PR heuristic
        if "number" in obj and "title" in obj and "state" in obj:
            # Extract repository with fallback order:
            # 1. repository field  2. repository_url  3. parse html_url
            _pr_repo = obj.get("repository")
            if not _pr_repo:
                _rurl = obj.get("repository_url", "")
                if _rurl:
                    _parts = _rurl.rstrip("/").split("/")
                    if len(_parts) >= 2:
                        _pr_repo = "/".join(_parts[-2:])
            if not _pr_repo:
                import re as _re_pr
                _html = obj.get("html_url", "")
                _m = _re_pr.search(r'github\.com/([^/]+/[^/]+)/', _html)
                _pr_repo = _m.group(1) if _m else None
            return {
                "number": obj.get("number"),
                "title": obj.get("title"),
                "state": obj.get("state"),
                "repository": _pr_repo,
                "createdAt": obj.get("created_at"),
                "updatedAt": obj.get("updated_at"),
                "url": obj.get("html_url"),
                "pull_request": "pull_request" in obj,  # True if this is a PR
            }

        # Commit heuristic
        if "sha" in obj and "commit" in obj:
            commit_data = obj["commit"]
            return {
                "sha": obj.get("sha"),
                "message": commit_data.get("message"),
                "author": commit_data.get("author", {}).get("name"),
                "date": commit_data.get("author", {}).get("date"),
                "url": obj.get("html_url"),
            }

        # Fallback strip fields
        return {
            k: _normalize_obj(v, depth + 1)
            for k, v in obj.items()
            if k not in _STRIP_FIELDS
        }

    if isinstance(obj, list):
        return [_normalize_obj(item, depth + 1) for item in obj[:15]]  # tighter cap

    return obj


def _apply_reduction(data: Any, reduction: dict | None, full_data: dict | None = None) -> Any:
    """Apply deterministic data reduction to a result list based on the QueryPlan."""
    if not isinstance(data, list):
        return data

    if not reduction:
        if len(data) > 10:
            return {
                "items": data[:10],
                "note": "Results safely truncated to 10. For full analysis, use a deterministic reduction operation (like count or top_n)."
            }
        return data

    op = reduction.get("operation")
    if not op:
        return data

    metric = reduction.get("metric")
    limit = int(reduction.get("limit", reduction.get("n", 5)))

    # Safe metric normalizations
    if metric == "stars":
        metric = "stargazers_count"
    if metric == "forks":
        metric = "forks_count"

    # 1. Filter
    filters = reduction.get("filters", {})
    if "filter_key" in reduction and "filter_value" in reduction:
        filters[reduction["filter_key"]] = reduction["filter_value"]

    if filters:
        for k, v in filters.items():
            data = [item for item in data if isinstance(item, dict) and str(item.get(k, "")).lower() == str(v).lower()]

    # 1.5 Fork Filtering
    include_forks = reduction.get("include_forks", False)
    if not include_forks and reduction.get("scope") != "specific_repository":
        if data and isinstance(data[0], dict) and "fork" in data[0]:
            data = [item for item in data if isinstance(item, dict) and item.get("fork") is not True]

    # 2. Sort
    sort_field = reduction.get("sort")
    if sort_field:
        desc = True
        if sort_field.lower().endswith(" asc"):
            desc = False
            sort_field = sort_field[:-4]
        elif sort_field.lower().endswith(" desc"):
            sort_field = sort_field[:-5]

        try:
            data.sort(
                key=lambda x: (
                    x.get(sort_field, 0) if isinstance(x, dict) and x.get(sort_field) is not None else 0,
                    x.get("full_name", x.get("name", "")) if isinstance(x, dict) else ""
                ),
                reverse=desc
            )

            if limit and len(data) > limit and isinstance(data[0], dict) and data[0].get(sort_field) is not None:
                first_val = data[0].get(sort_field)
                last_val = data[min(len(data)-1, limit-1)].get(sort_field)
                if first_val == last_val and first_val == 0:
                    for i in range(min(len(data), limit)):
                        if isinstance(data[i], dict):
                            data[i]["_sort_note"] = f"Tied at {first_val} for {sort_field}"
        except Exception:
            pass

    # Generic Operations
    if op == "count":
        if full_data and "total_count" in full_data and isinstance(full_data["total_count"], int):
            return {"total_count": full_data["total_count"], "note": "Authoritative global count from GitHub."}
        return {"partial_count": len(data), "note": "Local count of provided subset. This may not represent the global total."}

    if op == "sum" and metric:
        total = sum(item.get(metric, 0) for item in data if isinstance(item, dict) and isinstance(item.get(metric), (int, float)))
        return {f"total_{metric}": total}

    if op == "max" and metric:
        if not data:
            return {"max": None}
        best = max(data, key=lambda x: x.get(metric, 0) if isinstance(x, dict) and isinstance(x.get(metric), (int, float)) else -float('inf'))
        return {"max_item": best}

    if op == "min" and metric:
        if not data:
            return {"min": None}
        worst = min(data, key=lambda x: x.get(metric, 0) if isinstance(x, dict) and isinstance(x.get(metric), (int, float)) else float('inf'))
        return {"min_item": worst}

    if op in ["top_n", "latest_n"]:
        field = metric if op == "top_n" else "updated_at"
        if not sort_field:
            try:
                data.sort(key=lambda x: x.get(field, 0) if isinstance(x, dict) and x.get(field) is not None else 0, reverse=True)
            except Exception:
                pass
        return {"items": data[:limit]}

    if op == "select_fields":
        field_str = metric or reduction.get("field", "")
        fields = [f.strip() for f in field_str.split(",") if f.strip()]
        if fields:
            reduced = []
            for item in data[:limit]:
                if isinstance(item, dict):
                    reduced.append({k: v for k, v in item.items() if k in fields})
                else:
                    reduced.append(item)
            return {"items": reduced}
        return {"items": data[:limit]}

    if op == "aggregate" and metric == "language":
        # Only count by primary language (bytes are unavailable)
        lang_totals: dict[str, int] = {}
        for item in data:
            if isinstance(item, dict):
                lang = item.get("language")
                if lang:
                    if "bytes" in item:
                        lang_totals[lang] = lang_totals.get(lang, 0) + item.get("bytes", 0)
                    else:
                        # Repository frequency count
                        lang_totals[lang] = lang_totals.get(lang, 0) + 1

        sorted_langs = [
            {"language": k, "repository_count": v}
            for k, v in sorted(lang_totals.items(), key=lambda item: item[1], reverse=True)
        ]
        return {
            "aggregated_languages": sorted_langs,
            "_note": "Aggregated by repository primary language count (byte breakdown unavailable via MCP).",
        }
    return {"items": data[:limit]}


def _project_result(data: Any, capability: str | None, operation: str | None, sort_metric: str | None = None) -> Any:
    """
    Capability-aware field projection.
    Projects ONLY the fields required to answer the current operation.
    Never removes a field required by the active capability.
    Applied AFTER reduction so only the final items are projected.
    """
    if capability is None or data is None:
        return data

    # REPOSITORIES capability
    if capability == "REPOSITORIES":
        if operation in ("top_n", "select_fields"):
            # Keep only name + the sort metric
            keep_metric = sort_metric or "forks"
            if keep_metric in ("stars", "stargazers_count"):
                keep_metric = "stars"
            elif keep_metric in ("forks", "forks_count"):
                keep_metric = "forks"

            if isinstance(data, dict) and "items" in data:
                projected = []
                for item in data["items"]:
                    if isinstance(item, dict):
                        p = {"name": item.get("name"), keep_metric: item.get(keep_metric) or item.get("forks_count") or item.get("stargazers_count") or 0}
                        if "_sort_note" in item:
                            p["_sort_note"] = item["_sort_note"]
                        projected.append(p)
                return {"items": projected}
            elif isinstance(data, list):
                projected = []
                for item in data:
                    if isinstance(item, dict):
                        p = {"name": item.get("name"), keep_metric: item.get(keep_metric) or item.get("forks_count") or item.get("stargazers_count") or 0}
                        if "_sort_note" in item:
                            p["_sort_note"] = item["_sort_note"]
                        projected.append(p)
                return projected
        elif operation == "count":
            # Already compact — pass through
            return data
        elif operation in ("sum", "max", "min"):
            # Already scalar — pass through
            return data
        def _slim_repo(item):
            if isinstance(item, dict):
                res = {
                    "name": item.get("name"),
                    "full_name": item.get("full_name") or item.get("name"),
                    "language": item.get("language"),
                }
                if sort_metric in ("stars", "stargazers_count"):
                    res["stars"] = item.get("stars") or item.get("stargazers_count")
                elif sort_metric in ("forks", "forks_count"):
                    res["forks"] = item.get("forks") or item.get("forks_count")
                elif sort_metric == "updated":
                    res["updatedAt"] = item.get("updated_at") or item.get("updatedAt")
                
                res["url"] = item.get("html_url") or item.get("url")
                return res
            return item
        if isinstance(data, dict) and "items" in data:
            return {"items": [_slim_repo(i) for i in data["items"]]}
        if isinstance(data, list):
            return [_slim_repo(i) for i in data]

    # PULL_REQUESTS capability
    elif capability == "PULL_REQUESTS":
        pr_fields = {"number", "title", "state", "repository", "createdAt", "url"}
        def _slim_pr(item):
            if isinstance(item, dict):
                return {k: v for k, v in item.items() if k in pr_fields}
            return item
        if isinstance(data, dict) and "items" in data:
            return {"items": [_slim_pr(i) for i in data["items"]]}
        if isinstance(data, list):
            return [_slim_pr(i) for i in data]

    # ISSUES capability
    elif capability == "ISSUES":
        issue_fields = {"number", "title", "state", "createdAt", "url"}
        def _slim_issue(item):
            if isinstance(item, dict):
                return {k: v for k, v in item.items() if k in issue_fields}
            return item
        if isinstance(data, dict) and "items" in data:
            return {"items": [_slim_issue(i) for i in data["items"]]}
        if isinstance(data, list):
            return [_slim_issue(i) for i in data]

    # LANGUAGES capability
    elif capability == "LANGUAGES":
        # aggregated_languages already compact; slim repo list to language only
        if isinstance(data, dict) and "aggregated_languages" in data:
            return data  # already compact
        def _slim_lang(item):
            if isinstance(item, dict):
                return {"name": item.get("name"), "language": item.get("language")}
            return item
        if isinstance(data, dict) and "items" in data:
            return {"items": [_slim_lang(i) for i in data["items"]]}
        if isinstance(data, list):
            return [_slim_lang(i) for i in data]

    # README_CODE capability
    elif capability == "README_CODE":
        # README content can be large — apply hard character budget
        if isinstance(data, dict):
            content = data.get("content", "")
            truncated = False
            if content and len(content) > MAX_README_CHARS:
                content = content[:MAX_README_CHARS]
                truncated = True
            return {
                "status": "PARTIAL" if truncated else "FOUND",
                "content": content,
                "truncated": truncated,
                "source": "README.md"
            } if content else data
        if isinstance(data, str):
            content = data
            truncated = False
            if len(content) > MAX_README_CHARS:
                content = content[:MAX_README_CHARS]
                truncated = True
            return {
                "status": "PARTIAL" if truncated else "FOUND",
                "content": content,
                "truncated": truncated,
                "source": "README.md"
            }

    # ACTIVITY capability — keep only commit essentials
    elif capability == "ACTIVITY":
        commit_fields = {"sha", "message", "author", "date", "url"}
        def _slim_commit(item):
            if isinstance(item, dict):
                return {k: v for k, v in item.items() if k in commit_fields}
            return item
        if isinstance(data, list):
            return [_slim_commit(i) for i in data]
        if isinstance(data, dict) and "items" in data:
            return {"items": [_slim_commit(i) for i in data["items"]]}

    return data


def _extract_content(parsed: dict, reduction: dict | None) -> Any:
    """
    Extract the actual content from an MCP response.
    GitHub MCP wraps results in result.content[].text or result.content[].
    """
    result = parsed.get("result", parsed)

    content = result.get("content") if isinstance(result, dict) else None
    if isinstance(content, list) and content:
        first = content[0]
        if isinstance(first, dict) and first.get("type") == "text":
            text = first.get("text", "")
            try:
                data = json.loads(text)
            except Exception:
                return text

            items = data.get("items", data) if isinstance(data, dict) else data
            return _apply_reduction(items, reduction, full_data=data if isinstance(data, dict) else None)
        return first

    items = result.get("items", result) if isinstance(result, dict) else result
    return _apply_reduction(items, reduction, full_data=result if isinstance(result, dict) else None)


async def _execute_mcp_direct(tool_name: str, arguments: dict[str, Any], reduction: dict | None = None) -> dict[str, Any]:
    """
    Execute a raw MCP tool directly (used by repo_resolver and internal workflows).

    Signature: _execute_mcp_direct(tool_name, arguments, reduction=None)
    Raises RuntimeError on failure (so callers can distinguish ERROR from NOT_FOUND).
    """
    try:
        raw = await mcp_request(
            method="tools/call",
            params={"name": tool_name, "arguments": arguments},
        )
        parsed = parse_mcp_response(raw)

        if parsed.get("error") and not parsed.get("result"):
            raise RuntimeError(parsed.get("message", "MCP tool returned an error."))

        content = _extract_content(parsed, reduction)
        return _normalize_obj(content)
    except Exception as e:
        logger.error("Raw MCP execution error (%s): %s", tool_name, str(e))
        raise


# ---------------------------------------------------------------------------
# Capability Resolver
# ---------------------------------------------------------------------------
# Maps blocked/unavailable tool names to deterministic available workflows.
# Only maps tools where the semantic intent is truly preserved.

def _resolve_capability(tool_name: str, args: dict[str, Any]) -> tuple[str, dict[str, Any]] | None:
    """
    If tool_name is blocked or unavailable, return a (replacement_tool, replacement_args) tuple.
    Returns None if no deterministic mapping exists.

    Rules:
    - Only map when the semantic intent is FULLY preserved.
    - Never guess. If uncertain, return None (capability_unavailable).
    - Preserve the user's username, filters, sorting, and repository info.
    """
    # list_repositories(owner=<username>) → search_repositories(query="user:<username>")
    if tool_name == "list_repositories":
        owner = args.get("owner") or args.get("username", "")
        if owner:
            sort = args.get("sort", "")
            query = f"user:{owner}"
            if sort in ("stars", "stargazers"):
                query += " sort:stars"
            elif sort in ("updated", "pushed"):
                query += " sort:updated"
            elif sort in ("forks",):
                query += " sort:forks"
            new_args = {"query": query}
            logger.info(
                "[CAPABILITY RESOLVER] Mapped list_repositories(owner=%s) → search_repositories(query=%s)",
                owner, query
            )
            return "search_repositories", new_args

    return None


def _enforce_pr_query_filter(tool_name: str, args: dict[str, Any], capability: str | None) -> dict[str, Any]:
    """
    For PULL_REQUESTS capability, prefer search_pull_requests over search_issues.
    The connected MCP server has a dedicated search_pull_requests tool already scoped to is:pr.
    If the LLM calls search_issues for PRs, log a warning but still enforce is:pr in the query.
    """
    if capability == Capability.PULL_REQUESTS and tool_name == "search_issues":
        query = args.get("query", "")
        if "is:pr" not in query.lower():
            args = dict(args)
            args["query"] = f"is:pr {query}".strip()
            logger.warning("[PR FILTER ENFORCED] search_issues used for PULL_REQUESTS — added 'is:pr'. Prefer search_pull_requests.")
        else:
            logger.warning("[PR TOOL NOTE] search_pull_requests is preferred over search_issues for PR queries.")
    return args


def _log_pr_query_constraints(tool_name: str, args: dict[str, Any], capability: str | None) -> None:
    """Log sanitized query constraints for PR searches to prove enforcement."""
    if tool_name in ("search_issues", "search_pull_requests") and capability == Capability.PULL_REQUESTS:
        import re as _re
        query = args.get("query", "")
        constraints = []
        if "is:pr" in query.lower():
            constraints.append("is:pr")
        author_match = _re.search(r'author:([\S]+)', query)
        if author_match:
            constraints.append(f"author:{author_match.group(1)}")
        repo_match = _re.search(r'repo:([\S]+)', query)
        if repo_match:
            constraints.append(f"repo:{repo_match.group(1)}")
        sort_match = _re.search(r'sort:([\S]+)', query)
        if sort_match:
            constraints.append(f"sort:{sort_match.group(1)}")
        logger.info(
            "[PR QUERY] tool=%s capability=%s query_constraints=%s",
            tool_name, capability, constraints
        )


def _build_evidence(
    status: str,
    capability: str | None,
    tool: str,
    query_or_args: dict | None = None,
    result_count: int | None = None,
    complete: bool = True,
    error: str | None = None,
) -> dict:
    """Build a compact evidence state dict attached to tool results."""
    ev = {
        "evidence_status": status,    # SUCCESS, SUCCESS_EMPTY, NOT_FOUND, AMBIGUOUS, CAPABILITY_UNAVAILABLE, EVIDENCE_INSUFFICIENT, MCP_ERROR, PARTIAL
        "source": "mcp",
        "capability": capability or "UNKNOWN",
        "tool": tool,
        "complete": complete,
    }
    if result_count is not None:
        ev["result_count"] = result_count
    if error:
        ev["error"] = error
    return ev


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

async def execute_tool(tool_name: str, arguments: dict[str, Any], reduction: dict | None = None) -> dict[str, Any]:
    """
    Execute an MCP tool by name with the given arguments.

    Security:
    1. Verify tool is in allow-list — if not, attempt capability resolution first
    2. Verify tool is read-only
    3. Validate required arguments
    4. Execute MCP request
    5. Normalize and truncate result
    6. Attach evidence state

    Returns:
        {
            "success": True/False,
            "tool_name": str,
            "result": ...,
            "error": str | None,
            "evidence": dict,
        }
    """
    capability = reduction.get("capability") if reduction else None

    # 0. Contract Enforcement
    if reduction:
        cap = reduction.get("capability")
        op = reduction.get("operation")
        metric = reduction.get("metric")
        scope = reduction.get("scope")
        try:
            validate_contract(cap, op, metric, scope)
            # Safe deterministic normalization
            if metric == "stars":
                reduction["metric"] = "stargazers_count"
            if metric == "forks":
                reduction["metric"] = "forks_count"
        except ValueError as e:
            err_msg = str(e)
            logger.warning("[CONTRACT VIOLATION] capability=%s operation=%s metric=%s: %s", cap, op, metric, err_msg)
            # Check for language byte limitation
            if "CAPABILITY_LIMITATION" in err_msg:
                return {
                    "success": False,
                    "tool_name": tool_name,
                    "result": None,
                    "error": err_msg,
                    "evidence": _build_evidence(
                        "CAPABILITY_UNAVAILABLE", cap, tool_name, error=err_msg
                    ),
                }
            return {
                "success": False,
                "tool_name": tool_name,
                "result": None,
                "error": err_msg,
                "evidence": _build_evidence("MCP_ERROR", cap, tool_name, error=err_msg),
            }

    # 1. Check allow-list — if blocked, attempt capability resolution
    if not is_tool_allowed(tool_name):
        logger.warning("[TOOL NOT ALLOWED] %s — attempting capability resolution", tool_name)

        resolved = _resolve_capability(tool_name, arguments)
        if resolved:
            replacement_tool, replacement_args = resolved
            logger.info(
                "[CAPABILITY RESOLVER] %s → %s | args=%s",
                tool_name, replacement_tool, list(replacement_args.keys())
            )
            # Recurse with replacement (pass capability from reduction)
            new_reduction = dict(reduction) if reduction else {}
            new_reduction["_resolved_from"] = tool_name
            return await execute_tool(replacement_tool, replacement_args, new_reduction if new_reduction else None)
        else:
            # No equivalent workflow — return honest limitation immediately
            msg = (
                f"CAPABILITY_UNAVAILABLE: The tool '{tool_name}' is not available in the connected "
                f"GitHub MCP server. No equivalent workflow exists for the requested operation. "
                f"Please inform the user of this limitation."
            )
            logger.warning("[CAPABILITY_UNAVAILABLE] %s — no resolution found", tool_name)
            return {
                "success": False,
                "tool_name": tool_name,
                "result": None,
                "error": msg,
                "evidence": _build_evidence("CAPABILITY_UNAVAILABLE", capability, tool_name, error=msg),
            }

    tool_def = get_tool(tool_name)
    if not tool_def:
        return {
            "success": False,
            "tool_name": tool_name,
            "result": None,
            "error": f"Tool '{tool_name}' definition not found.",
            "evidence": _build_evidence("MCP_ERROR", capability, tool_name, error="Tool definition not found"),
        }

    # 2. Read-only check (belt-and-suspenders)
    if not tool_def.get("readonly", True):
        logger.error("Attempted non-readonly tool execution: %s", tool_name)
        return {
            "success": False,
            "tool_name": tool_name,
            "result": None,
            "error": "This tool is not permitted (write operations are disabled).",
            "evidence": _build_evidence("MCP_ERROR", capability, tool_name, error="Write tool blocked"),
        }

    # 3. Enforce PR query filter before argument validation + log constraints
    arguments = _enforce_pr_query_filter(tool_name, arguments, capability)
    _log_pr_query_constraints(tool_name, arguments, capability)

    # 4. Validate required args
    schema = tool_def.get("input_schema", {})
    required = schema.get("required", [])
    for field in required:
        if field not in arguments or arguments[field] is None:
            return {
                "success": False,
                "tool_name": tool_name,
                "result": None,
                "error": f"Missing required argument: {field}",
                "evidence": _build_evidence("MCP_ERROR", capability, tool_name, error=f"Missing arg: {field}"),
            }

    # 5. Repository resolution for tools that require owner/repo
    from app.agent.repo_resolver import resolve_repository
    import re

    needs_repo_resolution = False
    repo_query = None

    if reduction and reduction.get("scope") == "specific_repository":
        needs_repo_resolution = True

    # NOTE: get_repository does NOT exist in the GitHub Remote MCP server.
    # Repository resolution is handled by repo_resolver via search_repositories.
    if tool_name in ["get_file_contents", "list_commits", "list_branches", "list_issues", "list_pull_requests"]:
        owner = arguments.get("owner", "")
        repo = arguments.get("repo", arguments.get("name", ""))  # prefer 'repo'; fall back to 'name'
        if repo:
            repo_query = f"{owner}/{repo}" if owner else repo
            needs_repo_resolution = True

    if tool_name in ["search_issues", "search_pull_requests", "search_repositories"] and "query" in arguments:
        match = re.search(r'repo:([^\s]+)', arguments["query"])
        if match:
            repo_query = match.group(1)
            needs_repo_resolution = True

    if needs_repo_resolution and repo_query:
        logger.info("[REPO RESOLUTION] Resolving repository for query: %s", repo_query)
        username = reduction.get("username") if reduction else None
        resolved = await resolve_repository(repo_query, _execute_mcp_direct, username=username)

        if resolved.state != "FOUND":
            # Map resolution state to evidence status — preserve distinction
            if resolved.state == "NOT_FOUND":
                ev_status = "NOT_FOUND"
                msg = f"Repository Resolution: {resolved.state}: {resolved.message}"
            elif resolved.state == "AMBIGUOUS":
                ev_status = "AMBIGUOUS"
                msg = f"Repository Resolution: {resolved.state}: {resolved.message}"
            else:
                # ERROR or ACCESS_DENIED — never convert to NOT_FOUND
                ev_status = "MCP_ERROR"
                msg = f"Repository Resolution: {resolved.state}: {resolved.message}"

            logger.warning(
                "[REPO RESOLUTION] status=%s tool=%s repo_query=%s",
                resolved.state, tool_name, repo_query
            )
            return {
                "success": False,
                "tool_name": tool_name,
                "result": None,
                "error": msg,
                "evidence": _build_evidence(ev_status, capability, tool_name, error=msg),
            }

        # Update arguments with canonical repository identity.
        # get_file_contents uses 'owner' and 'repo' (verified against actual MCP schema).
        if tool_name in ["get_file_contents", "list_commits", "list_branches", "list_issues", "list_pull_requests"]:
            arguments["owner"] = resolved.owner
            # Always set 'repo' — that is the actual MCP parameter name
            arguments["repo"] = resolved.name
            # Remove legacy 'name' key if it was passed by the LLM
            arguments.pop("name", None)

            # README chain: ensure path is set
            if tool_name == "get_file_contents":
                cap = reduction.get("capability") if reduction else capability
                if cap == "README_CODE":
                    if "path" not in arguments or not arguments.get("path"):
                        arguments["path"] = "README.md"

        if tool_name in ["search_issues", "search_pull_requests", "search_repositories"] and "query" in arguments:
            arguments["query"] = re.sub(r'repo:[^\s]+', f'repo:{resolved.full_name}', arguments["query"])

    # 6. Execute MCP
    try:
        # Sanitize args for logging: show keys + query value (no tokens)
        safe_args_log = list(arguments.keys())
        if "query" in arguments:
            safe_args_log = {"keys": list(arguments.keys()), "query": arguments["query"]}
        logger.info(
            "[MCP EXECUTE] tool=%s capability=%s args=%s",
            tool_name, capability, safe_args_log
        )
        raw = await mcp_request(
            method="tools/call",
            params={"name": tool_name, "arguments": arguments},
        )
        parsed = parse_mcp_response(raw)

        if parsed.get("error") and not parsed.get("result"):
            raise RuntimeError(parsed.get("message", "MCP tool returned an error."))

        # 7. Normalize result
        content = _extract_content(parsed, reduction)

        # 7a. README diagnostic: inspect what get_file_contents actually returned
        if tool_name == "get_file_contents" and capability == "README_CODE":
            _raw_type = type(content).__name__
            _has_content_field = isinstance(content, dict) and "content" in content
            _content_len = 0
            if isinstance(content, dict):
                _content_len = len(content.get("content", ""))
            elif isinstance(content, str):
                _content_len = len(content)
            logger.info(
                "[README DIAGNOSTIC] raw_type=%s has_content_field=%s content_length=%d keys=%s",
                _raw_type, _has_content_field, _content_len,
                list(content.keys())[:10] if isinstance(content, dict) else "N/A"
            )

            # Handle GitHub MCP file response shapes:
            # Shape 1: dict with {content: "base64...", encoding: "base64", download_url: "..."}
            # Shape 2: dict with {content: "actual text", ...}
            # Shape 3: raw string (the actual file text)
            if isinstance(content, dict):
                encoding = content.get("encoding", "")
                raw_content = content.get("content", "")
                download_url = content.get("download_url") or content.get("html_url") or content.get("url")

                if encoding == "base64" and raw_content:
                    import base64
                    try:
                        decoded = base64.b64decode(raw_content).decode("utf-8", errors="replace")
                        content = {"content": decoded, "source": "README.md", "status": "FOUND"}
                        logger.info("[README DIAGNOSTIC] Decoded base64 content, length=%d", len(decoded))
                    except Exception as _e:
                        logger.warning("[README DIAGNOSTIC] base64 decode failed: %s", _e)
                        content = {
                            "content": f"README file exists but content could not be decoded. View at: {download_url}" if download_url else "README content unavailable.",
                            "source": "README.md",
                            "status": "PARTIAL"
                        }
                elif raw_content and len(raw_content) > 20:
                    # Actual text content present
                    content = {"content": raw_content, "source": "README.md", "status": "FOUND"}
                elif download_url and not raw_content:
                    # Only a URL, no content — honestly report
                    content = {
                        "content": f"The MCP response contains a link to the README but not its text content. View it at: {download_url}",
                        "source": "README.md",
                        "status": "PARTIAL",
                        "download_url": download_url,
                    }
                    logger.warning("[README DIAGNOSTIC] Only download_url returned, no text content")

        normalized = _normalize_obj(content)

        raw_bytes = len(json.dumps(normalized, default=str))

        # 7b. Capability-aware projection — project ONLY fields required by the operation
        op = reduction.get("operation") if reduction else None
        sort_metric = reduction.get("metric") or reduction.get("sort") if reduction else None
        projected = _project_result(normalized, capability, op, sort_metric)
        projected_bytes = len(json.dumps(projected, default=str))

        logger.info(
            "[MCP NORMALIZE] tool=%s raw_bytes=%d projected_bytes=%d projected_tokens≈%d",
            tool_name, raw_bytes, projected_bytes, projected_bytes // 4
        )

        # Count results for evidence (from projected data)
        result_count = None
        if isinstance(projected, list):
            result_count = len(projected)
        elif isinstance(projected, dict):
            if "total_count" in projected:
                result_count = projected["total_count"]
            elif "items" in projected:
                result_count = len(projected["items"])
            elif "partial_count" in projected:
                result_count = projected["partial_count"]
            elif "count" in projected:
                result_count = projected["count"]

        # 8. Final size guard — truncate only if still oversized after projection
        result_str = json.dumps(projected, default=str)
        if len(result_str) > MAX_RESULT_CHARS:
            logger.warning(
                "Tool result for %s still large after projection (%d chars) — truncating to %d",
                tool_name, len(result_str), MAX_RESULT_CHARS,
            )
            result_str = result_str[:MAX_RESULT_CHARS] + "... [result truncated]"
            projected = result_str

        # 8a. README evidence validation — do NOT mark SUCCESS unless actual content retrieved
        if capability == "README_CODE" and tool_name == "get_file_contents":
            _readme_content = ""
            _readme_status = ""
            if isinstance(projected, dict):
                _readme_content = projected.get("content", "")
                _readme_status = projected.get("status", "")
            elif isinstance(projected, str):
                _readme_content = projected

            # Detect placeholder/metadata-only responses
            _is_placeholder = False
            if not _readme_content or len(_readme_content.strip()) < 20:
                _is_placeholder = True
            elif _readme_status in ("PARTIAL",) and not _readme_content.strip():
                _is_placeholder = True
            # Check for download-URL-only or metadata-only responses
            elif _readme_content.strip().startswith("The MCP response contains a link"):
                _is_placeholder = True
            elif _readme_content.strip().startswith("README file exists but"):
                _is_placeholder = True

            if _is_placeholder:
                logger.warning(
                    "[README EVIDENCE] Content is empty/placeholder (len=%d). Marking CONTENT_UNAVAILABLE.",
                    len(_readme_content) if _readme_content else 0
                )
                evidence = _build_evidence(
                    "CONTENT_UNAVAILABLE", capability, tool_name,
                    result_count=result_count, complete=False,
                    error="README content not available or too small to be meaningful.",
                )
                projected = {
                    "status": "CONTENT_UNAVAILABLE",
                    "content_available": False,
                    "reason": "The MCP server returned metadata or a placeholder instead of actual README text content.",
                }
                return {
                    "success": False,
                    "tool_name": tool_name,
                    "result": projected,
                    "error": "README content unavailable from MCP.",
                    "evidence": evidence,
                }
            else:
                # Genuine README content — mark SUCCESS
                evidence = _build_evidence(
                    "SUCCESS", capability, tool_name,
                    result_count=result_count, complete=True,
                )
        else:
            evidence = _build_evidence(
                "SUCCESS_WITH_DATA" if result_count and result_count > 0 else "SUCCESS_EMPTY", capability, tool_name,
                result_count=result_count, complete=True,
            )

        logger.info(
            "[MCP RESULT] tool=%s capability=%s result_count=%s evidence_status=%s",
            tool_name, capability, result_count, evidence.get("evidence_status", "SUCCESS")
        )

        return {
            "success": True,
            "tool_name": tool_name,
            "result": projected,
            "error": None,
            "evidence": evidence,
        }

    except Exception as e:
        logger.error("Tool execution error (%s): %s", tool_name, str(e))
        return {
            "success": False,
            "tool_name": tool_name,
            "result": None,
            "error": f"GitHub could not be reached for '{tool_name}'. Please try again.",
            "evidence": _build_evidence("MCP_ERROR", capability, tool_name, error=str(e)),
        }
