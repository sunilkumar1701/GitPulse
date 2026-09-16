import logging
from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import create_client, Client
from app.core.config import get_settings

logger = logging.getLogger(__name__)
security = HTTPBearer()

def get_supabase_client() -> Client:
    settings = get_settings()
    if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
        logger.error("SUPABASE_URL or SUPABASE_KEY is missing in backend config")
        raise HTTPException(status_code=500, detail="Internal server configuration error")
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

def verify_supabase_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    """
    FastAPI dependency to verify Supabase JWT tokens via Supabase Auth API.
    """
    token = credentials.credentials
    if not token:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")

    try:
        settings = get_settings()
        
        # 1. Try local offline verification first if secret is provided (works for HS256)
        if settings.SUPABASE_JWT_SECRET:
            import jwt
            try:
                decoded_token = jwt.decode(
                    token, 
                    settings.SUPABASE_JWT_SECRET, 
                    algorithms=["HS256"], 
                    options={"verify_audience": False}
                )
                return decoded_token
            except jwt.ExpiredSignatureError:
                raise HTTPException(status_code=401, detail="Token has expired")
            except jwt.InvalidAlgorithmError:
                # Token is using new ES256 asymmetric keys. We must verify via network, 
                # or fallback to unverified decode if we are offline.
                pass
            except jwt.InvalidTokenError as e:
                logger.error(f"Local JWT decode failed: {str(e)}")
        
        # 2. Fallback to network verification (requires internet connection)
        supabase = get_supabase_client()
        try:
            user_response = supabase.auth.get_user(token)
            if not user_response or not user_response.user:
                raise HTTPException(status_code=401, detail="Invalid token")
            return user_response.user
        except Exception as network_error:
            # 3. Ultimate Offline Fallback: If network is down, we allow viewing cached data
            error_str = str(network_error)
            if "getaddrinfo failed" in error_str or "Name or service not known" in error_str or "nodename nor servname provided" in error_str:
                import jwt
                logger.warning("Network is offline. Bypassing JWT signature verification for cached data access.")
                # Decode without signature verification just to check expiration
                decoded_token = jwt.decode(token, options={"verify_signature": False, "verify_audience": False})
                return decoded_token
            raise network_error
        
    except Exception as e:
        logger.error(f"Auth error: {str(e)}")
        raise HTTPException(status_code=401, detail="Authentication failed or token expired")
