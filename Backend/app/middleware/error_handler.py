"""
Centralized error handling for FastAPI.
Ports the behavior from:
  - middleware/errorHandler.js
  - middleware/githubErrorHandler.js
"""

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import httpx

logger = logging.getLogger(__name__)


class GitHubAPIException(Exception):
    """Custom exception for GitHub API errors."""

    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(self.message)


class MCPException(Exception):
    """Custom exception for MCP errors."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)



def handle_github_error(error: Exception, default_message: str = "GitHub request failed.") -> None:
    """
    Process a GitHub API error and raise an appropriate GitHubAPIException.
    Exact port of middleware/githubErrorHandler.js.

    Args:
        error: The caught exception.
        default_message: Fallback error message.

    Raises:
        GitHubAPIException: Always raised with the appropriate status code and message.
    """
    if isinstance(error, httpx.HTTPStatusError):
        status = error.response.status_code

        # Log the error (no secrets)
        try:
            error_data = error.response.json()
            logger.error("GitHub Service Error: %s", error_data.get("message", str(error)))
        except Exception:
            logger.error("GitHub Service Error: %s", str(error))

        if status == 404:
            raise GitHubAPIException(404, "GitHub resource not found.")
        elif status == 403:
            raise GitHubAPIException(403, "GitHub API rate limit exceeded.")
        elif status == 401:
            raise GitHubAPIException(401, "Invalid GitHub credentials.")
        else:
            try:
                msg = error.response.json().get("message", default_message)
            except Exception:
                msg = default_message
            raise GitHubAPIException(status, msg)

    # Non-HTTP errors
    logger.error("GitHub Service Error: %s", str(error))
    raise GitHubAPIException(500, getattr(error, "message", None) or str(error) or default_message)


def register_exception_handlers(app: FastAPI) -> None:
    """
    Register global exception handlers on the FastAPI application.
    Mirrors the errorHandler.js middleware.
    """

    @app.exception_handler(GitHubAPIException)
    async def github_api_exception_handler(request: Request, exc: GitHubAPIException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "message": exc.message,
            },
        )

    @app.exception_handler(MCPException)
    async def mcp_exception_handler(request: Request, exc: MCPException) -> JSONResponse:
        return JSONResponse(
            status_code=502,
            content={
                "success": False,
                "message": exc.message,
            },
        )

    @app.exception_handler(ValueError)
    async def validation_exception_handler(request: Request, exc: ValueError) -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "message": str(exc),
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error("Unhandled error: %s", str(exc), exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": "Internal Server Error",
            },
        )
