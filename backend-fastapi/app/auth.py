import os
from datetime import datetime, timedelta, timezone

from pathlib import Path
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

# Load environment variables from local .env if available
try:
    from dotenv import load_dotenv
    load_dotenv()
    backend_env = Path(__file__).resolve().parent.parent / ".env"
    if backend_env.exists():
        load_dotenv(backend_env)
except ImportError:
    pass

import logging

logger = logging.getLogger("traveltrack.auth")

DEFAULT_DEV_SECRET = "default_traveltrack_jwt_secret_key_change_in_production"

def get_jwt_secret_key() -> str:
    key = (
        os.getenv("JWT_SECRET_KEY")
        or os.getenv("SECRET_KEY")
        or os.getenv("JWT_SECRET")
        or ""
    ).strip()

    if (key.startswith('"') and key.endswith('"')) or (key.startswith("'") and key.endswith("'")):
        key = key[1:-1].strip()

    is_prod = os.getenv("ENVIRONMENT", "").lower() in ["production", "prod"] or os.getenv("RENDER") is not None
    if not key:
        if is_prod:
            raise RuntimeError("CRITICAL SECURITY ERROR: JWT_SECRET_KEY environment variable is required in production!")
        logger.warning("SECURITY WARNING: Using fallback development JWT secret key. Set JWT_SECRET_KEY in production.")
        return DEFAULT_DEV_SECRET

    if len(key) < 32:
        logger.warning("SECURITY WARNING: JWT_SECRET_KEY is shorter than 32 characters, which provides weak entropy.")

    return key


SECRET_KEY = get_jwt_secret_key()
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

# HTTPBearer scheme enables the "Authorize" button in Swagger UI
security = HTTPBearer(auto_error=True)


def create_access_token(user_id: str) -> str:
    """
    Create a signed JWT access token containing the user_id as subject (sub).
    """
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    payload = {
        "sub": str(user_id),
        "exp": expire
    }

    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    """
    Validate the Bearer token and return the authenticated user's ID.
    Raises HTTP 401 Unauthorized for missing, invalid, or expired tokens.
    """
    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        user_id = payload.get("sub")

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing subject",
                headers={"WWW-Authenticate": "Bearer"}
            )

        return str(user_id)

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )