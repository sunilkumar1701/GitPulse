import logging
from fastapi import APIRouter, Depends, HTTPException
from supabase import create_client, Client

from app.core.auth import verify_supabase_token
from app.core.config import get_settings

router = APIRouter(dependencies=[Depends(verify_supabase_token)])
logger = logging.getLogger(__name__)

def get_supabase_admin() -> Client:
    settings = get_settings()
    if not settings.SUPABASE_URL or not settings.SUPABASE_SECRET_KEY:
        logger.error("SUPABASE_URL or SUPABASE_SECRET_KEY is missing in backend config")
        raise HTTPException(status_code=500, detail="Internal server configuration error")
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SECRET_KEY)

@router.delete("/account")
async def delete_user_account(auth_user=Depends(verify_supabase_token)):
    """
    Securely delete the authenticated user's account using the Supabase Admin API.
    """
    if not auth_user or not auth_user.id:
        raise HTTPException(status_code=401, detail="Unauthorized")
        
    user_id = auth_user.id
    
    try:
        supabase_admin = get_supabase_admin()
        
        # In a real app with user-owned public tables, you'd delete them here:
        # supabase_admin.table('profiles').delete().eq('user_id', user_id).execute()
        # Since this app doesn't have custom public tables, we just delete the Auth user.
        
        response = supabase_admin.auth.admin.delete_user(user_id)
        
        return {"success": True, "message": "Account deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete user account")
