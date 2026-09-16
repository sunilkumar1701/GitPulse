"""
Repository-related Pydantic schemas.
"""

from pydantic import BaseModel
from typing import Optional


class TopRepoData(BaseModel):
    """Top repository info."""
    name: str
    html_url: str
    stars: int
    forks: int


class RepositoryAnalysisData(BaseModel):
    """Repository analysis returned by GET /api/github/repository-analysis/:username"""
    total_repos: int = 0
    total_stars: int = 0
    total_forks: int = 0
    top_repo: Optional[TopRepoData] = None


class MostStarredRepoData(BaseModel):
    """Most starred repository."""
    name: str
    html_url: str
    stars: int
    language: str = "Unknown"


class MostForkedRepoData(BaseModel):
    """Most forked repository."""
    name: str
    html_url: str
    forks: int
    language: str = "Unknown"
