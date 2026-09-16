"""
Technology stack analysis service.
Port of getTechnologyStackAnalysis() from services/github.service.js.
"""

import logging

from app.services.github_service import get_user_repos
from app.middleware.error_handler import handle_github_error

logger = logging.getLogger(__name__)


async def get_technology_stack_analysis(username: str) -> dict:
    """
    Analyze the technology/language stack of a user's repositories.

    Returns:
        Dict with total_languages and top_languages (top 5 by repo count).
        Each language has: name, value (percentage), repos (count).
    """
    try:
        if not username:
            raise ValueError("Username is required.")

        repos = await get_user_repos(username)

        language_count: dict[str, int] = {}

        for repo in repos:
            language = repo.get("language")
            if not language:
                continue
            language_count[language] = language_count.get(language, 0) + 1

        total_language_repos = sum(language_count.values())

        if total_language_repos == 0:
            return {
                "total_languages": 0,
                "top_languages": [],
            }

        # Build top languages list sorted by repo count descending, take top 5
        top_languages = sorted(
            [
                {
                    "name": name,
                    "value": round((count / total_language_repos) * 100),
                    "repos": count,
                }
                for name, count in language_count.items()
            ],
            key=lambda x: x["repos"],
            reverse=True,
        )[:5]

        return {
            "total_languages": len(top_languages),
            "top_languages": top_languages,
        }
    except Exception as error:
        handle_github_error(error, "Failed to fetch technology stack analysis.")
