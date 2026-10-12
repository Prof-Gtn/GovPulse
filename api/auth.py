"""
GovPulse API — Authentication
JWT-based login using users stored in the SQLite database.
"""

import os
import sys
import bcrypt
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError


# Make sure we can import from src/
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src import db


# JWT configuration
JWT_SECRET = os.getenv("JWT_SECRET", "govpulse_dev_secret_change_in_production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 8


# Bearer token extraction
security = HTTPBearer()


# ------------------------------------------------------------
# PASSWORD VERIFICATION
# ------------------------------------------------------------
def verify_password(plain: str, hashed: str) -> bool:
    """Check password against stored hash using bcrypt directly."""
    try:
        plain_bytes = plain.encode("utf-8")[:72]
        hashed_bytes = hashed.encode("utf-8")
        return bcrypt.checkpw(plain_bytes, hashed_bytes)
    except Exception as e:
        print(f"[AUTH] bcrypt error: {e}")
        return False


# ------------------------------------------------------------
# AUTHENTICATION
# ------------------------------------------------------------
def authenticate_user(username: str, password: str) -> Optional[dict]:
    """Return the user dict if credentials are correct, else None."""
    user = db.get_user(username)
    if not user:
        return None
    if not verify_password(password, user["password_hash"]):
        return None
    return user


# ------------------------------------------------------------
# JWT
# ------------------------------------------------------------
def create_access_token(username: str) -> str:
    """Generate a JWT token for the given username."""
    expire = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRE_HOURS)
    payload = {
        "sub": username,
        "exp": expire,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode a JWT token. Raises HTTPException if invalid."""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ------------------------------------------------------------
# CURRENT USER
# ------------------------------------------------------------
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """Extract and validate the current user from the Authorization header."""
    payload = decode_token(credentials.credentials)
    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.get_user(username)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user


# ------------------------------------------------------------
# ROLE ENFORCEMENT
# ------------------------------------------------------------
def require_admin(user: dict = Depends(get_current_user)) -> dict:
    """Ensure the current user is an admin."""
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


def require_admin_or_analyst(user: dict = Depends(get_current_user)) -> dict:
    """Ensure the current user is admin or analyst."""
    if user.get("role") not in ("admin", "analyst"):
        raise HTTPException(status_code=403, detail="Analyst access required")
    return user


def require_ministry(user: dict = Depends(get_current_user)) -> dict:
    """Ensure the current user is a ministry user."""
    if user.get("role") != "ministry":
        raise HTTPException(status_code=403, detail="Ministry access required")
    return user


def require_any_role(roles: list):
    """Factory: require one of the given roles."""
    def _checker(user: dict = Depends(get_current_user)) -> dict:
        if user.get("role") not in roles:
            raise HTTPException(
                status_code=403,
                detail=f"Access denied. Required roles: {', '.join(roles)}",
            )
        return user
    return _checker


def decode_token_for_download(token: str) -> dict:
    """Validate a token passed via query string (for downloads)."""
    if not token:
        raise HTTPException(status_code=401, detail="Missing token")
    try:
        payload = decode_token(token)
        username = payload.get("sub")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid token")
        user = db.get_user(username)
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")


# ------------------------------------------------------------
# LAST LOGIN TRACKING
# ------------------------------------------------------------
def mark_login(username: str):
    """Update the last_login timestamp for a user."""
    try:
        db.update_last_login(username)
    except Exception:
        pass