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
        
    # Query user_profiles and operational tables to load detailed metadata & onboarding state
    try:
        is_onboarded = False
        email_val = email
        full_name_val = ""
        avatar_url_val = ""

        with get_auth_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT email, full_name, avatar_url, onboarding_complete FROM public.user_profiles WHERE user_id = %s",
                (user_id,)
            )
            row = cursor.fetchone()
            if row:
                email_val = row[0] or email
                full_name_val = row[1] or ""
                avatar_url_val = row[2] or ""
                is_onboarded = bool(row[3])

        # If not marked onboarded in auth user_profiles, check user_career_profiles & user_resumes
        if not is_onboarded:
            try:
                with get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT 1 FROM public.user_career_profiles WHERE user_id = %s UNION ALL SELECT 1 FROM public.user_resumes WHERE user_id = %s",
                        (user_id, user_id)
                    )
                    if cursor.fetchone():
                        is_onboarded = True
            except Exception:
                pass

        return CurrentUser(
            user_id=user_id,
            email=email_val,
            full_name=full_name_val,
            avatar_url=avatar_url_val,
            onboarding_complete=is_onboarded
        )
    except Exception as e:
        logger.error(f"Error loading user profile from database: {e}")
        
    return CurrentUser(
        user_id=user_id,
        email=email,
        full_name="",
        avatar_url="",
        onboarding_complete=True
    )
