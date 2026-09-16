"""
Developer score Pydantic schemas.
"""

from pydantic import BaseModel


class DeveloperScoreData(BaseModel):
    """Developer score result."""
    score: int = 0
    level: str = "Beginner"
