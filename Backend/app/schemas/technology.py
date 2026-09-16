"""
Technology stack Pydantic schemas.
"""

from pydantic import BaseModel


class LanguageData(BaseModel):
    """Individual language entry."""
    name: str
    value: int  # Percentage
    repos: int  # Number of repos using this language


class TechnologyStackData(BaseModel):
    """Technology stack analysis."""
    total_languages: int = 0
    top_languages: list[LanguageData] = []
