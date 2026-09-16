"""
Chat API route — POST /api/chat

Returns Server-Sent Events (SSE) stream.
Protected by Supabase JWT authentication.
"""

from fastapi import APIRouter, Depends

from app.core.auth import verify_supabase_token
from app.schemas.chat import ChatRequest
from app.controllers.chat_controller import handle_chat_stream

router = APIRouter(dependencies=[Depends(verify_supabase_token)])


@router.post("")
async def chat_stream(
    request: ChatRequest,
    auth_user=Depends(verify_supabase_token),
):
    """
    POST /api/chat

    Request body:
        {
            username: str,
            message: str,
            dashboard_context?: dict,
            conversation_history?: [{role, content}],
            conversation_summary?: str
        }

    Response:
        text/event-stream with SSE events:
        - agent_started
        - tool_started
        - tool_completed
        - message_delta
        - source
        - message_completed
        - error
    """
    return await handle_chat_stream(request=request, auth_user=auth_user)
