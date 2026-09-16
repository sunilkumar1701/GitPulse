"""
Capability Contract — backend source of truth for what each capability can do.

Every high-level semantic capability has an explicit contract defining:
  - supported MCP tools/workflows (from actual loaded tools, not assumed GitHub REST API)
  - required arguments
  - required query filters
  - supported operations
  - output fields
  - sorting rules
  - aggregation rules
  - known limitations
  - failure states

IMPORTANT: These contracts reflect the ACTUAL tools loaded from the GitHub Remote MCP server.

Known unavailable tools (blocked as write operations or not loaded):
  - list_repositories  (NOT in allow-list — use search_repositories instead)
  - analyze_languages  (NOT loaded — language bytes unavailable via MCP)
  - create_*, update_*, delete_*, push_*, merge_*, close_*, fork_*, add_issue_comment

Language byte data limitation:
  The GitHub Remote MCP server does NOT expose a per-repository language byte breakdown
  tool (e.g. GET /repos/{owner}/{repo}/languages). The only language data available via
  MCP is the primary_language field returned by search_repositories/get_repository.
  Do NOT fabricate byte counts or percentages. State the limitation explicitly.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel


class CapabilityContract(BaseModel):
    """
    Defines the supported dataset operations and constraints for a specific capability.
    Acts as the backend source of truth to prevent LLM hallucinations.
    """
    dataset_scope: str
    supported_scopes: List[str]
    supported_operations: List[str]
    supported_metrics: List[str]
    required_fields: List[str]
    pagination_support: bool
    native_total_support: bool
    native_sort_support: bool
    native_filter_support: bool
    # Actual MCP tools available (verified against tool registry at startup)
    preferred_mcp_tools: List[str]
    fallback_mcp_tools: List[str]
    # Required query filters (must be present in the MCP request)
    required_query_filters: Dict[str, str]
    # Known limitations that must be stated explicitly if the request cannot be satisfied
    known_limitations: List[str]
    read_only: bool
    scope_requirements: Dict[str, str]


# ---------------------------------------------------------------------------
# REPOSITORIES capability
# ---------------------------------------------------------------------------
# list_repositories is BLOCKED (not in allow-list).
# Use search_repositories(query="user:<username>") for all-user-repository workflows.
# get_repository(owner, name) for specific repository lookups.
REPOSITORIES_CONTRACT = CapabilityContract(
    dataset_scope="GitHub Repositories",
    supported_scopes=["all_user_repositories", "specific_repository"],
    supported_operations=["count", "sum", "max", "min", "top_n", "latest_n", "sort", "filter", "select_fields"],
    supported_metrics=["stars", "forks", "language", "updated_at", "stargazers_count", "forks_count"],
    required_fields=["name", "full_name"],
    pagination_support=True,
    native_total_support=True,   # search_repositories returns total_count
    native_sort_support=True,
    native_filter_support=True,
    preferred_mcp_tools=["search_repositories"],   # list_repositories is BLOCKED
    fallback_mcp_tools=["get_repository"],
    required_query_filters={
        "all_user_repositories": "user:<username>",
    },
    known_limitations=[
        "list_repositories is not available. Use search_repositories(query='user:<username>') instead.",
        "search_repositories returns up to 30 results per page. A count from total_count is authoritative.",
        "Fork repositories are included in search results unless explicitly filtered with fork:false.",
    ],
    read_only=True,
    scope_requirements={
        "all_user_repositories": "Use search_repositories with query='user:<username>'. Add sort/filter as needed.",
        "specific_repository": "Use get_repository(owner, name) for exact lookup.",
    }
)

# ---------------------------------------------------------------------------
# PROFILE capability
# ---------------------------------------------------------------------------
PROFILE_CONTRACT = CapabilityContract(
    dataset_scope="GitHub User Profile",
    supported_scopes=["current_profile"],
    supported_operations=["get", "select_fields"],
    supported_metrics=["followers", "following", "location", "bio", "company", "blog"],
    required_fields=["login", "name"],
    pagination_support=False,
    native_total_support=False,
    native_sort_support=False,
    native_filter_support=False,
    preferred_mcp_tools=["get_user"],
    fallback_mcp_tools=[],
    required_query_filters={},
    known_limitations=[],
    read_only=True,
    scope_requirements={
        "current_profile": "Use get_user(username=<username>).",
    }
)

# ---------------------------------------------------------------------------
# LANGUAGES capability
# ---------------------------------------------------------------------------
# CRITICAL LIMITATION: The GitHub Remote MCP server does NOT expose language byte
# breakdown per repository. Only the primary_language field is available from
# search_repositories/get_repository. Do NOT fabricate percentages or byte counts.
LANGUAGES_CONTRACT = CapabilityContract(
    dataset_scope="Repository Languages",
    supported_scopes=["all_user_repositories", "specific_repository"],
    supported_operations=["aggregate", "top_n", "count"],
    supported_metrics=["language"],  # NOT "bytes" or "percentage" — those are unavailable
    required_fields=["language"],
    pagination_support=False,
    native_total_support=False,
    native_sort_support=False,
    native_filter_support=False,
    preferred_mcp_tools=["search_repositories"],  # Primary language only, not byte counts
    fallback_mcp_tools=["get_repository"],
    required_query_filters={
        "all_user_repositories": "user:<username>",
    },
    known_limitations=[
        "CRITICAL: Language byte breakdown is NOT available via the connected MCP server.",
        "Only the primary language per repository is available (the 'language' field).",
        "Do NOT fabricate byte counts or percentage breakdowns.",
        "Do NOT substitute dashboard language percentages for MCP language data.",
        "If asked for 'most used language by bytes', explain that byte-level data is unavailable "
        "and offer to show the most common primary language across repositories instead.",
        "Language aggregation can only count how many repositories use each primary language.",
    ],
    read_only=True,
    scope_requirements={
        "all_user_repositories": "Use search_repositories(query='user:<username>') and aggregate the 'language' field by repository count.",
        "specific_repository": "Use get_repository(owner, name) and read the 'language' field.",
    }
)

# ---------------------------------------------------------------------------
# README_CODE capability
# ---------------------------------------------------------------------------
# Workflow: resolve repository → verify get_file_contents is available → retrieve README
# Never claim README is unavailable when MCP returned it successfully.
README_CODE_CONTRACT = CapabilityContract(
    dataset_scope="Repository Files/README",
    supported_scopes=["specific_repository"],
    supported_operations=["get", "select_fields"],
    supported_metrics=["content"],
    required_fields=["content"],
    pagination_support=False,
    native_total_support=False,
    native_sort_support=False,
    native_filter_support=False,
    preferred_mcp_tools=["get_file_contents"],
    fallback_mcp_tools=[],
    required_query_filters={},
    known_limitations=[
        "Requires repository resolution (owner + repo name) before retrieval.",
        "If repository resolution fails with ERROR, do not claim the README is unavailable.",
        "Binary files cannot be read.",
    ],
    read_only=True,
    scope_requirements={
        "specific_repository": (
            "Step 1: Resolve repository to get canonical owner and repo name. "
            "Step 2: Call get_file_contents(owner=<owner>, repo=<repo>, path='README.md'). "
            "Step 3: If not found, try 'readme.md' or 'README'. "
            "Step 4: Return decoded text content only."
        ),
    }
)

# ---------------------------------------------------------------------------
# PULL_REQUESTS capability
# ---------------------------------------------------------------------------
# CRITICAL: Pull-request requests must ALWAYS include `is:pr` in the search query.
# Do NOT use search_issues for generic issue lookup and call it a PR search.
# search_issues with is:pr is the authoritative PR search workflow on GitHub.
PULL_REQUESTS_CONTRACT = CapabilityContract(
    dataset_scope="Pull Requests",
    supported_scopes=["all_user_pull_requests", "specific_repository"],
    supported_operations=["count", "latest_n", "top_n", "sort", "filter", "select_fields"],
    supported_metrics=["created_at", "updated_at", "state"],
    required_fields=["title", "number", "state"],
    pagination_support=True,
    native_total_support=True,   # search returns total_count
    native_sort_support=True,
    native_filter_support=True,
    preferred_mcp_tools=["search_pull_requests"],   # Dedicated PR tool, already scoped to is:pr
    fallback_mcp_tools=["search_issues"],            # Fallback: must include is:pr in query
    required_query_filters={
        "all_user_pull_requests": "author:<username>",  # No is:pr needed for search_pull_requests
        "specific_repository": "repo:<owner>/<repo>",
    },
    known_limitations=[
        "PREFERRED: Use search_pull_requests — it is already scoped to is:pr by the MCP server.",
        "FALLBACK: If using search_issues, you MUST include 'is:pr' in the query.",
        "Do NOT claim 'you have no PRs' unless total_count=0 is returned by the MCP search.",
        "Sort by 'created' descending to get the latest PR.",
    ],
    read_only=True,
    scope_requirements={
        "all_user_pull_requests": "search_pull_requests(query='author:<username>', sort='created', order='desc'). Return top 1 for 'latest'.",
        "specific_repository": "search_pull_requests(query='repo:<owner>/<repo>', sort='created', order='desc').",
    }
)

# ---------------------------------------------------------------------------
# ISSUES capability
# ---------------------------------------------------------------------------
ISSUES_CONTRACT = CapabilityContract(
    dataset_scope="Issues",
    supported_scopes=["all_user_issues", "specific_repository"],
    supported_operations=["count", "latest_n", "top_n", "sort", "filter", "select_fields"],
    supported_metrics=["created_at", "updated_at", "state", "comments"],
    required_fields=["title", "number", "state"],
    pagination_support=True,
    native_total_support=True,
    native_sort_support=True,
    native_filter_support=True,
    preferred_mcp_tools=["search_issues"],
    fallback_mcp_tools=["list_issues"],
    required_query_filters={
        "all_user_issues": "is:issue author:<username>",
        "specific_repository": "is:issue repo:<owner>/<repo>",
    },
    known_limitations=[
        "Always include 'is:issue' in search_issues queries to distinguish issues from PRs.",
        "Do not omit 'is:issue' — search_issues returns both issues and PRs without it.",
    ],
    read_only=True,
    scope_requirements={
        "all_user_issues": "search_issues(query='is:issue author:<username>').",
        "specific_repository": "Resolve repository first, then search_issues(query='is:issue repo:<owner>/<repo>').",
    }
)

# ---------------------------------------------------------------------------
# ACTIVITY capability
# ---------------------------------------------------------------------------
ACTIVITY_CONTRACT = CapabilityContract(
    dataset_scope="Commits and Activity",
    supported_scopes=["specific_repository"],
    supported_operations=["count", "latest_n", "filter", "select_fields"],
    supported_metrics=["date"],
    required_fields=["sha", "commit"],
    pagination_support=True,
    native_total_support=False,
    native_sort_support=True,
    native_filter_support=True,
    preferred_mcp_tools=["list_commits"],
    fallback_mcp_tools=[],
    required_query_filters={},
    known_limitations=[
        "list_commits requires an explicit repository (owner + repo).",
        "Cross-repository commit aggregation requires multiple calls.",
        "Default scope is specific_repository; use the most recently active repository if none specified.",
    ],
    read_only=True,
    scope_requirements={
        "specific_repository": "Resolve repository, then list_commits(owner=<owner>, repo=<repo>).",
    }
)

# ---------------------------------------------------------------------------
# Central contract registry
# ---------------------------------------------------------------------------
CAPABILITY_CONTRACTS: dict[str, CapabilityContract] = {
    "REPOSITORIES": REPOSITORIES_CONTRACT,
    "PROFILE": PROFILE_CONTRACT,
    "LANGUAGES": LANGUAGES_CONTRACT,
    "README_CODE": README_CODE_CONTRACT,
    "PULL_REQUESTS": PULL_REQUESTS_CONTRACT,
    "ISSUES": ISSUES_CONTRACT,
    "ACTIVITY": ACTIVITY_CONTRACT,
}


def validate_contract(capability: str, operation: str, metric: str, scope: str) -> None:
    """
    Validates that a requested operation and metric are supported by the capability contract.
    Raises ValueError with a structured explanation if not supported.

    Also enforces metric semantic preservation:
      - "stars" → "stargazers_count" (safe normalization)
      - "forks" → "forks_count" (safe normalization)
      - "bytes" for LANGUAGES → immediately raises ValueError with capability limitation
    """
    if not capability:
        return  # No capability specified — skip (explicit override path)

    contract = CAPABILITY_CONTRACTS.get(capability)
    if not contract:
        raise ValueError(f"Unknown capability: {capability}")

    # Safe deterministic normalizations (do not change semantic meaning)
    if metric == "stars":
        metric = "stargazers_count"
    if metric == "forks":
        metric = "forks_count"

    # Normalize metric aliases to canonical form before validation.
    # This prevents router-produced aliases (e.g. "created") from failing
    # contract validation while keeping the contract authoritative.
    _METRIC_ALIASES: dict[str, str] = {
        "created": "created_at",
        "createdAt": "created_at",
        "date created": "created_at",
        "creation date": "created_at",
        "updated": "updated_at",
        "updatedAt": "updated_at",
        "date updated": "updated_at",
    }
    if metric in _METRIC_ALIASES:
        metric = _METRIC_ALIASES[metric]

    # Language bytes are UNAVAILABLE — reject immediately with an honest message
    if capability == "LANGUAGES" and metric in ("bytes", "percentage"):
        raise ValueError(
            "CAPABILITY_LIMITATION: Language byte and percentage breakdown is not available "
            "via the connected GitHub MCP server. Only primary language per repository is available. "
            "Please inform the user of this limitation rather than fabricating byte counts."
        )

    if operation and operation not in contract.supported_operations:
        raise ValueError(
            f"Operation '{operation}' is not supported for capability '{capability}'. "
            f"Supported: {contract.supported_operations}"
        )

    if metric and metric not in contract.supported_metrics:
        raise ValueError(
            f"Metric '{metric}' is not supported for capability '{capability}'. "
            f"Supported: {contract.supported_metrics}"
        )

    if scope and scope not in contract.supported_scopes:
        raise ValueError(
            f"Scope '{scope}' is not supported for capability '{capability}'. "
            f"Supported: {contract.supported_scopes}"
        )


def get_capability_limitation(capability: str) -> str | None:
    """Return a human-readable limitation string for a capability, or None if no limitations."""
    contract = CAPABILITY_CONTRACTS.get(capability)
    if not contract or not contract.known_limitations:
        return None
    # Return the most critical limitation (first in list)
    return contract.known_limitations[0]


def get_required_filter(capability: str, scope: str) -> str | None:
    """Return the required query filter for a capability+scope combination."""
    contract = CAPABILITY_CONTRACTS.get(capability)
    if not contract:
        return None
    return contract.required_query_filters.get(scope)
