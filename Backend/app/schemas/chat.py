"""
Chat schemas — Pydantic models for the new agentic chat API.
"""

from pydantic import BaseModel
from typing import Any, Optional


class ConversationTurn(BaseModel):
    """A single turn in conversation history sent from the frontend."""
    role: str   # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    """POST /api/chat request body for the new agentic chatbot."""
    username: str
    message: str
    dashboard_context: Optional[dict[str, Any]] = None
    conversation_history: Optional[list[ConversationTurn]] = []
    conversation_summary: Optional[str] = None
