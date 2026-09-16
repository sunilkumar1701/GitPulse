"""
Repository analysis service.
Port of getRepositoryAnalysis(), getMostStarredRepository(),
getMostForkedRepository() from services/github.service.js.
"""

import logging
from datetime import datetime

from app.services.github_service import get_user_repos
from app.middleware.error_handler import handle_github_error

logger = logging.getLogger(__name__)


async def get_repository_analysis(username: str) -> dict:
    """
    Analyze a user's repositories.

    Returns:
        Dict with total_repos, total_stars, total_forks, and top_repo.
        Exact port of the Node.js implementation including tiebreaker logic.
    """
    try:
        if not username:
            raise ValueError("Username is required.")

        repos = await get_user_repos(username)

        if not repos:
            return {
                "total_repos": 0,
                "total_stars": 0,
                "total_forks": 0,
                "top_repo": None,
            }

        total_stars = sum(r.get("stargazers_count", 0) for r in repos)
        total_forks = sum(r.get("forks_count", 0) for r in repos)

        # Find top repo — same logic as Node.js:
        # 1. Highest stars
        # 2. Highest forks (tiebreaker)
        # 3. Most recently updated (tiebreaker)
        top_repo = repos[0]
        for repo in repos[1:]:
            if repo.get("stargazers_count", 0) > top_repo.get("stargazers_count", 0):
                top_repo = repo
            elif (
                repo.get("stargazers_count", 0) == top_repo.get("stargazers_count", 0)
                and repo.get("forks_count", 0) > top_repo.get("forks_count", 0)
            ):
                top_repo = repo
            elif (
                repo.get("stargazers_count", 0) == top_repo.get("stargazers_count", 0)
                and repo.get("forks_count", 0) == top_repo.get("forks_count", 0)
                and _parse_date(repo.get("updated_at")) > _parse_date(top_repo.get("updated_at"))
            ):
                top_repo = repo

        return {
            "total_repos": len(repos),
            "total_stars": total_stars,
            "total_forks": total_forks,
            "top_repo": {
                "name": top_repo.get("name"),
                "html_url": top_repo.get("html_url"),
                "stars": top_repo.get("stargazers_count", 0),
                "forks": top_repo.get("forks_count", 0),
            },
        }
    except Exception as error:
        handle_github_error(error, "Failed to fetch repository analysis.")


async def get_most_starred_repository(username: str) -> dict | None:
    """
    Find the repository with the most stars.
    Tiebreaker: most recently updated.

    Returns:
        Dict with name, html_url, stars, language or None.
    """
    try:
        repos = await get_user_repos(username)

        if not repos:
            return None

        best = repos[0]
        for repo in repos[1:]:
            if repo.get("stargazers_count", 0) > best.get("stargazers_count", 0):
                best = repo
            elif (
                repo.get("stargazers_count", 0) == best.get("stargazers_count", 0)
                and _parse_date(repo.get("updated_at")) > _parse_date(best.get("updated_at"))
            ):
                best = repo

        return {
            "name": best.get("name"),
            "html_url": best.get("html_url"),
            "stars": best.get("stargazers_count", 0),
            "language": best.get("language") or "Unknown",
        }
    except Exception as error:
        handle_github_error(error, "Failed to fetch most starred repository.")


async def get_most_forked_repository(username: str) -> dict | None:
    """
    Find the repository with the most forks.
    Tiebreaker: most recently updated.

    Returns:
        Dict with name, html_url, forks, language or None.
    """
    try:
        repos = await get_user_repos(username)

        if not repos:
            return None

        best = repos[0]
        for repo in repos[1:]:
            if repo.get("forks_count", 0) > best.get("forks_count", 0):
                best = repo
            elif (
                repo.get("forks_count", 0) == best.get("forks_count", 0)
                and _parse_date(repo.get("updated_at")) > _parse_date(best.get("updated_at"))
            ):
                best = repo

        return {
            "name": best.get("name"),
            "html_url": best.get("html_url"),
            "forks": best.get("forks_count", 0),
            "language": best.get("language") or "Unknown",
        }
    except Exception as error:
        handle_github_error(error, "Failed to fetch most forked repository.")


def _parse_date(date_str: str | None) -> datetime:
    """Parse an ISO date string, returning epoch on failure."""
    if not date_str:
        return datetime.min
    try:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return datetime.min
