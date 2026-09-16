"""
Chat service — thin orchestrator for the agentic chatbot.

Applies domain guard, then delegates to the agent loop.
Returns an async generator of SSE events.
"""

import json
import logging
from typing import Any, AsyncGenerator

from app.agent.domain_guard import check_domain
from app.agent.agent_loop import run_agent
from app.agent.schemas import ConversationTurn

logger = logging.getLogger(__name__)


def _sse(event: dict) -> str:
    return f"data: {json.dumps(event)}\n\n"


async def stream_chat(
    username: str,
    message: str,
    dashboard_context: dict[str, Any] | None,
    conversation_history: list[ConversationTurn] | None,
    conversation_summary: str | None,
) -> AsyncGenerator[str, None]:
    """
    Main entry point for chat streaming.

    Applies domain guard first, then runs the agent loop.

    Yields SSE event strings.
    """
    if not message or not message.strip():
        yield _sse({"type": "error", "message": "Please enter a message."})
        return

    if not username:
        yield _sse({"type": "error", "message": "No GitHub username provided."})
        return

    # Domain guard — lightweight, no LLM call
    is_allowed, refusal = check_domain(message)
    if not is_allowed:
        yield _sse({"type": "agent_started"})
        yield _sse({"type": "message_delta", "content": refusal})
        yield _sse({"type": "message_completed"})
        return

    logger.info("Chat request — user: %s | message: %.80s", username, message)

    # Run agentic loop
    async for event in run_agent(
        username=username,
        question=message,
        dashboard_data=dashboard_context,
        history=conversation_history,
        summary=conversation_summary,
    ):
        yield event
