"""
GovPulse API — On-demand response draft generation
"""

import json
import os
import subprocess
import sys
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.config import MAPPED_FILE, RESPONSES_FILE, PROJECT_ROOT
from api.auth import get_current_user


router = APIRouter(prefix="/responses", tags=["responses"])


class GenerateRequest(BaseModel):
    headline: str


@router.post("/generate")
def generate_draft(req: GenerateRequest, user: dict = Depends(get_current_user)):
    """Generate a fresh response draft for one story."""

    # Find the story
    with open(MAPPED_FILE, "r", encoding="utf-8-sig") as f:
        stories = json.load(f)

    story = next((s for s in stories if s.get("headline") == req.headline), None)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    # Import the response_desk draft logic
    sys.path.insert(0, PROJECT_ROOT)
    from src.response_desk import draft_response

    result = draft_response(story)

    # Merge into responses.json
    responses = []
    if os.path.exists(RESPONSES_FILE):
        try:
            with open(RESPONSES_FILE, "r", encoding="utf-8-sig") as f:
                responses = json.load(f)
        except Exception:
            responses = []

    # Replace any existing entry for this headline
    responses = [r for r in responses if r.get("headline") != req.headline]
    responses.append({
        "headline": story["headline"],
        "oma": story.get("oma", []),
        "sentiment": story.get("sentiment", "Neutral"),
        "response": result,
    })

    with open(RESPONSES_FILE, "w", encoding="utf-8-sig") as f:
        json.dump(responses, f, indent=2, ensure_ascii=False)

    return result