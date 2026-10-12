"""
GovPulse API — FastAPI application entry point
"""

import os
import sys
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


from api.config import ALLOWED_ORIGINS
from api.auth import (
    authenticate_user,
    create_access_token,
    get_current_user,
    mark_login,
)
from api.models import LoginRequest, LoginResponse
from api.routes import stories, brief, responses, pipeline, response_generate
from src import db


app = FastAPI(
    title="GovPulse API",
    description="Government Media Intelligence Platform — API",
    version="1.0.0",
)


# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ------------------------------------------------------------
# ROOT
# ------------------------------------------------------------
@app.get("/")
def root():
    return {
        "app": "GovPulse API",
        "version": "1.0.0",
        "status": "running",
    }


@app.get("/health")
def health():
    return {"status": "ok"}


# ------------------------------------------------------------
# AUTH
# ------------------------------------------------------------
@app.post("/auth/login", response_model=LoginResponse)
def login(req: LoginRequest):
    """Login and receive a JWT token."""
    user = authenticate_user(req.username, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(req.username)

    # Mark login + audit
    try:
        mark_login(req.username)
        db.log_audit(
            action="logged_in",
            user=req.username,
            target="system",
            details={"role": user.get("role")},
        )
    except Exception:
        pass

    return LoginResponse(
        access_token=token,
        name=user.get("name", req.username),
        role=user.get("role", "viewer"),
        ministry=user.get("ministry"),
    )


@app.get("/auth/me")
def me(user: dict = Depends(get_current_user)):
    """Return the current user's info."""
    return {
        "username": user.get("username"),
        "name": user.get("name"),
        "role": user.get("role"),
        "ministry": user.get("ministry"),
    }


# ------------------------------------------------------------
# AUDIT
# ------------------------------------------------------------
@app.get("/audit")
def list_audit(limit: int = 200, user: dict = Depends(get_current_user)):
    """Return recent audit entries."""
    if user.get("role") not in ("admin", "analyst", "oversight"):
        raise HTTPException(status_code=403, detail="Not allowed")
    entries = db.get_audit_entries(limit=limit)
    return {"count": len(entries), "entries": entries}


# ------------------------------------------------------------
# MINISTRY VIEW
# ------------------------------------------------------------
@app.get("/ministry/summary")
def ministry_summary(user: dict = Depends(get_current_user)):
    """Summary metrics for the current user's ministry."""
    if user.get("role") != "ministry":
        raise HTTPException(status_code=403, detail="Ministry users only")

    ministry = user.get("ministry")
    if not ministry:
        raise HTTPException(status_code=400, detail="No ministry assigned")

    stories = db.get_stories(ministry=ministry)
    approvals = [
        a for a in db.get_all_approvals()
        if a.get("ministry") == ministry
    ]
    responses = [
        r for r in db.get_all_responses()
        if r.get("ministry") == ministry
    ]

    counts = {"Positive": 0, "Neutral": 0, "Negative": 0}
    for s in stories:
        counts[s.get("sentiment")] = counts.get(s.get("sentiment"), 0) + 1

    return {
        "ministry": ministry,
        "total_stories": len(stories),
        "sentiment": counts,
        "approvals": len(approvals),
        "responses": len(responses),
    }


# ------------------------------------------------------------
# ROUTERS
# ------------------------------------------------------------
app.include_router(stories.router)
app.include_router(brief.router)
app.include_router(responses.router)
app.include_router(pipeline.router)
app.include_router(response_generate.router)