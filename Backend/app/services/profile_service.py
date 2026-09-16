"""
Profile analysis service.
Port of getProfileAnalysis() from services/github.service.js.
"""

import asyncio
import logging

from app.clients.github_client import github_get
from app.middleware.error_handler import handle_github_error

logger = logging.getLogger(__name__)


async def get_profile_analysis(username: str) -> dict:
    """
    Analyze a GitHub user's profile.

    Returns:
        Dict with followers, following, public_repos, and recent_repo.
    """
    try:
        if not username:
            raise ValueError("Username is required.")

        # Parallel requests — matches Promise.all in Node.js
        user_task = github_get(f"/users/{username}")
        repos_task = github_get(f"/users/{username}/repos?sort=updated&per_page=1")

        user, repos = await asyncio.gather(user_task, repos_task)

        recent_repo = None
        if isinstance(repos, list) and len(repos) > 0:
            repo = repos[0]
            recent_repo = {
                "name": repo.get("name"),
                "html_url": repo.get("html_url"),
                "updated_at": repo.get("updated_at"),
            }

        return {
            "followers": user.get("followers", 0),
            "following": user.get("following", 0),
            "public_repos": user.get("public_repos", 0),
            "recent_repo": recent_repo,
        }
    except Exception as error:
        handle_github_error(error, "Failed to fetch profile analysis.")
