"""
GitHub API routes.
Port of routes/github.routes.js.

All routes are prefixed with /api/github in main.py.
"""

from fastapi import APIRouter, Depends
from app.core.auth import verify_supabase_token

from app.controllers.github_controller import (
    handle_get_profile,
    handle_get_profile_analysis,
    handle_get_repository_analysis,
    handle_get_technology_stack_analysis,
    handle_get_activity_analysis,
    handle_get_repository_quality_analysis,
    handle_get_portfolio_readiness_analysis,
    handle_get_most_starred_repository,
    handle_get_most_forked_repository,
    handle_get_activity_status,
)

router = APIRouter(dependencies=[Depends(verify_supabase_token)])


@router.get("/profile/{username}")
async def get_profile(username: str):
    """GET /api/github/profile/:username"""
    return await handle_get_profile(username)


@router.get("/analysis/{username}")
async def get_profile_analysis(username: str):
    """GET /api/github/analysis/:username"""
    return await handle_get_profile_analysis(username)


@router.get("/repository-analysis/{username}")
async def get_repository_analysis(username: str):
    """GET /api/github/repository-analysis/:username"""
    return await handle_get_repository_analysis(username)


@router.get("/technology-stack/{username}")
async def get_technology_stack_analysis(username: str):
    """GET /api/github/technology-stack/:username"""
    return await handle_get_technology_stack_analysis(username)


@router.get("/activity-analysis/{username}")
async def get_activity_analysis(username: str):
    """GET /api/github/activity-analysis/:username"""
    return await handle_get_activity_analysis(username)


@router.get("/repository-quality/{username}")
async def get_repository_quality_analysis(username: str):
    """GET /api/github/repository-quality/:username"""
    return await handle_get_repository_quality_analysis(username)


@router.get("/portfolio-readiness/{username}")
async def get_portfolio_readiness_analysis(username: str):
    """GET /api/github/portfolio-readiness/:username"""
    return await handle_get_portfolio_readiness_analysis(username)


@router.get("/most-starred-repository/{username}")
async def get_most_starred_repository(username: str):
    """GET /api/github/most-starred-repository/:username"""
    return await handle_get_most_starred_repository(username)


@router.get("/most-forked-repository/{username}")
async def get_most_forked_repository(username: str):
    """GET /api/github/most-forked-repository/:username"""
    return await handle_get_most_forked_repository(username)


@router.get("/activity-status/{username}")
async def get_activity_status(username: str):
    """GET /api/github/activity-status/:username"""
    return await handle_get_activity_status(username)
