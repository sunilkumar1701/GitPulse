"""
Profile-related Pydantic schemas.
"""

from pydantic import BaseModel
from typing import Optional


class ProfileData(BaseModel):
    """Basic profile info returned by GET /api/github/profile/:username"""
    name: Optional[str] = None
    login: Optional[str] = None
    avatar_url: Optional[str] = None
    location: Optional[str] = None
    blog: Optional[str] = None


class RecentRepo(BaseModel):
    """Recent repository info."""
    name: str
    html_url: str
    updated_at: str


class ProfileAnalysisData(BaseModel):
    """Profile analysis returned by GET /api/github/analysis/:username"""
    followers: int = 0
    following: int = 0
    public_repos: int = 0
    recent_repo: Optional[RecentRepo] = None
