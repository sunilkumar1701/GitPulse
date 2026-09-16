"""
Context builder — builds a compact, relevant dashboard context for the agent.

Does NOT send the entire dashboard JSON on every request.
Selects relevant sections based on question topic to minimize token usage.
"""

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Maps topic keywords to dashboard keys to include
# Strict capability mapping: determines exactly which dashboard fields are sent
_CAPABILITY_MAP: dict[str, tuple[list[str], list[str], bool]] = {
    # capability_name -> (keywords, dashboard_keys, needs_mcp)
    "developer_score": (["score", "rating", "rank", "grade", "overall"], ["developerScore", "overallScore", "score"], False),
    "portfolio": (["portfolio", "recruiter", "ready", "readiness", "hire"], ["portfolioReadiness", "recruiterReadiness"], False),
    "repository_quality": (["repository quality", "repo quality", "quality metric", "quality score"], ["repositoryQuality", "repoQuality"], False),
    "technology": (["tech", "lang", "programming", "framework", "tool", "strongest"], ["technologyStack", "languages", "technologies", "topLanguages"], False),
    "activity": (["activity", "commit", "contribution", "active", "streak"], ["activityAnalysis", "activityStatus", "activity"], False),
    "profile": (["profile", "follower", "following", "bio", "account", "user", "location", "linkedin", "twitter", "social", "website", "blog", "email", "link"], ["profileAnalysis", "profile", "profileCard"], False),
    "most_starred": (["star", "popular", "top repo", "best repo"], ["mostStarredRepository", "mostStarredRepo"], False),
    "most_forked": (["fork"], ["mostForkedRepository", "mostForkedRepo"], False),
    "repository_overview": (["repo", "project"], ["repositoryAnalysis"], False),
    "issues": (["issue", "bug"], [], True),
    "pull_requests": (["pull request", "pr", "merge"], [], True),
}


from app.agent.semantic_router import determine_source_and_capabilities

def build_dashboard_context(
    question: str,
    dashboard_data: dict[str, Any] | None,
    history: list | None = None
) -> tuple[str, str, list[str], str | None, str | None]:
    """
    Build a compact dashboard context string for the agent.

    Returns:
        tuple: (context_string, source_mode, capabilities, operation, metric)
    """
    source_mode, capabilities, explicit_mcp, operation, metric = determine_source_and_capabilities(question, dashboard_data, history)

    if not dashboard_data:
        return "No dashboard data available.", source_mode, capabilities, operation, metric

    # Build filtered context by strictly extracting required fields
    # If source_mode is dashboard or hybrid, we provide everything currently
    # But ideally, we should map back to keys. For simplicity, we just use a fallback mapping here.
    question_lower = question.lower()
    selected_keys: set[str] = set()

    # Fallback keyword logic just for extracting dashboard subsets
    broad_keywords = ["summary", "overview", "everything", "all", "full", "general"]
    if any(kw in question_lower for kw in broad_keywords):
        selected_keys = {"developerScore", "profileAnalysis", "repositoryAnalysis"}
    else:
        for cap_name, (keywords, keys, _) in _CAPABILITY_MAP.items():
            if any(kw in question_lower for kw in keywords):
                selected_keys.update(keys)

    if not selected_keys:
        selected_keys = {"developerScore", "profileAnalysis"}

    filtered: dict[str, Any] = {}
    for key in selected_keys:
        if key in dashboard_data:
            val = dashboard_data[key]
            if isinstance(val, dict):
                new_val = {}
                for k, v in val.items():
                    if isinstance(v, (str, int, float, bool)):
                        new_val[k] = v
                    elif isinstance(v, list):
                        new_val[k] = v[:10]
                    elif isinstance(v, dict):
                        new_val[k] = v
                filtered[key] = new_val
            elif isinstance(val, list):
                filtered[key] = val[:10]
            else:
                filtered[key] = val

    if not filtered:
        return "No relevant dashboard data found.", source_mode, capabilities, operation, metric

    if explicit_mcp:
        # User explicitly demanded MCP — do NOT inject dashboard data that could confuse the LLM.
        # Return only the _INSTRUCTION warning so prompt_builder skips injection (it's < 300 chars).
        _instruction = (
            "The user explicitly requested GitHub/MCP. "
            "Do NOT use dashboard data as a factual source for this request. "
            "You MUST execute an MCP tool to satisfy factual claims."
        )
        return _instruction, source_mode, capabilities, operation, metric

    try:
        return json.dumps(filtered, default=str, indent=None), source_mode, capabilities, operation, metric
    except Exception as e:
        logger.error("Context builder serialization error: %s", e)
        return "Dashboard data unavailable.", source_mode, capabilities, operation, metric


def build_compact_profile_summary(dashboard_data: dict[str, Any] | None) -> str:
    """
    Build a one-line profile summary for use in the system prompt.
    Gives the agent basic identity context about the analyzed user.
    """
    if not dashboard_data:
        return ""

    parts = []

    # Try common profile fields
    for profile_key in ["profileCard", "profile", "profileAnalysis"]:
        profile = dashboard_data.get(profile_key, {})
        if isinstance(profile, dict):
            name = profile.get("name") or profile.get("login") or profile.get("username")
            if name:
                parts.append(f"Name: {name}")
            login = profile.get("login") or profile.get("username")
            if login and login not in str(parts):
                parts.append(f"Username: {login}")
            break

    score_val = None
    for score_key in ["developerScore", "overallScore", "score"]:
        score_obj = dashboard_data.get(score_key, {})
        if isinstance(score_obj, dict):
            score_val = score_obj.get("score") or score_obj.get("overall")
        elif isinstance(score_obj, (int, float)):
            score_val = score_obj
        if score_val is not None:
            parts.append(f"Developer Score: {score_val}/100")
            break

    return " | ".join(parts) if parts else ""
