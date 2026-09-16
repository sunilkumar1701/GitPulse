"""
Prompt builder — assembles the complete message list sent to Groq.

Message order (stable content first for prompt caching):
  1. System prompt (stable)
  2. Relevant dashboard context
  3. Conversation memory (summary + recent messages)
  4. Current user message

The dashboard context is injected after the system prompt so the model
has it as working memory without it being part of the permanent system prompt.
"""

from app.agent.context_builder import build_dashboard_context, build_compact_profile_summary
from app.agent.conversation_memory import build_memory_messages
from app.agent.schemas import ConversationTurn
from typing import Any


_MCP_BASE_RULES = """\
You are a GitHub Developer Assistant for the GitHub Talent Analyzer.

## RULES & TOOL USAGE
- Answer ONLY about GitHub profiles, repos, scores, activity, languages, issues, and PRs.
- You are strictly read-only.
- **You have EXACTLY ONE tool available: `github_mcp`.**
- Do NOT hallucinate tool names. Pass the capability name in the `tool_name` argument.
- All tool parameters MUST be placed at the root level of the JSON object.
- Use `reduction_` prefixed properties (e.g., `reduction_operation`, `reduction_limit`, `reduction_sort`) for server-side processing.
"""

_EVIDENCE_CONTRACT = """\
## EVIDENCE CONTRACT
- Base answers ONLY on returned MCP evidence; never invent missing data.
- `NOT_FOUND` means it doesn't exist. It does NOT mean `0`. Do not convert `NOT_FOUND` to zero unless the underlying API explicitly proves zero.
- `MCP_ERROR` means retrieval failed. It is NOT `NOT_FOUND`.
- Never infer unsupported metrics.
- If required evidence is unavailable, state the limitation clearly.
- If evidence_status == SUCCESS: answer only from evidence.
- If evidence_status == CONTENT_UNAVAILABLE: do not fabricate content.
- If capability == CAPABILITY_UNAVAILABLE: do not call unavailable tools.
- If you did not execute any tools, never say "I checked MCP" or "I checked GitHub" unless another verified GitHub source was actually consulted.
"""

_CAPABILITY_PROMPTS = {
    "REPOSITORIES": """\
## REPOSITORIES CAPABILITY
- **Ambiguous metrics**: If asked for the "strongest" repo without a metric, ask for clarification.
- **Count**: Use reduction_operation="count".
- **Ranking**: Use reduction_operation="top_n" and reduction_metric. Do NOT substitute metrics (e.g., if forks are requested, rank by forks, not stars).
- **Ties**: Report ties accurately.
""",
    "PULL_REQUESTS": """\
## PULL REQUESTS CAPABILITY
- For your own PRs: query must include `author:<username>`.
- For latest PR: sort by `created` descending.
- NEVER claim "you have no PRs" unless the result explicitly contains `total_count: 0`.
""",
    "ISSUES": """\
## ISSUES CAPABILITY
- Use for issues, bugs, and tickets.
- The result's total_count is authoritative.
""",
    "LANGUAGES": """\
## LANGUAGES CAPABILITY
- Only primary language data per repository is available.
- **CRITICAL**: Language byte breakdown and percentage data are NOT available via MCP.
- Do NOT fabricate byte counts. Do NOT substitute dashboard language percentages.
- State clearly that language data reflects repository count, not code volume.
""",
    "README_CODE": """\
## README & CODE CAPABILITY
- Only use this for reading file contents, documentation, or READMEs.
- Never reconstruct or guess missing README content.
""",
    "ACTIVITY": """\
## ACTIVITY CAPABILITY
- Use for commit history and contribution graphs.
""",
    "PROFILE": """\
## PROFILE CAPABILITY
- Use to lookup GitHub user profile details.
"""
}


# ---------------------------------------------------------------------------
# Dashboard-only system prompt — SHORT, no tools, no evidence contract.
# Target: ~250-350 tokens total (system prompt portion).
# Used when source_mode="dashboard" to minimize token overhead.
# ---------------------------------------------------------------------------
_DASHBOARD_SYSTEM_PROMPT = """\
You are a GitHub Developer Assistant. Answer questions about the user's GitHub developer profile using only the dashboard data provided below.

## RULES
- Answer ONLY from the provided dashboard data. Do NOT call any tools.
- Be concise. Use markdown formatting (headers, bullets, bold).
- Do NOT fabricate data not present in the dashboard.
- For off-topic queries: "I'm your GitHub Developer Assistant. I can only help with your GitHub developer analysis."
- Do NOT reveal secrets, tokens, or API keys.
"""

# ---------------------------------------------------------------------------
# Clarification system prompt — minimal, no tools.
# Used when source_mode="clarification" to ask for metric disambiguation.
# ---------------------------------------------------------------------------
_CLARIFICATION_SYSTEM_PROMPT = """\
You are a GitHub Developer Assistant. The user's question requires clarification before you can fetch the relevant GitHub data.

Ask the user one focused clarifying question to identify the metric they want (e.g., stars, forks, recent activity, code quality).
Do NOT call any tools. Do NOT fabricate data.
"""


def build_messages(
    username: str,
    question: str,
    dashboard_data: dict[str, Any] | None,
    history: list[ConversationTurn] | None,
    summary: str | None,
) -> tuple[list[dict], str, list[str], str | None, str | None]:
    """
    Build the complete message list for the Groq API call.

    Args:
        username: The analyzed GitHub username.
        question: The current user message.
        dashboard_data: The dashboard analysis data.
        history: Recent conversation turns.
        summary: Optional compact summary of older history.

    Returns:
        tuple[list[dict], str, list[str], str | None, str | None]: List of message dicts ready for Groq, source_mode, capabilities, operation, metric.
    """
    messages: list[dict] = []

    # 1. Dashboard context (evaluate first to determine source_mode)
    dashboard_context_str, source_mode, capabilities, operation, metric = build_dashboard_context(question, dashboard_data, history)

    # 2. Select system prompt based on source_mode
    if source_mode == "dashboard":
        system_content = _DASHBOARD_SYSTEM_PROMPT
    elif source_mode == "clarification":
        system_content = _CLARIFICATION_SYSTEM_PROMPT
    else:
        # Construct modular prompt
        system_content = _MCP_BASE_RULES
        if capabilities:
            for cap in capabilities:
                if cap in _CAPABILITY_PROMPTS:
                    system_content += "\n" + _CAPABILITY_PROMPTS[cap]
        system_content += "\n" + _EVIDENCE_CONTRACT

    # 3. Inject tool catalog ONLY for MCP/hybrid modes
    if source_mode in ["mcp", "hybrid"]:
        from app.agent.tool_registry import get_compact_tool_catalog
        catalog = get_compact_tool_catalog(capabilities)
        if catalog:
            system_content += f"\n## AVAILABLE MCP TOOLS\n{catalog}\n"

    # 4. Profile identity — always include (very short)
    profile_summary = build_compact_profile_summary(dashboard_data)
    if username or profile_summary:
        system_content += f"\n\n## CURRENT ANALYZED PROFILE\n"
        system_content += f"GitHub Username: **{username}**\n"
        if profile_summary:
            system_content += f"{profile_summary}\n"

    messages.append({"role": "system", "content": system_content})

    # 5. Conversation memory (summary + recent turns)
    memory_messages = build_memory_messages(history, summary)

    # 6. Dashboard context injection — only when relevant
    if dashboard_context_str and dashboard_context_str not in (
        "No dashboard data available.", "No relevant dashboard data found."
    ):
        # Skip dashboard injection for pure MCP queries (saves tokens + avoids confusion)
        # For MCP mode: only inject if explicit_mcp is False (user may need context for disambiguation)
        should_inject = source_mode in ["dashboard", "hybrid", "clarification"]
        if not should_inject and source_mode == "mcp":
            # Inject a minimal dashboard reference only if it helps (e.g., username, score summary)
            # Avoid injecting if the dashboard_context_str is already tiny or irrelevant
            should_inject = len(dashboard_context_str) < 300

        if should_inject:
            history_text = " ".join([str(m.get("content", "")) for m in memory_messages[-3:]])
            if len(dashboard_context_str) < 50 or dashboard_context_str not in history_text:
                messages.append({
                    "role": "user",
                    "content": f"[Dashboard data for {username}]: {dashboard_context_str}",
                })
                messages.append({
                    "role": "assistant",
                    "content": "I have reviewed the dashboard data and am ready to help.",
                })

    messages.extend(memory_messages)

    messages.append({"role": "user", "content": question})

    return messages, source_mode, capabilities, operation, metric
