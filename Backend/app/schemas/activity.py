"""
Activity-related Pydantic schemas.
"""

from pydantic import BaseModel
from typing import Optional


class MonthlyActivity(BaseModel):
    """Activity data for a single month."""
    label: str
    month: str
    year: str
    commits: int = 0
    pullRequests: int = 0
    repositoriesCreated: int = 0


class ActivityAnalysisData(BaseModel):
    """Activity analysis over 12 months."""
    accountAgeMonths: int = 0
    monthsDisplayed: int = 0
    activity: list[MonthlyActivity] = []


class ActivityStatusData(BaseModel):
    """Activity status with streak info."""
    status: str = "Inactive"
    commitCount: int = 0
    streak: int = 0
    lastActive: Optional[str] = None
