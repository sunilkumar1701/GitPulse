"""
Repository quality analysis service.
Port of getRepositoryQualityAnalysis() from services/github.service.js.

Scoring formula:
    README     = 30%
    Description = 30%
    Topics      = 20%
    Documentation = 20% (README word count >= 100)
    Maximum: 100%
"""

import asyncio
import base64
import re
import logging

from app.services.github_service import get_user_repos, get_repo_readme
from app.middleware.error_handler import handle_github_error

logger = logging.getLogger(__name__)


async def get_repository_quality_analysis(username: str) -> dict:
    """
    Analyze the quality of a user's repositories.

    Returns:
        Dict with total_repos, score, metrics (readme, description, documentation, topics),
        and counts.
    """
    try:
        repos = await get_user_repos(username)

        # Filter out forks
        filtered_repos = [r for r in repos if not r.get("fork", False)]
        total_repos = len(filtered_repos)

        if not total_repos:
            return {
                "score": 0,
                "metrics": {
                    "readme": 0,
                    "description": 0,
                    "documentation": 0,
                    "topics": 0,
                },
            }

        # Count repos with descriptions and topics
        description_count = 0
        topics_count = 0

        for repo in filtered_repos:
            desc = repo.get("description")
            if desc and str(desc).strip():
                description_count += 1

            topics = repo.get("topics")
            if topics and len(topics) > 0:
                topics_count += 1

        # Fetch READMEs concurrently
        readme_tasks = [
            get_repo_readme(username, repo.get("name", ""))
            for repo in filtered_repos
        ]

        results = await asyncio.gather(*readme_tasks, return_exceptions=True)

        readme_count = 0
        documentation_count = 0

        for result in results:
            if isinstance(result, Exception) or result is None:
                continue

            readme_count += 1

            # Decode base64 content and count words
            content_b64 = result.get("content", "")
            if content_b64:
                try:
                    content = base64.b64decode(content_b64).decode("utf-8")

                    # Strip markdown formatting — matches the Node.js regex:
                    # .replace(/[#*_`\-\[\]\(\)]/g, "")
                    cleaned = re.sub(r'[#*_`\-\[\]\(\)]', '', content)

                    # Split on whitespace and filter empty strings
                    words = [w for w in cleaned.split() if w]
                    word_count = len(words)

                    if word_count >= 100:
                        documentation_count += 1
                except Exception:
                    pass

        # Calculate scores
        readme_score = (readme_count / total_repos) * 30
        description_score = (description_count / total_repos) * 30
        documentation_score = (documentation_count / total_repos) * 20
        topics_score = (topics_count / total_repos) * 20

        return {
            "total_repos": total_repos,
            "score": round(readme_score + description_score + documentation_score + topics_score),
            "metrics": {
                "readme": round(readme_score),
                "description": round(description_score),
                "documentation": round(documentation_score),
                "topics": round(topics_score),
            },
            "counts": {
                "readme": readme_count,
                "description": description_count,
                "documentation": documentation_count,
                "topics": topics_count,
            },
        }
    except Exception as error:
        handle_github_error(error, "Failed to fetch repository quality analysis.")
