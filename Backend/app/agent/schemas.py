"""
Agent schemas — Pydantic models for the agentic chatbot.
"""

from pydantic import BaseModel
from typing import Any, Optional


class ConversationTurn(BaseModel):
    """A single turn in the conversation history (sent from frontend)."""
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    """POST /api/chat request body."""
    username: str
    message: str
    dashboard_context: Optional[dict[str, Any]] = None
    conversation_history: Optional[list[ConversationTurn]] = []
    # Optional compact summary of older history
    conversation_summary: Optional[str] = None


class ToolCallResult(BaseModel):
    """Result of a single MCP tool call."""
    tool_name: str
    ui_label: str
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None


class AgentSource(BaseModel):
    """Source attribution for the frontend."""
    label: str
    detail: Optional[str] = None
    url: Optional[str] = None
