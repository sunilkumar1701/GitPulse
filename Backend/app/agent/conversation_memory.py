"""
Conversation memory — compact sliding window conversation history.

Keeps the last N messages plus an optional summary of older context.
Prevents unlimited token growth while preserving follow-up capability.
"""

from app.agent.schemas import ConversationTurn

MAX_RECENT_MESSAGES = 6  # Keep last 3 turns (6 messages)


def build_memory_messages(
    history: list[ConversationTurn] | None,
    summary: str | None = None,
) -> list[dict]:
    """
    Build the message list representing conversation memory.

    Structure:
      - Optional summary as a system/user note
      - Last MAX_RECENT_MESSAGES messages

    Args:
        history: Full conversation history from the frontend.
        summary: Optional compact summary of older history.

    Returns:
        List of message dicts ready for the Groq API.
    """
    messages: list[dict] = []

    if summary and summary.strip():
        messages.append({
            "role": "user",
            "content": f"[Conversation context so far: {summary.strip()}]",
        })
        messages.append({
            "role": "assistant",
            "content": "Understood. I have that context.",
        })

    if history:
        # Take only the last MAX_RECENT_MESSAGES messages
        recent = history[-MAX_RECENT_MESSAGES:]
        for turn in recent:
            role = turn.role if turn.role in ("user", "assistant") else "user"
            content = turn.content or ""
            if len(content) > 1500:
                content = content[:500] + f"\n... [Content truncated from {len(content)} chars to preserve context]"
            messages.append({
                "role": role,
                "content": content,
            })

    return messages


def should_summarize(history: list[ConversationTurn] | None) -> bool:
    """
    Determine if the history is long enough to benefit from summarization.
    Currently returns False — summarization is driven by the frontend
    by passing in a conversation_summary string.
    """
    return False
