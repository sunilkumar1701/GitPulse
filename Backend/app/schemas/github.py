"""
Common/shared Pydantic schemas for API responses.
"""

from pydantic import BaseModel
from typing import Any


class SuccessResponse(BaseModel):
    """Standard success response wrapper: { success: true, data: ... }"""
    success: bool = True
    data: Any = None


class ErrorResponse(BaseModel):
    """Standard error response: { success: false, message: ... }"""
    success: bool = False
    message: str = "An error occurred."
