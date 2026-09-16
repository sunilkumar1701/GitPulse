"""
GitHub service — fetches raw user/repo data from the GitHub REST API.
Port of the getGithubProfile() from services/github.service.js.
"""

import logging

from app.clients.github_client import github_get
from app.middleware.error_handler import handle_github_error

logger = logging.getLogger(__name__)


async def get_github_profile(username: str) -> dict:
    """
    Fetch a GitHub user profile.

    Args:
        username: GitHub username.

    Returns:
        GitHub user profile data dict.

    Raises:
        GitHubAPIException: On API errors.
    """
    try:
        if not username:
            raise ValueError("Username is required.")

        data = await github_get(f"/users/{username}")
        return data
    except Exception as error:
        handle_github_error(error, "Failed to fetch GitHub profile.")


async def get_user_repos(username: str, per_page: int = 100, sort: str | None = None) -> list[dict]:
    """
    Fetch repositories for a GitHub user.

    Args:
        username: GitHub username.
        per_page: Number of repos per page (max 100).
        sort: Sort field (e.g., "updated").

    Returns:
        List of repository dicts.
    """
    try:
        params = f"per_page={per_page}"
        if sort:
            params = f"sort={sort}&{params}"

        data = await github_get(f"/users/{username}/repos?{params}")
        return data if isinstance(data, list) else []
    except Exception as error:
        handle_github_error(error, "Failed to fetch repositories.")


async def get_repo_commits(username: str, repo_name: str, per_page: int = 100) -> list[dict]:
    """
    Fetch commits for a specific repository.
    Returns empty list on 404 (e.g., empty repos).
    """
    try:
        data = await github_get(f"/repos/{username}/{repo_name}/commits?per_page={per_page}")
        return data if isinstance(data, list) else []
    except Exception:
        # Expected 404s for empty repos — return empty list
        return []


async def get_repo_pulls(username: str, repo_name: str, per_page: int = 100) -> list[dict]:
    """
    Fetch pull requests for a specific repository.
    Returns empty list on 404.
    """
    try:
        data = await github_get(f"/repos/{username}/{repo_name}/pulls?state=all&per_page={per_page}")
        return data if isinstance(data, list) else []
    except Exception:
        return []


async def get_repo_readme(username: str, repo_name: str) -> dict | None:
    """
    Fetch the README for a specific repository.
    Returns None on 404 (no README).
    """
    try:
        data = await github_get(f"/repos/{username}/{repo_name}/readme")
        return data
    except Exception:
        return None


async def get_user_repo(username: str, repo_name: str) -> dict | None:
    """
    Fetch a specific repository by owner/name.
    Returns None on 404.
    """
    try:
        data = await github_get(f"/repos/{username}/{repo_name}")
        return data
    except Exception:
        return None
