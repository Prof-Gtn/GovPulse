"""
GovPulse API — Authentication
JWT-based login using the same users from app/config.yaml
"""

import os
import yaml
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError

from api.config import CONFIG_YAML, JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRE_HOURS


# Bearer token extraction
security = HTTPBearer()


def load_users():
    """Load users from app/config.yaml."""
    with open(CONFIG_YAML, encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return config["credentials"]["usernames"]


def verify_password(plain: str, hashed: str) -> bool:
    """Check password against stored hash using bcrypt directly."""
    try:
        plain_bytes = plain.encode("utf-8")[:72]
        hashed_bytes = hashed.encode("utf-8")
        return bcrypt.checkpw(plain_bytes, hashed_bytes)
    except Exception as e:
        print(f"[AUTH] bcrypt error: {e}")
        return False


def authenticate_user(username: str, password: str) -> Optional[dict]:
    """Return the user dict if credentials are correct, else None."""
    users = load_users()
    user = users.get(username)
    if not user:
        return None
    if not verify_password(password, user["password"]):
        return None
    return user


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


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """Extract and validate the current user from the Authorization header."""
    payload = decode_token(credentials.credentials)
    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token")

    users = load_users()
    user = users.get(username)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return {"username": username, **user}


def require_admin(user: dict = Depends(get_current_user)) -> dict:
    """Ensure the current user is an admin."""
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user