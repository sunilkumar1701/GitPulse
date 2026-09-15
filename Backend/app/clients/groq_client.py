"""
Groq AI client — powers the agentic chatbot.

Uses the official `groq` SDK.
Model: openai/gpt-oss-120b (configurable via GROQ_MODEL env var).

The GROQ_API_KEY lives ONLY here, on the backend.
It is NEVER sent to the browser or the LLM context.
"""

import json
import logging
from typing import AsyncGenerator, Any

from groq import AsyncGroq, RateLimitError, APIStatusError, APIConnectionError, APITimeoutError
from app.core.config import get_settings

logger = logging.getLogger(__name__)

_client: AsyncGroq | None = None


def get_groq_client() -> AsyncGroq:
    """Return the singleton Groq async client."""
    global _client
    if _client is None:
        settings = get_settings()
        if not settings.GROQ_API_KEY:
            raise RuntimeError(
                "GROQ_API_KEY is not configured. Please add it to Backend/.env and restart the server."
            )
        _client = _create_client()
    return _client


def _create_client() -> AsyncGroq:
    settings = get_settings()
    if not settings.GROQ_API_KEY:
        raise RuntimeError(
            "GROQ_API_KEY is missing. Add it to Backend/.env."
        )
    return AsyncGroq(api_key=settings.GROQ_API_KEY)


def init_groq_client() -> None:
    """Initialize the Groq client at application startup."""
    global _client
    settings = get_settings()
    if not settings.GROQ_API_KEY:
        logger.warning(
            "GROQ_API_KEY is not set. Chat endpoint will return an error until the key is configured in Backend/.env"
        )
        return
    _client = _create_client()
    logger.info("Groq client initialized (model: %s)", settings.GROQ_MODEL)


async def chat_completion(
    messages: list[dict],
    tools: list[dict] | None = None,
    temperature: float = 0.3,
    max_tokens: int = 1024,
) -> dict:
    """
    Non-streaming Groq chat completion.

    Returns the full response dict.
    Raises RateLimitError, APIStatusError, APIConnectionError as-is.
    """
    client = get_groq_client()
    settings = get_settings()

    kwargs: dict[str, Any] = {
        "model": settings.GROQ_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if tools:
        kwargs["tools"] = tools

    response = await client.chat.completions.create(**kwargs)
    return response


async def chat_completion_stream(
    messages: list[dict],
    tools: list[dict] | None = None,
    temperature: float = 0.3,
    max_tokens: int = 1024,
) -> AsyncGenerator:
    """
    Streaming Groq chat completion.

    Yields chunks from the stream.
    The caller must handle tool calls by collecting the full assistant message.
    """
    client = get_groq_client()
    settings = get_settings()

    kwargs: dict[str, Any] = {
        "model": settings.GROQ_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": True,
    }
    if tools:
        kwargs["tools"] = tools

    stream = await client.chat.completions.create(**kwargs)
    return stream


def handle_groq_error(error: Exception) -> str:
    """
    Map Groq exceptions to user-friendly messages.
    Never exposes API keys or internal details.
    """
    if isinstance(error, RateLimitError):
        logger.warning("Groq rate limit hit.")
        return "The AI service is temporarily rate-limited. Please try again shortly."
    if isinstance(error, APITimeoutError):
        logger.warning("Groq API timeout: %s", str(error))
        return "The AI service took too long to respond. Please try again."
    if isinstance(error, APIConnectionError):
        logger.error("Groq connection error: %s", str(error))
        return "Couldn't reach the AI service. Please check your connection and try again."
    if isinstance(error, APIStatusError):
        logger.error("Groq API status error %d: %s", error.status_code, error.message)
        if error.status_code == 503:
            return "The AI service is temporarily unavailable. Please try again shortly."
        return "The AI service encountered an error. Please try again."
    logger.error("Groq unexpected error: %s", str(error))
    return "Couldn't complete that request. Please try again."
