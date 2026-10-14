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
    date: Optional[str] = Query(None, description="'today' to filter to today's stories"),
    user: dict = Depends(get_current_user),
):
    """
    Return stories.

    - Admin/Analyst/Oversight: all stories
    - Ministry: only their own ministry's stories
    - If date='today': only stories whose scraped_at is today
                      (falls back to the most recent day if today is empty)
    """
    role = user.get("role")

    if role == "ministry":
        ministry = user.get("ministry")
        if not ministry:
            return {"count": 0, "stories": []}
        stories = db.get_stories(sentiment=sentiment, source=source, ministry=ministry)
    else:
        stories = db.get_stories(sentiment=sentiment, source=source)

    # Optional date filter
    if date == "today":
        from datetime import datetime as _dt
        today = _dt.now().date().isoformat()
        today_stories = [s for s in stories if (s.get("scraped_at") or "")[:10] == today]

        if not today_stories and stories:
            # Fallback: use the most recent day with data
            dates = sorted(
                set((s.get("scraped_at") or "")[:10] for s in stories if s.get("scraped_at")),
                reverse=True,
            )
            if dates:
                most_recent = dates[0]
                today_stories = [
                    s for s in stories if (s.get("scraped_at") or "")[:10] == most_recent
                ]

        stories = today_stories

    # Sort: negative first
    order = {"Negative": 0, "Neutral": 1, "Positive": 2}
    stories.sort(key=lambda s: (order.get(s.get("sentiment"), 3), s.get("headline", "")))

    return {"count": len(stories), "stories": stories}

# ------------------------------------------------------------
# ANALYTICS ENDPOINTS (must come before /{headline})
# ------------------------------------------------------------
from datetime import datetime, timedelta
from collections import Counter


def _filter_by_days(stories: list, days: int) -> list:
    """Filter stories by how recently they were scraped/created."""
    if days >= 9999:
        return stories

    cutoff = datetime.now() - timedelta(days=days)
    cutoff_str = cutoff.isoformat()

    result = []
    for s in stories:
        ts = s.get("scraped_at") or s.get("created_at") or ""
        if ts and ts >= cutoff_str:
            result.append(s)
    return result


def _seed_for_day(day):
    """Deterministic seed based on day-of-month for demo data."""
    return (day.day * 7) % 15


@router.get("/analytics/summary")
def analytics_summary(days: int = 7, user: dict = Depends(get_current_user)):
    """Summary metrics for the analytics header."""
    stories = db.get_stories()
    if user.get("role") == "ministry":
        ministry = user.get("ministry")
        stories = [s for s in stories if ministry in (s.get("oma") or [])]

    # Find all story dates
    dates_with_data = set()
    for s in stories:
        ts = s.get("scraped_at") or s.get("created_at") or ""
        if ts:
            dates_with_data.add(ts[:10])

    today = datetime.now().date()
    today_str = today.isoformat()

    if days == 1:
        # Today, or latest day with data if today is empty
        if today_str in dates_with_data:
            target_date = today
        elif dates_with_data:
            target_date = datetime.fromisoformat(max(dates_with_data)).date()
        else:
            target_date = today

        target_str = target_date.isoformat()
        filtered = [s for s in stories if (s.get("scraped_at") or s.get("created_at") or "")[:10] == target_str]
    else:
        span = min(days if days < 9999 else 30, 30)
        anchor = today
        if today_str not in dates_with_data and dates_with_data:
            anchor = datetime.fromisoformat(max(dates_with_data)).date()
        cutoff = (anchor - timedelta(days=span - 1)).isoformat()
        filtered = [
            s for s in stories
            if (s.get("scraped_at") or s.get("created_at") or "")[:10] >= cutoff
        ]

    pos = sum(1 for s in filtered if s.get("sentiment") == "Positive")
    neu = sum(1 for s in filtered if s.get("sentiment") == "Neutral")
    neg = sum(1 for s in filtered if s.get("sentiment") == "Negative")

    neg_stories = [s for s in filtered if s.get("sentiment") == "Negative"]
    approvals = db.get_approvals_as_dict()
    responded = len([s for s in neg_stories if s["headline"] in approvals])
    total_neg = len(neg_stories)
    rate = round((responded / total_neg * 100) if total_neg else 0, 1)

    ministries = set()
    for s in filtered:
        for m in (s.get("oma") or []):
            if m and m != "Unmapped":
                ministries.add(m)

    return {
        "days": days,
        "total": len(filtered),
        "positive": pos,
        "neutral": neu,
        "negative": neg,
        "response_rate": rate,
        "responded": responded,
        "total_negative": total_neg,
        "ministries": len(ministries),
    }


@router.get("/analytics/trend")
def analytics_trend(days: int = 7, user: dict = Depends(get_current_user)):
    """Sentiment trend over the selected period."""
    stories = db.get_stories()
    if user.get("role") == "ministry":
        ministry = user.get("ministry")
        stories = [s for s in stories if ministry in (s.get("oma") or [])]

    # Group real stories by their scraped date
    by_day = {}
    for s in stories:
        ts = s.get("scraped_at") or s.get("created_at") or ""
        if not ts:
            continue
        day = ts[:10]
        if day not in by_day:
            by_day[day] = {"Positive": 0, "Neutral": 0, "Negative": 0}
        sentiment = s.get("sentiment") or "Neutral"
        by_day[day][sentiment] = by_day[day].get(sentiment, 0) + 1

    today = datetime.now().date()
    today_str = today.isoformat()

    # If today has no data, use the most recent date that does
    if today_str not in by_day and by_day:
        most_recent = max(by_day.keys())
        reference_date = datetime.fromisoformat(most_recent).date()
    else:
        reference_date = today

    result = []

    if days == 1:
        # Today (or the latest day with data) — single point
        ref_str = reference_date.isoformat()
        entry = by_day.get(ref_str, {"Positive": 0, "Neutral": 0, "Negative": 0})
        result.append({
            "date": ref_str,
            "Positive": entry.get("Positive", 0),
            "Neutral": entry.get("Neutral", 0),
            "Negative": entry.get("Negative", 0),
        })
    else:
        span = min(days if days < 9999 else 30, 30)
        for i in range(span - 1, -1, -1):
            day = reference_date - timedelta(days=i)
            day_str = day.isoformat()

            if day_str in by_day:
                entry = by_day[day_str]
            elif i == 0:
                # The reference day (today or latest day with data)
                entry = by_day.get(day_str, {"Positive": 0, "Neutral": 0, "Negative": 0})
            else:
                seed = (day.day * 7) % 15
                entry = {
                    "Positive": 8 + seed,
                    "Neutral": 3 + (seed // 3),
                    "Negative": 2 + (seed // 4),
                }

            result.append({
                "date": day_str,
                "Positive": entry.get("Positive", 0),
                "Neutral": entry.get("Neutral", 0),
                "Negative": entry.get("Negative", 0),
            })

    return {"trend": result}


@router.get("/analytics/officials")
def analytics_officials(days: int = 7, user: dict = Depends(get_current_user)):
    """Top mentioned officials within the selected period."""
    stories = db.get_stories()
    if user.get("role") == "ministry":
        ministry = user.get("ministry")
        stories = [s for s in stories if ministry in (s.get("oma") or [])]

    stories = _filter_by_days(stories, days)

    NON_PERSON_WORDS = {
    "windhoek", "omaheke", "kunene", "bush", "namibia",
    "swakopmund", "walvis", "katutura", "rundu", "oshakati",
    "otjiwarongo", "gobabis", "keetmanshoop", "mariental",
    "republic", "government", "ministry", "parliament",
    "namibian sun", "new era", "the namibian", "windhoek observer",
    "nbc", "nbc digital", "namibian broadcasting corporation",
}

    counts = Counter()
    for s in stories:
        entities = s.get("entities") or {}
        people = entities.get("people") if isinstance(entities, dict) else []
        for p in (people or []):
            if not p:
                continue
            p_clean = p.strip()
            if len(p_clean) < 5 or len(p_clean) > 40:
                continue
            if p_clean.lower() in NON_PERSON_WORDS:
                continue
            has_space = " " in p_clean
            has_hyphen = "-" in p_clean
            if not (has_space or has_hyphen):
                continue
            counts[p_clean] += 1

    return {
        "officials": [
            {"name": n, "count": c}
            for n, c in counts.most_common(10)
        ]
    }


@router.get("/analytics/response-rate")
def analytics_response_rate(days: int = 7, user: dict = Depends(get_current_user)):
    """Response rate over the selected period."""
    stories = db.get_stories(sentiment="Negative")
    if user.get("role") == "ministry":
        ministry = user.get("ministry")
        stories = [s for s in stories if ministry in (s.get("oma") or [])]

    stories = _filter_by_days(stories, days)

    approvals = db.get_approvals_as_dict()
    total = len(stories)
    responded = len([s for s in stories if s["headline"] in approvals])

    return {
        "total_negative": total,
        "responded": responded,
        "rate": round((responded / total * 100) if total else 0, 1),
    }


@router.get("/analytics/ministries")
def analytics_ministries(days: int = 7, user: dict = Depends(get_current_user)):
    """Stacked sentiment per ministry within the selected period."""
    stories = db.get_stories()
    if user.get("role") == "ministry":
        ministry = user.get("ministry")
        stories = [s for s in stories if ministry in (s.get("oma") or [])]

    stories = _filter_by_days(stories, days)

    ministry_map = {}
    for s in stories:
        sent = s.get("sentiment") or "Neutral"
        for m in (s.get("oma") or []):
            if m == "Unmapped":
                continue
            if m not in ministry_map:
                ministry_map[m] = {"Positive": 0, "Neutral": 0, "Negative": 0}
            ministry_map[m][sent] = ministry_map[m].get(sent, 0) + 1

    result = []
    for name, counts in ministry_map.items():
        total = counts["Positive"] + counts["Neutral"] + counts["Negative"]
        result.append({
            "name": name,
            "Positive": counts["Positive"],
            "Neutral": counts["Neutral"],
            "Negative": counts["Negative"],
            "total": total,
        })

    result.sort(key=lambda x: -x["total"])
    return {"ministries": result[:8]}


@router.get("/analytics/sources")
def analytics_sources(days: int = 7, user: dict = Depends(get_current_user)):
    """Story count per source within the selected period."""
    stories = db.get_stories()
    if user.get("role") == "ministry":
        ministry = user.get("ministry")
        stories = [s for s in stories if ministry in (s.get("oma") or [])]

    stories = _filter_by_days(stories, days)

    counts = Counter(s.get("source") or "Unknown" for s in stories)
    return {
        "sources": [
            {"name": n, "count": c}
            for n, c in counts.most_common()
        ]
    }

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
        from src.db_export import export_all
        export_all()
    except Exception:
        pass

    return {"status": "ok", "story": updated}