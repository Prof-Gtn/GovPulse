"""
GovPulse API — Stories endpoints
"""

import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query


from api.config import MAPPED_FILE
from api.auth import get_current_user


router = APIRouter(prefix="/stories", tags=["stories"])


def _load_stories() -> List[dict]:
    with open(MAPPED_FILE, "r", encoding="utf-8-sig") as f:
        return json.load(f)


@router.get("")
def list_stories(
    sentiment: Optional[str] = Query(None, description="Filter by sentiment"),
    source: Optional[str] = Query(None, description="Filter by source"),
    user: dict = Depends(get_current_user),
):
    """Return all stories, optionally filtered."""
    stories = _load_stories()

    # Ministry-scoped users see only their ministry's stories
    if user.get("role") == "ministry":
        ministry = user.get("ministry", "")
        stories = [
            s for s in stories
            if ministry in (s.get("oma") or [])
        ]

    if sentiment:
        stories = [s for s in stories if s.get("sentiment") == sentiment]
    if source:
        stories = [s for s in stories if s.get("source") == source]

    # Sort: negative first
    stories = sorted(stories, key=lambda s: (
        0 if s.get("sentiment") == "Negative" else
        1 if s.get("sentiment") == "Neutral" else 2
    ))

    return {"count": len(stories), "stories": stories}


@router.get("/{headline}")
def get_story(headline: str, user: dict = Depends(get_current_user)):
    """Return one story by headline (URL-encoded)."""
    stories = _load_stories()
    for s in stories:
        if s.get("headline") == headline:
            return s
    return {"error": "Story not found"}, 404

from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class StoryEditRequest(BaseModel):
    headline: str            # the original headline (used as the key)
    new_headline: Optional[str] = None
    ai_summary: Optional[str] = None
    sentiment: Optional[str] = None
    oma: Optional[List[str]] = None
    government_source: Optional[str] = None


@router.put("/edit")
def edit_story(req: StoryEditRequest, user: dict = Depends(get_current_user)):
    """Edit a story's fields. Returns the updated story."""
    with open(MAPPED_FILE, "r", encoding="utf-8-sig") as f:
        stories = json.load(f)

    target = None
    for s in stories:
        if s.get("headline") == req.headline:
            target = s
            break

    if not target:
        raise HTTPException(status_code=404, detail="Story not found")

    if req.new_headline is not None:
        target["headline"] = req.new_headline
    if req.ai_summary is not None:
        target["ai_summary"] = req.ai_summary
    if req.sentiment is not None:
        if req.sentiment not in ("Positive", "Neutral", "Negative"):
            raise HTTPException(status_code=400, detail="Invalid sentiment")
        target["sentiment"] = req.sentiment
    if req.oma is not None:
        target["oma"] = [x.strip() for x in req.oma if x.strip()] or ["Unmapped"]
    if req.government_source is not None:
        target["government_source"] = req.government_source

    with open(MAPPED_FILE, "w", encoding="utf-8-sig") as f:
        json.dump(stories, f, indent=2, ensure_ascii=False)

    return {"status": "ok", "story": target}