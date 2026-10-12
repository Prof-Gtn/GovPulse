"""
GovPulse API — Admin endpoints
User management for MICT admins.
"""

import os
import sys
import bcrypt
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src import db
from api.auth import require_admin


router = APIRouter(prefix="/admin", tags=["admin"])


# ------------------------------------------------------------
# MODELS
# ------------------------------------------------------------
class CreateUserRequest(BaseModel):
    username: str
    email: str
    name: str
    password: str
    role: str
    ministry: Optional[str] = None


class UpdateUserRequest(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    ministry: Optional[str] = None
    password: Optional[str] = None


# ------------------------------------------------------------
# LIST USERS
# ------------------------------------------------------------
@router.get("/users")
def list_users(admin: dict = Depends(require_admin)):
    """Return all users. Passwords are never returned."""
    users = db.get_all_users()
    for u in users:
        u.pop("password_hash", None)
    return {"count": len(users), "users": users}


# ------------------------------------------------------------
# CREATE USER
# ------------------------------------------------------------
@router.post("/users")
def create_user(req: CreateUserRequest, admin: dict = Depends(require_admin)):
    """Create a new user."""
    # Validate role
    if req.role not in ("admin", "analyst", "ministry", "oversight"):
        raise HTTPException(status_code=400, detail="Invalid role")

    # Ministry users must have a ministry
    if req.role == "ministry" and not req.ministry:
        raise HTTPException(
            status_code=400,
            detail="Ministry role requires a ministry assignment",
        )

    # Check for existing username
    existing = db.get_user(req.username)
    if existing:
        raise HTTPException(status_code=409, detail="Username already exists")

    # Hash password
    try:
        password_hash = bcrypt.hashpw(
            req.password.encode("utf-8")[:72],
            bcrypt.gensalt(),
        ).decode("utf-8")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Password hashing failed: {e}")

    # Create
    db.create_user(
        username=req.username,
        email=req.email,
        name=req.name,
        password_hash=password_hash,
        role=req.role,
        ministry=req.ministry,
    )

    # Audit
    db.log_audit(
        action="user_created",
        user=admin.get("username", "unknown"),
        target=req.username,
        details={"role": req.role, "ministry": req.ministry or ""},
    )

    return {"status": "ok", "username": req.username}


# ------------------------------------------------------------
# UPDATE USER
# ------------------------------------------------------------
@router.put("/users/{username}")
def update_user(
    username: str,
    req: UpdateUserRequest,
    admin: dict = Depends(require_admin),
):
    """Update a user's fields."""
    user = db.get_user(username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    updates = {}
    if req.name is not None:
        updates["name"] = req.name
    if req.email is not None:
        updates["email"] = req.email
    if req.role is not None:
        if req.role not in ("admin", "analyst", "ministry", "oversight"):
            raise HTTPException(status_code=400, detail="Invalid role")
        updates["role"] = req.role
    if req.ministry is not None:
        updates["ministry"] = req.ministry

    if req.password:
        try:
            updates["password_hash"] = bcrypt.hashpw(
                req.password.encode("utf-8")[:72],
                bcrypt.gensalt(),
            ).decode("utf-8")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Hashing failed: {e}")

    if not updates:
        return {"status": "no_changes"}

    # Update via direct SQL
    keys = list(updates.keys())
    values = [updates[k] for k in keys]
    set_clause = ", ".join(f"{k} = ?" for k in keys)
    values.append(username)

    with db.get_db() as conn:
        conn.execute(f"UPDATE users SET {set_clause} WHERE username = ?", values)

    # Audit
    db.log_audit(
        action="user_updated",
        user=admin.get("username", "unknown"),
        target=username,
        details={k: v for k, v in updates.items() if k != "password_hash"},
    )

    return {"status": "ok"}


# ------------------------------------------------------------
# DELETE USER
# ------------------------------------------------------------
@router.delete("/users/{username}")
def delete_user(username: str, admin: dict = Depends(require_admin)):
    """Delete a user."""
    if username == admin.get("username"):
        raise HTTPException(status_code=400, detail="Cannot delete yourself")

    user = db.get_user(username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    db.delete_user(username)

    # Audit
    db.log_audit(
        action="user_deleted",
        user=admin.get("username", "unknown"),
        target=username,
        details={"role": user.get("role")},
    )

    return {"status": "ok"}


# ------------------------------------------------------------
# SYSTEM STATS
# ------------------------------------------------------------
@router.get("/stats")
def stats(admin: dict = Depends(require_admin)):
    """Return system-wide stats."""
    stories = db.get_stories()
    responses = db.get_all_responses()
    approvals = db.get_all_approvals()
    users = db.get_all_users()
    audit = db.get_audit_entries(limit=10000)

    db_path = db.DB_PATH
    db_size = os.path.getsize(db_path) if os.path.exists(db_path) else 0

    # Count by role
    roles = {}
    for u in users:
        roles[u["role"]] = roles.get(u["role"], 0) + 1

    return {
        "users": len(users),
        "roles": roles,
        "stories": len(stories),
        "responses": len(responses),
        "approvals": len(approvals),
        "audit_events": len(audit),
        "db_size_kb": round(db_size / 1024, 1),
    }