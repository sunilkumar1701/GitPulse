"""
Domain guard — lightweight application-level boundary.

Rejects obviously off-topic requests WITHOUT making an LLM call.
This does NOT decide dashboard vs MCP — that is the agent's job.

Only catches clearly unrelated requests like weather, sports, jokes, recipes.
"""

import re
import logging

logger = logging.getLogger(__name__)

# Keywords that strongly indicate off-topic requests
_OFF_TOPIC_PATTERNS = [
    r"\bweather\b",
    r"\bforecast\b",
    r"\btemperature\b",
    r"\bhumidity\b",
    r"\brain\b.*today",
    r"\bchief minister\b",
    r"\bprime minister\b",
    r"\bpresident\b.*country",
    r"\bcricket match\b",
    r"\bfootball match\b",
    r"\bwon.*match\b",
    r"\bscore.*match\b",
    r"\brecipe\b",
    r"\bcook\b.*food",
    r"\bingredient\b",
    r"\bjoke\b",
    r"\bfunny\b",
    r"\blaugh\b",
    r"\bquantum\b.*mechanics",
    r"\btheory of relativity\b",
    r"\bblack hole\b",
    r"\bcapital of\b",
    r"\bwho is the president\b",
    r"\bstock price\b",
    r"\bbitcoin\b",
    r"\bcrypto\b.*price",
    r"\bhoroscope\b",
    r"\bzodiac\b",
    r"\btranslate.*to\b",
    r"\bfilm review\b",
    r"\bmovie.*release\b",
    r"\bsong lyrics\b",
    r"\bwho sang\b",
]

_COMPILED = [re.compile(p, re.IGNORECASE) for p in _OFF_TOPIC_PATTERNS]

_DOMAIN_REFUSAL = (
    "I'm your GitHub Developer Assistant. I can help with your GitHub profile, "
    "repositories, activity, technologies, portfolio readiness, issues, pull requests, "
    "and related developer analysis. Please ask me something about your GitHub profile."
)


def check_domain(message: str) -> tuple[bool, str | None]:
    """
    Check if the message is obviously off-topic.

    Returns:
        (is_allowed, refusal_message)
        If is_allowed is True, refusal_message is None.
        If is_allowed is False, refusal_message is the rejection text.
    """
    text = message.strip().lower()
    if not text:
        return False, "Please enter a message."

    for pattern in _COMPILED:
        if pattern.search(text):
            logger.info("Domain guard blocked message matching: %s", pattern.pattern)
            return False, _DOMAIN_REFUSAL

    return True, None
