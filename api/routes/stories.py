"""
GovPulse API — Stories endpoints
Reads from SQLite. Ministry-scoped for ministry users.
"""

import os
import sys
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel


# Make sure src/ is on the path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src import db
from api.auth import get_current_user


router = APIRouter(prefix="/stories", tags=["stories"])


# ------------------------------------------------------------
# MODELS
# ------------------------------------------------------------
class StoryEditRequest(BaseModel):
    headline: str
    new_headline: Optional[str] = None
    ai_summary: Optional[str] = None
    sentiment: Optional[str] = None
    oma: Optional[List[str]] = None
    government_source: Optional[str] = None


# ------------------------------------------------------------
# LIST
# ------------------------------------------------------------
@router.get("")
def list_stories(
    sentiment: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    user: dict = Depends(get_current_user),
):
    """
    Return stories.
    - Admin/Analyst/Oversight: all stories
    - Ministry: only their own ministry's stories
    """
    role = user.get("role")
    print(f"[DEBUG] list_stories: user={user.get('username')} role={role!r} ministry={user.get('ministry')!r}")

    if role == "ministry":
        ministry = user.get("ministry")
        if not ministry:
            return {"count": 0, "stories": []}
        stories = db.get_stories(sentiment=sentiment, source=source, ministry=ministry)
    else:
        stories = db.get_stories(sentiment=sentiment, source=source)

    print(f"[DEBUG] returning {len(stories)} stories for {user.get('username')}")

    # Sort: negative first
    order = {"Negative": 0, "Neutral": 1, "Positive": 2}
    stories.sort(key=lambda s: (order.get(s.get("sentiment"), 3), s.get("headline", "")))

    return {"count": len(stories), "stories": stories}


# ------------------------------------------------------------
# GET ONE
# ------------------------------------------------------------
@router.get("/{headline}")
def get_story(headline: str, user: dict = Depends(get_current_user)):
    story = db.get_story(headline)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    # Ministry users can only see their own
    if user.get("role") == "ministry":
        ministry = user.get("ministry")
        if ministry not in (story.get("oma") or []):
            raise HTTPException(status_code=403, detail="Not your ministry's story")

    return story


# ------------------------------------------------------------
# EDIT
# ------------------------------------------------------------
@router.put("/edit")
def edit_story(
    req: StoryEditRequest,
    user: dict = Depends(get_current_user),
):
    """
    Update a story's editable fields.
    Admin/Analyst: full edit
    Ministry: only their own stories
    """
    story = db.get_story(req.headline)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    role = user.get("role")
    if role == "ministry":
        ministry = user.get("ministry")
        if ministry not in (story.get("oma") or []):
            raise HTTPException(status_code=403, detail="Not your ministry's story")

    if role not in ("admin", "analyst", "ministry"):
        raise HTTPException(status_code=403, detail="Not allowed to edit")

    # Build update dict
    updates = {}

    if req.new_headline is not None and req.new_headline.strip():
        updates["headline"] = req.new_headline.strip()

    if req.ai_summary is not None:
        updates["ai_summary"] = req.ai_summary

    if req.sentiment is not None:
        if req.sentiment not in ("Positive", "Neutral", "Negative"):
            raise HTTPException(status_code=400, detail="Invalid sentiment")
        updates["sentiment"] = req.sentiment

    if req.oma is not None:
        clean = [x.strip() for x in req.oma if x.strip()]
        updates["oma"] = clean or ["Unmapped"]

    if req.government_source is not None:
        updates["government_source"] = req.government_source

    if not updates:
        return {"status": "no_changes", "story": story}

    # Handle headline change
    if "headline" in updates and updates["headline"] != req.headline:
        story_copy = dict(story)
        story_copy["headline"] = updates["headline"]
        for k, v in updates.items():
            story_copy[k] = v
        db.delete_story(req.headline)
        db.upsert_story(story_copy)
        updated = db.get_story(updates["headline"])
    else:
        db.update_story_fields(req.headline, updates)
        updated = db.get_story(req.headline)

    # Audit
    try:
        db.log_audit(
            action="edited",
            user=user.get("username", "unknown"),
            target=req.headline,
            details={
                "sentiment": updated.get("sentiment"),
                "oma": updated.get("oma"),
            },
        )
    except Exception:
        pass

    # Export DB to JSON so report.py still works
    try:
        from src.db_import import export_all
        export_all()
    except Exception:
        pass

    return {"status": "ok", "story": updated}