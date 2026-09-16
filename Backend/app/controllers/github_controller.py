"""
GitHub controller — request/response orchestration for all GitHub analysis endpoints.
Port of controllers/github.controller.js.
"""

from app.services.github_service import get_github_profile
from app.services.profile_service import get_profile_analysis
from app.services.repository_service import (
    get_repository_analysis,
    get_most_starred_repository,
    get_most_forked_repository,
)
from app.services.technology_service import get_technology_stack_analysis
from app.services.activity_service import get_activity_analysis, get_activity_status
from app.services.repository_quality_service import get_repository_quality_analysis
from app.services.portfolio_service import get_portfolio_readiness_analysis


def _validate_username(username: str) -> bool:
    """Validate that a username is provided and non-empty."""
    return bool(username and username.strip())


async def handle_get_profile(username: str) -> dict:
    """
    Handle GET /api/github/profile/:username

    Returns:
        { success: true, data: { name, login, avatar_url, location, blog } }
    """
    if not _validate_username(username):
        raise ValueError("Username is required.")

    profile = await get_github_profile(username)

    return {
        "success": True,
        "data": {
            "name": profile.get("name"),
            "login": profile.get("login"),
            "avatar_url": profile.get("avatar_url"),
            "location": profile.get("location"),
            "blog": profile.get("blog"),
        },
    }


async def handle_get_profile_analysis(username: str) -> dict:
    """Handle GET /api/github/analysis/:username"""
    if not _validate_username(username):
        raise ValueError("Username is required.")

    data = await get_profile_analysis(username)
    return {"success": True, "data": data}


async def handle_get_repository_analysis(username: str) -> dict:
    """Handle GET /api/github/repository-analysis/:username"""
    if not _validate_username(username):
        raise ValueError("Username is required.")

    data = await get_repository_analysis(username)
    return {"success": True, "data": data}


async def handle_get_technology_stack_analysis(username: str) -> dict:
    """Handle GET /api/github/technology-stack/:username"""
    if not _validate_username(username):
        raise ValueError("Username is required.")

    data = await get_technology_stack_analysis(username)
    return {"success": True, "data": data}


async def handle_get_activity_analysis(username: str) -> dict:
    """Handle GET /api/github/activity-analysis/:username"""
    if not _validate_username(username):
        raise ValueError("Username is required.")

    data = await get_activity_analysis(username)
    return {"success": True, "data": data}


async def handle_get_repository_quality_analysis(username: str) -> dict:
    """Handle GET /api/github/repository-quality/:username"""
    if not _validate_username(username):
        raise ValueError("Username is required.")

    data = await get_repository_quality_analysis(username)
    return {"success": True, "data": data}


async def handle_get_portfolio_readiness_analysis(username: str) -> dict:
    """Handle GET /api/github/portfolio-readiness/:username"""
    if not _validate_username(username):
        raise ValueError("Username is required.")

    data = await get_portfolio_readiness_analysis(username)
    return {"success": True, "data": data}


async def handle_get_most_starred_repository(username: str) -> dict:
    """Handle GET /api/github/most-starred-repository/:username"""
    if not _validate_username(username):
        raise ValueError("Username is required.")

    data = await get_most_starred_repository(username)
    return {"success": True, "data": data}


async def handle_get_most_forked_repository(username: str) -> dict:
    """Handle GET /api/github/most-forked-repository/:username"""
    if not _validate_username(username):
        raise ValueError("Username is required.")

    data = await get_most_forked_repository(username)
    return {"success": True, "data": data}


async def handle_get_activity_status(username: str) -> dict:
    """Handle GET /api/github/activity-status/:username"""
    if not _validate_username(username):
        raise ValueError("Username is required.")

    data = await get_activity_status(username)
    return {"success": True, "data": data}
