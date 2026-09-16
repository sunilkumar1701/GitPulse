"""
Tool registry — centralized registry of MCP tools available to the agent.

Populated at startup from the actual MCP tools/list response.
Maintains a read-only allow-list.
No tool names are hard-coded or invented here.
"""

import logging
import threading
from typing import Any
from app.agent.semantic_router import Capability

logger = logging.getLogger(__name__)

_lock = threading.Lock()

# Registered tools: name -> tool definition
_registry: dict[str, dict[str, Any]] = {}

# Friendly UI labels for known tool name patterns
_UI_LABEL_MAP: dict[str, str] = {
    "get_me": "Checking your GitHub profile",
    "get_user": "Looking up GitHub profile",
    "list_repos": "Fetching repositories",
    "list_repositories": "Fetching repositories",
    "get_repo": "Checking repository details",
    "get_repository": "Checking repository details",
    "search_repositories": "Searching repositories",
    "search_users": "Searching GitHub users",
    "list_issues": "Checking GitHub issues",
    "get_issue": "Reading issue details",
    "search_issues": "Searching GitHub issues",
    "list_pull_requests": "Checking pull requests",
    "search_pull_requests": "Searching pull requests",
    "get_pull_request": "Reading pull request details",
    "list_commits": "Reviewing recent commits",
    "get_commit": "Checking commit details",
    "get_file_contents": "Reading repository content",
    "list_branches": "Listing branches",
    "list_tags": "Listing tags",
    "get_code_scanning_alert": "Checking code security",
    "search_code": "Searching repository code",
}

# Prefix-based fallbacks
_PREFIX_LABELS: list[tuple[str, str]] = [
    ("get_me", "Checking your GitHub profile"),
    ("list_issue", "Checking GitHub issues"),
    ("get_issue", "Reading issue details"),
    ("list_pull", "Checking pull requests"),
    ("get_pull", "Reading pull request details"),
    ("list_commit", "Reviewing recent commits"),
    ("get_commit", "Checking commit details"),
    ("list_repo", "Fetching repositories"),
    ("get_repo", "Checking repository details"),
    ("search_repo", "Searching repositories"),
    ("search_user", "Searching GitHub users"),
    ("get_user", "Looking up GitHub profile"),
    ("get_file", "Reading repository content"),
    ("list_branch", "Listing branches"),
    ("search_code", "Searching repository code"),
]

# Tools that are explicitly blocked (write operations)
_BLOCKED_TOOLS: set[str] = {
    "create_issue",
    "update_issue",
    "close_issue",
    "delete_issue",
    "create_pull_request",
    "merge_pull_request",
    "close_pull_request",
    "create_repository",
    "delete_repository",
    "update_repository",
    "create_file",
    "update_file",
    "delete_file",
    "create_branch",
    "delete_branch",
    "push_files",
    "create_or_update_file",
    "fork_repository",
    "create_release",
    "create_tag",
    "add_issue_comment",
    "update_issue_comment",
    "delete_issue_comment",
}


def get_ui_label(tool_name: str) -> str:
    """Return a friendly UI label for a tool name."""
    if tool_name in _UI_LABEL_MAP:
        return _UI_LABEL_MAP[tool_name]
    for prefix, label in _PREFIX_LABELS:
        if tool_name.startswith(prefix):
            return label
    return f"Consulting GitHub ({tool_name})"


def register_tools_from_mcp(tools: list[dict[str, Any]]) -> None:
    """
    Populate the registry from the MCP tools/list response.

    Only allows read-only tools (blocks write tools by name pattern).
    """
    global _registry
    with _lock:
        _registry = {}
        allowed = 0
        blocked = 0
        for tool in tools:
            name = tool.get("name", "")
            if not name:
                continue
            if _is_write_tool(name):
                blocked += 1
                logger.debug("Tool blocked (write): %s", name)
                continue
            _registry[name] = {
                "name": name,
                "description": tool.get("description", ""),
                "input_schema": tool.get("inputSchema", {}),
                "ui_label": get_ui_label(name),
                "readonly": True,
                "source": "github_mcp",
            }
            allowed += 1

        logger.info(
            "Tool registry: %d allowed, %d blocked (write operations)", allowed, blocked
        )


def _is_write_tool(name: str) -> bool:
    """Return True if the tool name indicates a write operation."""
    if name in _BLOCKED_TOOLS:
        return True
    write_prefixes = ("create_", "update_", "delete_", "push_", "merge_", "close_", "fork_", "add_issue_comment")
    return any(name.startswith(p) for p in write_prefixes)


def get_tool(name: str) -> dict[str, Any] | None:
    """Return a tool definition by name, or None if not found/blocked."""
    with _lock:
        return _registry.get(name)


def get_all_tools() -> list[dict[str, Any]]:
    """Return all registered tools."""
    with _lock:
        return list(_registry.values())


def get_groq_tool_definitions() -> list[dict[str, Any]]:
    """
    Return the SINGLE compact gateway tool definition for Groq.
    This saves thousands of tokens by not sending all schemas.
    """
    return [
        {
            "type": "function",
            "function": {
                "name": "github_mcp",
                "description": "Execute a GitHub MCP capability. Look at the AVAILABLE MCP TOOLS catalog in your system prompt to see the exact tool_name to use.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "tool_name": { "type": "string", "description": "The capability to execute, e.g. list_repositories, search_issues" },
                        "owner": { "type": "string" },
                        "repo": { "type": "string" },
                        "path": { "type": "string" },
                        "query": { "type": "string" },
                        "sort": { "type": "string" },
                        "reduction_operation": { "type": "string", "description": "e.g., sum, top_n, latest_n, aggregate" },
                        "reduction_metric": { "type": "string", "description": "e.g., stars, language, created_at" },
                        "reduction_limit": { "type": "integer" },
                        "reduction_sort": { "type": "string" },
                        "reduction_group_by": { "type": "string" }
                    },
                    "required": ["tool_name"]
                },
            },
        }
    ]


# Mapping of semantic capability to tool signature descriptions for the LLM.
# IMPORTANT: Only actual available (non-blocked) tools are listed here.
# list_repositories is BLOCKED — the backend resolves it to search_repositories automatically.
_CAPABILITY_DEFINITIONS = {
    Capability.PROFILE: (
        "- get_user(username: string)\n"
        "  → Retrieves a GitHub user profile."
    ),
    Capability.REPOSITORIES: (
        "- search_repositories(query: string)\n"
        "  → To list all repositories for a user: query='user:<username>'\n"
        "  → To search by topic: query='user:<username> topic:<topic>'\n"
        "  → Supports sort param: sort:stars, sort:forks, sort:updated\n"
        "  NOTE: Do NOT request list_repositories — the backend handles this automatically."
    ),
    Capability.LANGUAGES: (
        "- search_repositories(query: string)\n"
        "  → Returns primary language per repository (the 'language' field).\n"
        "  → Use reduction_operation='aggregate' and reduction_metric='language' to count\n"
        "    how many repositories use each primary language.\n"
        "  CRITICAL LIMITATION: Language BYTE data and percentage breakdowns are NOT available\n"
        "  via the connected MCP server. Do NOT fabricate byte counts or percentages.\n"
        "  Do NOT substitute dashboard language percentages for this.\n"
        "  If asked for byte-level language data, state this limitation clearly."
    ),
    Capability.README_CODE: (
        "- get_file_contents(owner: string, repo: string, path: string)\n"
        "  → path='README.md' for README retrieval.\n"
        "  → Requires exact owner and repo. Resolve the repository first if only a name is given.\n"
        "  → Content is base64-encoded; the backend decodes it automatically."
    ),
    Capability.PULL_REQUESTS: (
        "- search_pull_requests(query: string)\n"
        "  → PREFERRED tool for PR searches. Already scoped to is:pr by the MCP server.\n"
        "  → For user's latest PR: query='author:<username> sort:created-desc'\n"
        "  → For PRs in a specific repo: query='repo:<owner>/<repo> sort:created-desc'\n"
        "  → Optional: owner, repo, sort, order, page, perPage params available.\n"
        "  → The result's total_count is authoritative. Do not claim 'no PRs' unless total_count=0.\n"
        "  → Alternatively: search_issues(query='is:pr author:<username>') also works but is less preferred."
    ),
    Capability.ISSUES: (
        "- search_issues(query: string)\n"
        "  → Use to search for GitHub Issues (NOT pull requests).\n"
        "  → REQUIRED: include 'is:issue' in the query to exclude PRs from results.\n"
        "  → For issues in a specific repo: query='is:issue repo:<owner>/<repo>'\n"
        "  → For the authenticated user's issues: query='is:issue author:<username>'\n"
        "  → Optional: owner, repo, sort, order, page, perPage params available.\n"
        "  → Or use list_issues(owner, repo) for all issues in one repository.\n"
        "  → The result's total_count is authoritative."
    ),
    Capability.ACTIVITY: (
        "- list_commits(owner: string, repo: string, author: string [optional])\n"
        "  → Lists commits for a specific repository.\n"
        "  → Requires owner and repo. Resolve repository first if only a name is given."
    ),
}

def get_compact_tool_catalog(active_capabilities: list[str]) -> str:
    """
    Return an ultra-compact text list of ONLY the activated capabilities.
    """
    if not active_capabilities:
        return ""

    lines = []
    for cap in active_capabilities:
        if cap in _CAPABILITY_DEFINITIONS:
            lines.append(_CAPABILITY_DEFINITIONS[cap])

    header = "Available tool_names for github_mcp:\n"
    return header + "\n\n".join(lines)


def is_tool_allowed(name: str) -> bool:
    """Check if a tool is in the allow-list."""
    with _lock:
        return name in _registry


def has_tools() -> bool:
    """Return True if the registry has at least one tool."""
    with _lock:
        return len(_registry) > 0
