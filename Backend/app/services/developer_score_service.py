"""
Developer score calculation service.
Port of getDeveloperScore() from services/github.service.js.

Scoring formula (exact port):
    Followers:  >=20 → 10, >=10 → 8, >=5 → 6, >=1 → 3
    Repos:      >=20 → 20, >=15 → 15, >=10 → 10, >=5 → 5
    Stars:      >=20 → 10, >=10 → 8, >=5 → 6, >=1 → 3
    Forks:      >=10 → 10, >=5 → 8, >=1 → 4
    Activity:   Highly Active → 25, Moderate → 15, Low → 5
    Portfolio:  round(portfolio_score * 0.25)

    Max: 100

Levels:
    >= 80 → Expert
    >= 60 → Advanced
    >= 40 → Intermediate
    else  → Beginner
"""

import asyncio
import logging

from app.services.profile_service import get_profile_analysis
from app.services.repository_service import get_repository_analysis
from app.services.portfolio_service import get_portfolio_readiness_analysis
from app.services.activity_service import get_activity_status
from app.middleware.error_handler import handle_github_error

logger = logging.getLogger(__name__)


async def get_developer_score(username: str) -> dict:
    """
    Calculate the overall developer score.

    Combines profile, repository, portfolio, and activity data.

    Returns:
        Dict with score (0-100) and level string.
    """
    try:
        # Parallel fetch of all required data
        profile, repository, portfolio, activity = await asyncio.gather(
            get_profile_analysis(username),
            get_repository_analysis(username),
            get_portfolio_readiness_analysis(username),
            get_activity_status(username),
        )

        score = 0

        # Followers
        followers = profile.get("followers", 0)
        if followers >= 20:
            score += 10
        elif followers >= 10:
            score += 8
        elif followers >= 5:
            score += 6
        elif followers >= 1:
            score += 3

        # Repositories
        total_repos = repository.get("total_repos", 0)
        if total_repos >= 20:
            score += 20
        elif total_repos >= 15:
            score += 15
        elif total_repos >= 10:
            score += 10
        elif total_repos >= 5:
            score += 5

        # Stars
        total_stars = repository.get("total_stars", 0)
        if total_stars >= 20:
            score += 10
        elif total_stars >= 10:
            score += 8
        elif total_stars >= 5:
            score += 6
        elif total_stars >= 1:
            score += 3

        # Forks
        total_forks = repository.get("total_forks", 0)
        if total_forks >= 10:
            score += 10
        elif total_forks >= 5:
            score += 8
        elif total_forks >= 1:
            score += 4

        # Activity
        activity_status = activity.get("status", "Inactive")
        if activity_status == "Highly Active":
            score += 25
        elif activity_status == "Moderate":
            score += 15
        elif activity_status == "Low":
            score += 5

        # Portfolio
        portfolio_score = portfolio.get("score", 0)
        score += round(portfolio_score * 0.25)

        # Cap at 100
        score = min(score, 100)

        # Determine level
        if score >= 80:
            level = "Expert"
        elif score >= 60:
            level = "Advanced"
        elif score >= 40:
            level = "Intermediate"
        else:
            level = "Beginner"

        return {
            "score": score,
            "level": level,
        }
    except Exception as error:
        handle_github_error(error, "Failed to calculate developer score.")
