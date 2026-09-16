"""
Semantic Router for the GitHub Talent Analyzer.

Determines source_mode and required capabilities without needing an extra LLM call.

source_mode values:
  "dashboard"     — answer from dashboard data only (no MCP)
  "mcp"           — answer requires GitHub MCP data
  "hybrid"        — both sources needed
  "clarification" — query is ambiguous; ask the user for a metric before proceeding

Capabilities:
  PROFILE, REPOSITORIES, LANGUAGES, README_CODE, PULL_REQUESTS, ISSUES, ACTIVITY

Design rules:
  - Do not route on a single keyword; consider the full semantic intent.
  - source_mode="mcp" must resolve to a specific supported capability, not "any tool."
  - Explicit MCP instructions (use MCP, check GitHub, don't use dashboard) force source_mode="mcp".
  - Language/tech questions → LANGUAGES (not REPOSITORIES).
  - README/documentation/code-content questions → README_CODE (not PROFILE).
  - Pull-request questions → PULL_REQUESTS (not ISSUES).
  - Activity/commit questions → ACTIVITY.
  - Repository ranking/detail questions → REPOSITORIES.
  - Ambiguous metric questions (strongest/best without explicit metric) → clarification.
"""

import re
from typing import Any
from app.agent.schemas import ConversationTurn


class Capability:
    PROFILE = "PROFILE"
    REPOSITORIES = "REPOSITORIES"
    LANGUAGES = "LANGUAGES"
    README_CODE = "README_CODE"
    PULL_REQUESTS = "PULL_REQUESTS"
    ISSUES = "ISSUES"
    ACTIVITY = "ACTIVITY"


# ---------------------------------------------------------------------------
# Intent patterns — each capability has multiple patterns covering synonyms,
# phrases, and question forms. Patterns are checked with re.IGNORECASE.
# ---------------------------------------------------------------------------
_INTENT_MAP: dict[str, list[str]] = {
    Capability.PROFILE: [
        # Identity fields
        r"\b(profile|account|bio|name|location|city|country)\b",
        # Contact/social
        r"\b(website|blog|email|twitter|linkedin|social\s*links?)\b",
        # Network
        r"\b(followers?|following|connections?)\b",
        # General user lookup
        r"\b(who\s+is|about\s+me|user\s+info|github\s+user)\b",
        # Hiring/readiness (proprietary score + profile)
        r"\b(hire\s*able|readiness|score|rank(ing)?|developer\s+score)\b",
    ],

    Capability.REPOSITORIES: [
        # Explicit repository nouns
        r"\b(repositor(y|ies)|repos?)\b",
        # Project synonyms
        r"\b(projects?|codebases?)\b",
        # Star/fork operations on a collection of repos
        r"\b(stars?|forked?|forks?)\b",
        # Specific ranking or listing operations
        r"\b(most\s+starred|most\s+popular|top\s+(repo|project|repositor))",
        r"\b(list\s+(my\s+)?(repo|project))\b",
        r"\b(strongest|best|biggest|largest)\s+(repositor|repo|project)?\b",
        # Count questions
        r"\b(how\s+many\s+(public|private)?\s*(repo|repositor|project))\b",
        # Sorting
        r"\b(sort(ed)?\s+by|order(ed)?\s+by|rank\s+by)\b",
    ],

    Capability.LANGUAGES: [
        # Direct language nouns
        r"\b(lang(uage)?s?)\b",
        r"\b(programming\s+lang(uage)?)\b",
        # Technology synonyms
        r"\b(tech(nolog(y|ies))?)\b",
        r"\b(tech\s*stack)\b",
        r"\b(frameworks?)\b",
        r"\b(tools?\s+use(d|s)?)\b",
        # Breakdown/analysis phrases
        r"\b(lang(uage)?\s+breakdown)\b",
        r"\b(lang(uage)?\s+(usage|stats?|statistics|distribution|analysis))\b",
        r"\b(code\s+in)\b",
        r"\b(most\s+used\s+(lang|programming))\b",
        r"\b(primary\s+lang(uage)?)\b",
        # Specific language names (common ones to avoid misrouting)
        r"\b(python|javascript|typescript|java|go|rust|c\+\+|c#|ruby|swift|kotlin)\b",
    ],

    Capability.README_CODE: [
        # README explicitly mentioned
        r"\b(readme)\b",
        r"\b(readme\s+file)\b",
        r"\b(readme\s+mention(s|ed)?)\b",
        r"\b(what\s+does\s+the\s+readme)\b",
        r"\b(is\s+.{1,30}\s+mention(ed)?\s+in\s+the\s+readme)\b",
        # Documentation synonyms
        r"\b(documentation|docs?)\b",
        r"\b(project\s+description)\b",
        # File/code content access
        r"\b(file\s+content(s)?)\b",
        r"\b(source\s+code)\b",
        r"\b(code\s+file(s)?)\b",
        # README-specific question patterns
        r"\b(summar(y|ize)\s+(the\s+)?(readme|documentation))\b",
    ],

    Capability.PULL_REQUESTS: [
        # Canonical phrases
        r"\b(pull\s+requests?)\b",
        r"\b(prs?)\b",
        # Synonyms
        r"\b(merges?|merged\s+(code|changes?))\b",
        r"\b(latest\s+(pr|pull))\b",
        r"\b(recent\s+(pr|pull))\b",
        r"\b(my\s+(pr|pull\s+request))\b",
        r"\b(open(ed)?\s+(pr|pull\s+request))\b",
        r"\b(closed?\s+(pr|pull\s+request))\b",
        # Contribution context
        r"\b(contributed?\s+(pr|pull))\b",
    ],

    Capability.ISSUES: [
        # Canonical
        r"\b(issues?)\b",
        # Synonyms
        r"\b(bugs?|bug\s+report)\b",
        r"\b(open\s+issues?)\b",
        r"\b(closed?\s+issues?)\b",
        r"\b(issue\s+count)\b",
        r"\b(how\s+many\s+issues?)\b",
        # Ticket/task synonyms (GitHub-contextual)
        r"\b(ticket(s)?|task(s)?)\b",
    ],

    Capability.ACTIVITY: [
        # Commits
        r"\b(commits?)\b",
        r"\b(commit\s+history)\b",
        r"\b(recent\s+commits?)\b",
        r"\b(latest\s+commit)\b",
        # Contribution graph terms
        r"\b(contributions?)\b",
        r"\b(contribution\s+graph)\b",
        r"\b(contribution\s+streak)\b",
        r"\b(active(ly)?)\b",
        r"\b(activity)\b",
        r"\b(streak)\b",
        # Event/push synonyms
        r"\b(pushes?|push\s+events?)\b",
    ],
}

# Explicit MCP override patterns — any of these forces source_mode="mcp"
# IMPORTANT: source_mode="mcp" must then resolve to a *specific* capability, not "any tool".
_EXPLICIT_MCP_OVERRIDE: list[str] = [
    r"\b(use\s+mcp)\b",
    r"\b(via\s+mcp)\b",
    r"\b(from\s+mcp)\b",
    r"\b(don'?t\s+(use|look\s+at)\s+(the\s+)?dashboard)\b",
    r"\b(ignore\s+(the\s+)?dashboard)\b",
    r"\b(not?\s+(from|in)\s+(the\s+)?dashboard)\b",
    r"\b(check\s+github)\b",
    r"\b(from\s+github)\b",
    r"\b(use\s+github)\b",
    r"\b(get\s+this\s+from\s+github)\b",
    r"\b(search\s+(my\s+)?(repos(itories)?|github))\b",
    r"\b(look\s+it\s+up\s+on\s+github)\b",
    r"\b(fetch\s+from\s+github)\b",
]

_AGGREGATION_KEYWORDS: list[str] = [
    r"\b(total|all|most|latest|top|highest|lowest|combined|sum|average|every|across\s+all)\b",
]

# ---------------------------------------------------------------------------
# Clarification triggers — queries that use ambiguous ranking terms without
# an explicit metric. These should request clarification rather than MCP.
# Only fired when NO explicit metric keyword accompanies the query.
# ---------------------------------------------------------------------------
_CLARIFICATION_TRIGGERS: list[str] = [
    r"\b(strongest)\s*(repositor|repo|project)?\b",
    r"\b(best)\s*(repositor|repo|project)?\b",
    r"\b(most\s+impressive)\s*(repositor|repo|project)?\b",
    r"\b(healthiest)\s*(repositor|repo|project)?\b",
    r"\b(most\s+impactful)\s*(repositor|repo|project)?\b",
]

# Explicit metric keywords that disambiguate ranking queries (prevent false clarification)
_EXPLICIT_METRIC_KEYWORDS: list[str] = [
    r"\b(stars?|stargazers?|forks?|views?|clones?|watchers?)\b",
    r"\b(commits?|activity|updated|recent|latest)\b",
    r"\b(most\s+(starred|forked|active|popular))\b",
    r"\b(by\s+(stars?|forks?|commits?|activity|date|size))\b",
]

# Capabilities that always require MCP (never answerable from dashboard alone)
_ALWAYS_MCP_CAPABILITIES = {
    Capability.REPOSITORIES,
    Capability.LANGUAGES,
    Capability.README_CODE,
    Capability.PULL_REQUESTS,
    Capability.ISSUES,
    Capability.ACTIVITY,
}

# Dashboard-only proprietary metrics (never answered by MCP even if MCP is requested)
_DASHBOARD_ONLY_KEYWORDS: list[str] = [
    r"\b(developer\s+score|dev\s+score)\b",
    r"\b(hiring\s+readiness|hire\s*able(ness)?)\b",
    r"\b(talent\s+score|talent\s+rank)\b",
    r"\b(developer\s+rank)\b",
]

# Capabilities that should NOT be added to README_CODE queries unless explicitly mentioned
_README_UNRELATED_CAPS = {
    Capability.PULL_REQUESTS,
    Capability.ISSUES,
    Capability.ACTIVITY,
}


def _match_any(text: str, patterns: list[str]) -> bool:
    """Return True if any pattern matches in `text` (case-insensitive)."""
    return any(re.search(p, text, re.IGNORECASE) for p in patterns)


def determine_source_and_capabilities(
    question: str,
    dashboard_data: dict[str, Any] | None,
    history: list[ConversationTurn] | None,
) -> tuple[str, list[str], bool, str | None, str | None]:
    """
    Returns (source_mode, capabilities, explicit_mcp, operation, metric).

    source_mode in ["dashboard", "mcp", "hybrid", "clarification"]
    capabilities is a list of Capability strings.
    explicit_mcp is True if the user explicitly requested MCP/GitHub data.
    operation is an optional string ("count", "top_n", "latest_n").
    metric is an optional string indicating the sort/filter metric.

    Routing rules (in priority order):
    1. If the question is dashboard-only (proprietary score/rank), use "dashboard".
    2. If the user explicitly overrides to MCP, use "mcp".
    3. If the question implies GitHub-specific data, use "mcp" with the matched capability.
    4. If the question is a profile question answerable from dashboard, use "dashboard".
    5. Default to "mcp" with PROFILE+REPOSITORIES to avoid silent hallucination.
    """
    q = question.strip()
    q_lower = q.lower()

    # 1. Explicit MCP override check (highest priority, except dashboard-only)
    explicit_mcp = _match_any(q_lower, _EXPLICIT_MCP_OVERRIDE)

    # 2. Detect required capabilities from the question
    required_caps: set[str] = set()
    for cap, patterns in _INTENT_MAP.items():
        if _match_any(q_lower, patterns):
            required_caps.add(cap)

    # 3. Enrich from history for short follow-up questions (< 10 words)
    # RULE: Only carry forward the dominant capability from the LAST prior turn.
    # Never blindly merge all prior capabilities — that causes cross-topic contamination.
    # If the current question already matched specific capabilities, do NOT add unrelated ones from history.
    if history and len(q.split()) < 10:
        current_caps_snapshot = set(required_caps)  # capabilities matched by current question alone
        # Only look at the immediately preceding turn (last 2 messages = 1 exchange)
        prev_turns = [t for t in history[-2:] if hasattr(t, "content")]
        history_caps: set[str] = set()
        for turn in prev_turns:
            prev_q = (turn.content or "").lower()
            for cap, patterns in _INTENT_MAP.items():
                if _match_any(prev_q, patterns):
                    history_caps.add(cap)
                    break  # take only first matched cap per turn to avoid bloat

        if current_caps_snapshot:
            # Current question already has direction — do NOT contaminate with unrelated history caps.
            # Only carry forward history caps that are already in the current set.
            required_caps = set(current_caps_snapshot)
        else:
            # Current question matched nothing on its own — take the single dominant history cap
            if history_caps:
                required_caps.add(next(iter(history_caps)))

    # 4. Dashboard-only proprietary metrics — never use MCP for these
    is_dashboard_only = _match_any(q_lower, _DASHBOARD_ONLY_KEYWORDS)

    is_aggregation = _match_any(q_lower, _AGGREGATION_KEYWORDS)

    # 4b. README_CODE capability pruning — strip unrelated caps added by history enrichment
    if Capability.README_CODE in required_caps and not explicit_mcp:
        # Only strip if the unrelated caps are NOT explicitly mentioned in the current question
        for unrelated_cap in _README_UNRELATED_CAPS:
            if unrelated_cap in required_caps:
                # Check if the current question (not history) explicitly mentions it
                if not _match_any(q_lower, _INTENT_MAP.get(unrelated_cap, [])):
                    required_caps.discard(unrelated_cap)

    # 4c. Capability Authority Rules — remove PROFILE when a domain-specific capability is authoritative.
    # This prevents the LLM from attempting invalid operations (sum, count, top_n) under PROFILE.
    _DOMAIN_CAPS = {
        Capability.REPOSITORIES, Capability.PULL_REQUESTS, Capability.ISSUES,
        Capability.README_CODE, Capability.LANGUAGES, Capability.ACTIVITY,
    }
    if required_caps & _DOMAIN_CAPS:
        # A domain-specific capability is present — PROFILE is never authoritative for these workflows
        required_caps.discard(Capability.PROFILE)

    # 4c-ii. PR Capability Isolation — when PULL_REQUESTS is the primary intent,
    # do not add REPOSITORIES unless the query requires a SEPARATE repository
    # operation (listing, counting, ranking repos). Merely mentioning "repository"
    # in the PR context ("which repository was it from?") does NOT require a
    # separate REPOSITORIES tool call — the PR evidence already contains the repo name.
    _SEPARATE_REPO_OPERATION_PATTERNS = [
        r"\b(list\s+(my\s+)?(repo|project))",
        r"\b(how\s+many\s+(public|private)?\s*(repo|repositor|project))\b",
        r"\b(most\s+starred|most\s+popular|top\s+(repo|project|repositor))",
        r"\b(sort(ed)?\s+by|order(ed)?\s+by|rank\s+by)\b",
        r"\b(strongest|best|biggest|largest)\s+(repositor|repo|project)?\b",
    ]
    if Capability.PULL_REQUESTS in required_caps and Capability.REPOSITORIES in required_caps:
        if not _match_any(q_lower, _SEPARATE_REPO_OPERATION_PATTERNS):
            required_caps.discard(Capability.REPOSITORIES)

    # 4d. Clarification check — ambiguous ranking terms without an explicit metric
    # Only triggered for non-explicit-MCP queries where no metric is specified
    if not explicit_mcp and not is_dashboard_only:
        if _match_any(q_lower, _CLARIFICATION_TRIGGERS):
            if not _match_any(q_lower, _EXPLICIT_METRIC_KEYWORDS):
                return "clarification", [], False, None, None

    # 4d. Deterministic Operation & Metric Extraction
    operation = None
    metric = None

    # Extract Metric
    if _match_any(q_lower, [r"\b(stars?|stargazers?|starred)\b"]):
        metric = "stars"
    elif _match_any(q_lower, [r"\b(forks?|forked)\b"]):
        metric = "forks"
    elif _match_any(q_lower, [r"\b(activity|updated)\b"]):
        metric = "updated"

    # Extract Operation (only high-confidence explicit matches)
    if metric and _match_any(q_lower, [r"\b(total|combined|sum|aggregate|how\s+many|all)\b"]):
        operation = "sum"
    elif _match_any(q_lower, [r"\b(how\s+many|count|number\s+of|total)\b"]):
        operation = "count"
    elif _match_any(q_lower, [r"\b(top|most\s+(starred|forked|active))\b"]) and metric:
        operation = "top_n"
    elif _match_any(q_lower, [r"\b(latest|recently|recent|last)\b"]):
        operation = "latest_n"
        if not metric:
            metric = "created_at"

    # 5. Resolve source_mode

    if is_dashboard_only and not explicit_mcp:
        # Developer score / talent rank — always dashboard
        source_mode = "dashboard"
        required_caps.clear()
        return source_mode, [], False, None, None

    if explicit_mcp:
        source_mode = "mcp"
        # If explicit MCP but no specific cap detected, default to REPOSITORIES + PROFILE
        if not required_caps:
            required_caps = {Capability.REPOSITORIES, Capability.PROFILE}
        return source_mode, sorted(required_caps), True, operation, metric

    import difflib
    words = q_lower.replace("?", "").replace(".", "").split()
    
    # Explicit score/rank or fuzzy misspellings (scre, sccor, scoore, etc.)
    if any(kw in q_lower for kw in ["score", "rank", "readiness"]) or \
       difflib.get_close_matches("score", words, n=5, cutoff=0.6) or \
       difflib.get_close_matches("rank", words, n=5, cutoff=0.6):
        source_mode = "dashboard"
        required_caps.clear()
        return source_mode, [], False, None, None

    # General knowledge / conversational fallback (e.g. "how to improve...", "what is...")
    if any(q_lower.startswith(prefix) for prefix in ["how to", "why", "best practices", "explain", "help"]):
        source_mode = "dashboard"
        required_caps.clear()
        return source_mode, [], False, None, None
        
    if q_lower.startswith("what is") and not _match_any(q_lower, [r"\b(my|our|me|i)\b"]):
        source_mode = "dashboard"
        required_caps.clear()
        return source_mode, [], False, None, None

    # Check if any detected capability mandates MCP
    mcp_required = bool(required_caps & _ALWAYS_MCP_CAPABILITIES)

    # Aggregation questions always need MCP for completeness
    if is_aggregation:
        mcp_required = True
        if not required_caps:
            required_caps = {Capability.REPOSITORIES}

    if mcp_required:
        # Check if dashboard can *also* partially answer (hybrid)
        dash_keys = set(dashboard_data.keys()) if dashboard_data else set()
        profile_in_caps = Capability.PROFILE in required_caps
        profile_in_dash = "profileAnalysis" in dash_keys

        if profile_in_caps and profile_in_dash and len(required_caps) == 1:
            # Pure profile question that dashboard can answer
            source_mode = "dashboard"
            required_caps.clear()
        else:
            source_mode = "mcp"
        return source_mode, sorted(required_caps), False, operation, metric

    # Dashboard sufficiency check for pure profile questions
    dash_keys = set(dashboard_data.keys()) if dashboard_data else set()
    if Capability.PROFILE in required_caps and "profileAnalysis" in dash_keys:
        source_mode = "dashboard"
        required_caps.clear()
        return source_mode, [], False, None, None



    # Default: use MCP to avoid hallucination
    source_mode = "mcp"
    if not required_caps:
        required_caps = {Capability.PROFILE, Capability.REPOSITORIES}
    return source_mode, sorted(required_caps), False, operation, metric
