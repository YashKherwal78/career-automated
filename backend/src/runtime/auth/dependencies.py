import urllib.request
import json
import logging
from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from pydantic import BaseModel, EmailStr
from src.runtime.config.settings import Settings
from src.runtime.postgres.connection import get_connection

logger = logging.getLogger("auth")

security = HTTPBearer()

# JWKS cache structures
_jwks_cache: Dict[str, Dict[str, Any]] = {}

class CurrentUser(BaseModel):
    user_id: str
    email: EmailStr
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    onboarding_complete: bool = False


def fetch_jwks() -> Dict[str, Any]:
    """Retrieve JWKS public keys directly from Supabase project."""
    url = f"{Settings.SUPABASE_URL.rstrip('/')}/auth/v1/.well-known/jwks.json"
    try:
        req = urllib.request.Request(
            url,
            headers={"apikey": Settings.SUPABASE_SERVICE_ROLE_KEY} if Settings.SUPABASE_SERVICE_ROLE_KEY else {}
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            return json.loads(response.read().decode())
    except Exception as e:
        logger.error(f"Failed to retrieve JWKS from Supabase: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service temporarily unavailable"
        )


def get_public_key(kid: str) -> Dict[str, Any]:
    """Retrieve public key matching kid parameter with lazy refresh."""
    global _jwks_cache
    if kid in _jwks_cache:
        return _jwks_cache[kid]
    
    # Lazy refresh cache
    jwks = fetch_jwks()
    keys = jwks.get("keys", [])
    for key in keys:
        k_id = key.get("kid")
        if k_id:
            _jwks_cache[k_id] = key
            
    if kid in _jwks_cache:
        return _jwks_cache[kid]
        
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid token signature key identifier"
    )


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> CurrentUser:
    """Validate incoming token and return CurrentUser structure."""
    token = credentials.credentials
    try:
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")
        if not kid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token header missing key identifier (kid)"
            )
            
        public_key = get_public_key(kid)
        
        # Use algorithm declared in the JWKS key (Supabase uses ES256, not RS256)
        key_alg = public_key.get("alg", "RS256")
        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256", "ES256"],
            audience="authenticated"
        )
        
        user_id = payload.get("sub")
        email = payload.get("email")
        if not user_id or not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload parameters"
            )
            
    except JWTError as e:
        logger.warning(f"JWT Verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token credentials: {str(e)}"
        )
        
    # Query public.user_profiles to load detailed metadata
    # NOTE: user_profiles lives in Supabase (AUTH_DATABASE_URL) — Google OAuth creates rows there.
    try:
        with get_auth_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT email, full_name, avatar_url, onboarding_complete FROM public.user_profiles WHERE user_id = %s",
                (user_id,)
            )
            row = cursor.fetchone()
            if row:
                # Support dictionary and sqlite Row styles compatibly
                if hasattr(row, "keys"):
                    data = dict(row)
                else:
                    data = {
                        "email": row[0],
                        "full_name": row[1],
                        "avatar_url": row[2],
                        "onboarding_complete": bool(row[3])
                    }
                return CurrentUser(
                    user_id=user_id,
                    email=data.get("email", email),
                    full_name=data.get("full_name"),
                    avatar_url=data.get("avatar_url"),
                    onboarding_complete=bool(data.get("onboarding_complete", False))
                )
    except Exception as e:
        logger.error(f"Error loading user profile from database: {e}")
        
    # Return default fallback if profile trigger is delayed
    return CurrentUser(
        user_id=user_id,
        email=email,
        full_name="",
        avatar_url="",
        onboarding_complete=False
    )
