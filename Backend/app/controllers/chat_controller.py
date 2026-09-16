"""
Chat controller — handles POST /api/chat.

Validates the request, verifies auth user matches request context,
and returns a StreamingResponse with SSE events.
"""

import logging
from fastapi import Request
from fastapi.responses import StreamingResponse

from app.schemas.chat import ChatRequest
from app.services.chat_service import stream_chat
from app.agent.schemas import ConversationTurn

logger = logging.getLogger(__name__)


async def handle_chat_stream(request: ChatRequest, auth_user) -> StreamingResponse:
    """
    Handle POST /api/chat → StreamingResponse (SSE).

    Args:
        request: ChatRequest from the frontend.
        auth_user: The authenticated Supabase user (from verify_supabase_token).

    Returns:
        StreamingResponse with Content-Type: text/event-stream
    """
    if not request.username:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="username is required.")

    if not request.message:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="message is required.")

    # Convert conversation history from schema models
    history: list[ConversationTurn] | None = None
    if request.conversation_history:
        history = [
            ConversationTurn(role=t.role, content=t.content)
            for t in request.conversation_history
        ]

    async def event_generator():
        async for chunk in stream_chat(
            username=request.username,
            message=request.message,
            dashboard_context=request.dashboard_context,
            conversation_history=history,
            conversation_summary=request.conversation_summary,
        ):
            yield chunk

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
