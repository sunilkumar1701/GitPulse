"""
Developer score controller.
Port of controllers/developerScore.controller.js.
"""

from app.services.developer_score_service import get_developer_score


async def handle_get_developer_score(username: str) -> dict:
    """
    Handle GET /api/github/developer-score/:username

    Returns:
        { success: true, data: { score, level } }
    """
    if not username or not username.strip():
        raise ValueError("Username is required.")

    data = await get_developer_score(username)
    return {"success": True, "data": data}
