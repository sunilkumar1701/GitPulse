"""
Portfolio readiness Pydantic schemas.
"""

from pydantic import BaseModel


class PortfolioCheck(BaseModel):
    """Individual portfolio readiness check."""
    name: str
    status: bool
    score: int
    maxScore: int


class PortfolioReadinessData(BaseModel):
    """Portfolio readiness analysis."""
    score: int = 0
    completed: int = 0
    total: int = 0
    checks: list[PortfolioCheck] = []
