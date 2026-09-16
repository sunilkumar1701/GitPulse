"""
Portfolio readiness analysis service.
Port of getPortfolioReadinessAnalysis() from services/github.service.js.

Scoring (5 checks × 20 points each = 100 max):
    Bio            = 20
    Profile Photo  = 20
    Website        = 20
    README Quality = 20
    Pinned Repos   = 20
"""

import asyncio
import logging

from app.clients.github_client import github_get
from app.middleware.error_handler import handle_github_error

logger = logging.getLogger(__name__)


async def get_portfolio_readiness_analysis(username: str) -> dict:
    """
    Analyze portfolio readiness for a GitHub user.

    Uses Promise.allSettled equivalent (asyncio gather with return_exceptions)
    to handle expected 404s gracefully.

    Returns:
        Dict with score, completed, total, and checks list.
    """
    try:
        # Parallel requests — mirrors Promise.allSettled in Node.js
        user_task = _safe_get(f"/users/{username}")
        readme_repo_task = _safe_get(f"/repos/{username}/{username}")
        repos_task = _safe_get(f"/users/{username}/repos?sort=updated&per_page=6")

        user, readme_repo, repos = await asyncio.gather(
            user_task, readme_repo_task, repos_task
        )

        # Default to empty dict if user fetch failed
        if user is None:
            user = {}

        # Filter non-fork repos
        non_fork_repos = []
        if isinstance(repos, list):
            non_fork_repos = [r for r in repos if not r.get("fork", False)]

        has_pinned_repos = len(non_fork_repos) > 0
        has_readme_repo = readme_repo is not None

        checks = [
            {
                "name": "Bio",
                "status": bool(user.get("bio", "") and str(user.get("bio", "")).strip()),
                "score": 20 if (user.get("bio", "") and str(user.get("bio", "")).strip()) else 0,
                "maxScore": 20,
            },
            {
                "name": "Profile Photo",
                "status": bool(user.get("avatar_url")),
                "score": 20 if user.get("avatar_url") else 0,
                "maxScore": 20,
            },
            {
                "name": "Website",
                "status": bool(user.get("blog", "") and str(user.get("blog", "")).strip()),
                "score": 20 if (user.get("blog", "") and str(user.get("blog", "")).strip()) else 0,
                "maxScore": 20,
            },
            {
                "name": "README Quality",
                "status": has_readme_repo,
                "score": 20 if has_readme_repo else 0,
                "maxScore": 20,
            },
            {
                "name": "Pinned Repos",
                "status": has_pinned_repos,
                "score": 20 if has_pinned_repos else 0,
                "maxScore": 20,
            },
        ]

        return {
            "score": sum(c["score"] for c in checks),
            "completed": sum(1 for c in checks if c["status"]),
            "total": len(checks),
            "checks": checks,
        }
    except Exception as error:
        handle_github_error(error, "Failed to fetch portfolio readiness.")


async def _safe_get(path: str):
    """
    Perform a GitHub GET request, returning None on failure.
    Equivalent to Promise.allSettled behavior.
    """
    try:
        return await github_get(path)
    except Exception:
        return None
