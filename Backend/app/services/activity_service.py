"""
Activity analysis service.
Port of getActivityAnalysis() and getActivityStatus() from services/github.service.js.
"""

import asyncio
import logging
from datetime import datetime, timedelta

from app.clients.github_client import github_get
from app.services.github_service import get_user_repos, get_repo_commits, get_repo_pulls
from app.utils.github_helpers import get_month_label
from app.middleware.error_handler import handle_github_error

logger = logging.getLogger(__name__)


async def get_activity_analysis(username: str) -> dict:
    """
    Analyze activity over the last 12 months (or account age, whichever is smaller).

    Returns:
        Dict with accountAgeMonths, monthsDisplayed, and activity list.
        Each activity entry: { label, month, year, commits, pullRequests, repositoriesCreated }
    """
    try:
        # Parallel fetch of user profile and repos
        user_task = github_get(f"/users/{username}")
        repos_task = github_get(f"/users/{username}/repos?per_page=100")

        user, all_repos = await asyncio.gather(user_task, repos_task)

        created_at = datetime.fromisoformat(
            user.get("created_at", "").replace("Z", "+00:00")
        )

        now = datetime.now(created_at.tzinfo) if created_at.tzinfo else datetime.now()

        account_age_months = (
            (now.year - created_at.year) * 12
            + (now.month - created_at.month)
            + 1
        )

        months_to_show = min(account_age_months, 12)

        # Build activity map for the last N months
        activity_map: dict[str, dict] = {}
        for i in range(months_to_show - 1, -1, -1):
            # Calculate the date for month (now - i months)
            year = now.year
            month = now.month - i
            while month <= 0:
                month += 12
                year -= 1

            date = datetime(year, month, 1)
            label = get_month_label(date)

            activity_map[label] = {
                "label": label,
                "month": date.strftime("%b"),
                "year": str(date.year)[-2:],
                "commits": 0,
                "pullRequests": 0,
                "repositoriesCreated": 0,
            }

        # Filter out forks
        repos = [r for r in all_repos if not r.get("fork", False)] if isinstance(all_repos, list) else []

        # Count repositories created per month
        for repo in repos:
            repo_created = repo.get("created_at", "")
            if repo_created:
                try:
                    repo_date = datetime.fromisoformat(repo_created.replace("Z", "+00:00"))
                    label = get_month_label(repo_date)
                    if label in activity_map:
                        activity_map[label]["repositoriesCreated"] += 1
                except (ValueError, TypeError):
                    pass

        # Fetch commits and PRs concurrently for all repos
        commit_tasks = [
            _fetch_commits_for_repo(username, repo.get("name", ""))
            for repo in repos
        ]
        pr_tasks = [
            _fetch_pulls_for_repo(username, repo.get("name", ""))
            for repo in repos
        ]

        commit_results, pr_results = await asyncio.gather(
            asyncio.gather(*commit_tasks, return_exceptions=True),
            asyncio.gather(*pr_tasks, return_exceptions=True),
        )

        # Process commit results
        for result in commit_results:
            if isinstance(result, Exception) or not isinstance(result, list):
                continue
            for commit in result:
                commit_date_str = None
                try:
                    commit_date_str = commit.get("commit", {}).get("author", {}).get("date")
                except (AttributeError, TypeError):
                    pass

                if not commit_date_str:
                    continue

                try:
                    commit_date = datetime.fromisoformat(commit_date_str.replace("Z", "+00:00"))
                    label = get_month_label(commit_date)
                    if label in activity_map:
                        activity_map[label]["commits"] += 1
                except (ValueError, TypeError):
                    pass

        # Process PR results
        for result in pr_results:
            if isinstance(result, Exception) or not isinstance(result, list):
                continue
            for pull in result:
                pr_date_str = pull.get("created_at", "")
                if not pr_date_str:
                    continue

                try:
                    pr_date = datetime.fromisoformat(pr_date_str.replace("Z", "+00:00"))
                    label = get_month_label(pr_date)
                    if label in activity_map:
                        activity_map[label]["pullRequests"] += 1
                except (ValueError, TypeError):
                    pass

        return {
            "accountAgeMonths": account_age_months,
            "monthsDisplayed": months_to_show,
            "activity": list(activity_map.values()),
        }
    except Exception as error:
        handle_github_error(error, "Failed to fetch activity analysis.")


async def get_activity_status(username: str) -> dict:
    """
    Determine the user's activity status.

    Thresholds (commits in last 30 days):
        >= 20  → "Highly Active"
        10–19  → "Moderate"
        1–9    → "Low"
        0      → "Inactive"

    Also calculates streak (consecutive days with commits from today backwards)
    and lastActive date.

    Returns:
        Dict with status, commitCount, streak, lastActive.
    """
    try:
        all_repos = await get_user_repos(username)

        repos = [r for r in all_repos if not r.get("fork", False)]

        thirty_days_ago = datetime.now() - timedelta(days=30)

        commit_count = 0
        last_active = None
        commit_days: set[str] = set()

        # Fetch commits for all repos concurrently
        commit_tasks = [
            _fetch_commits_for_repo(username, repo.get("name", ""))
            for repo in repos
        ]

        results = await asyncio.gather(*commit_tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception) or not isinstance(result, list):
                continue

            for commit in result:
                try:
                    commit_date_str = commit.get("commit", {}).get("author", {}).get("date")
                    if not commit_date_str:
                        continue

                    commit_date = datetime.fromisoformat(commit_date_str.replace("Z", "+00:00"))

                    # Track last active
                    if last_active is None or commit_date_str > last_active:
                        last_active = commit_date_str

                    # Track unique commit days
                    day = commit_date.strftime("%Y-%m-%d")
                    commit_days.add(day)

                    # Count commits in last 30 days
                    # Compare naive datetimes to match Node.js behavior
                    commit_naive = commit_date.replace(tzinfo=None)
                    if commit_naive >= thirty_days_ago:
                        commit_count += 1
                except (ValueError, TypeError, AttributeError):
                    continue

        # Determine status
        if commit_count >= 20:
            status = "Highly Active"
        elif commit_count >= 10:
            status = "Moderate"
        elif commit_count >= 1:
            status = "Low"
        else:
            status = "Inactive"

        # Calculate streak (consecutive days from today backwards)
        streak = 0
        current_date = datetime.now()
        while True:
            day = current_date.strftime("%Y-%m-%d")
            if day not in commit_days:
                break
            streak += 1
            current_date -= timedelta(days=1)

        return {
            "status": status,
            "commitCount": commit_count,
            "streak": streak,
            "lastActive": last_active,
        }
    except Exception as error:
        handle_github_error(error, "Failed to fetch activity status.")


async def _fetch_commits_for_repo(username: str, repo_name: str) -> list[dict]:
    """Fetch commits for a repo, returning empty list on failure."""
    return await get_repo_commits(username, repo_name)


async def _fetch_pulls_for_repo(username: str, repo_name: str) -> list[dict]:
    """Fetch PRs for a repo, returning empty list on failure."""
    return await get_repo_pulls(username, repo_name)
