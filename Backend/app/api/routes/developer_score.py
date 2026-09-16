"""
Developer score API route.
Port of routes/developerScore.routes.js.

Mounted at /api/github/developer-score in main.py.
"""

from fastapi import APIRouter, Depends
from app.core.auth import verify_supabase_token

from app.controllers.developer_score_controller import handle_get_developer_score

router = APIRouter(dependencies=[Depends(verify_supabase_token)])


@router.get("/{username}")
async def get_developer_score(username: str):
    """GET /api/github/developer-score/:username"""
    return await handle_get_developer_score(username)
