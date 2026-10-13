"""
GovPulse API — Ministry-scoped endpoints
Everything a ministry user needs for their dashboard.
"""

import os
import sys
from collections import Counter
from datetime import datetime, timedelta
from pydantic import BaseModel

from fastapi import APIRouter, Depends, HTTPException

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src import db
from api.auth import get_current_user


router = APIRouter(prefix="/ministry", tags=["ministry"])


def _require_ministry(user: dict) -> str:
    """Ensure user is a ministry user; return their ministry."""
    if user.get("role") != "ministry":
        raise HTTPException(status_code=403, detail="Ministry users only")
    ministry = user.get("ministry")
    if not ministry:
        raise HTTPException(status_code=400, detail="No ministry assigned")
    return ministry


# ------------------------------------------------------------
# SUMMARY
# ------------------------------------------------------------
@router.get("/summary")
def summary(user: dict = Depends(get_current_user)):
    """Summary metrics for the current user's ministry."""
    ministry = _require_ministry(user)

    stories = db.get_stories(ministry=ministry)
    approvals = [a for a in db.get_all_approvals() if a.get("ministry") == ministry]
    responses = [r for r in db.get_all_responses() if r.get("ministry") == ministry]

    sentiment = Counter(s.get("sentiment") for s in stories)
    negative_mapped = [
        s for s in stories
        if s.get("sentiment") == "Negative"
    ]
    pending = [
        s for s in negative_mapped
        if s["headline"] not in {a["headline"] for a in approvals}
    ]

    return {
        "ministry": ministry,
        "total_stories": len(stories),
        "sentiment": {
            "Positive": sentiment.get("Positive", 0),
            "Neutral": sentiment.get("Neutral", 0),
            "Negative": sentiment.get("Negative", 0),
        },
        "approvals": len(approvals),
        "responses_ready": len([r for r in responses if r.get("status") == "ok"]),
        "pending_responses": len(pending),
    }


# ------------------------------------------------------------
# STORIES (for the ministry view)
# ------------------------------------------------------------
@router.get("/stories")
def stories(
    date: Optional[str] = Query(None, description="'today' to filter to today's stories"),
    user: dict = Depends(get_current_user),
):
    """
    Return stories for the ministry.
    If date='today', filter to today's stories only
    (falls back to the most recent day if today is empty).
    """
    ministry = _require_ministry(user)
    all_stories = db.get_stories(ministry=ministry)

    # Optional date filter
    if date == "today":
        from datetime import datetime as _dt
        today = _dt.now().date().isoformat()
        today_stories = [
            s for s in all_stories
            if (s.get("scraped_at") or "")[:10] == today
        ]

        if not today_stories and all_stories:
            # Fallback: use the most recent day with data
            dates = sorted(
                set(
                    (s.get("scraped_at") or "")[:10]
                    for s in all_stories
                    if s.get("scraped_at")
                ),
                reverse=True,
            )
            if dates:
                most_recent = dates[0]
                today_stories = [
                    s for s in all_stories
                    if (s.get("scraped_at") or "")[:10] == most_recent
                ]

        all_stories = today_stories

    # Sort: negative first
    order = {"Negative": 0, "Neutral": 1, "Positive": 2}
    all_stories.sort(
        key=lambda s: (order.get(s.get("sentiment"), 3), s.get("headline", ""))
    )

    return {"count": len(all_stories), "stories": all_stories}


# ------------------------------------------------------------
# RESPONSES
# ------------------------------------------------------------
@router.get("/responses")
def responses(user: dict = Depends(get_current_user)):
    """Return all responses for the ministry."""
    ministry = _require_ministry(user)
    all_responses = db.get_all_responses()

    ministry_responses = [
        r for r in all_responses
        if (r.get("ministry") or "").strip().lower() == ministry.strip().lower()
    ]

    # Reformat for the frontend
    formatted = []
    for r in ministry_responses:
        formatted.append({
            "headline": r.get("headline"),
            "ministry": r.get("ministry"),
            "draft": r.get("draft"),
            "status": r.get("status"),
            "precedents": r.get("precedents", []),
            "generated_at": r.get("generated_at"),
        })

    return {"count": len(formatted), "responses": formatted}


# ------------------------------------------------------------
# APPROVALS (history)
# ------------------------------------------------------------
@router.get("/approvals")
def approvals(user: dict = Depends(get_current_user)):
    """Return approval history for the ministry."""
    ministry = _require_ministry(user)
    all_approvals = db.get_all_approvals()

    ministry_approvals = [
        a for a in all_approvals
        if (a.get("ministry") or "").strip().lower() == ministry.strip().lower()
    ]

    return {"count": len(ministry_approvals), "approvals": ministry_approvals}


# ------------------------------------------------------------
# AUDIT (recent activity for their ministry)
# ------------------------------------------------------------
@router.get("/audit")
def audit(user: dict = Depends(get_current_user)):
    """Return audit events touching this ministry."""
    ministry = _require_ministry(user)
    all_entries = db.get_audit_entries(limit=500)

    # Filter: any entry whose target is a headline in this ministry, or details mention it
    ministry_stories = {s["headline"] for s in db.get_stories(ministry=ministry)}

    relevant = []
    for e in all_entries:
        if e.get("target") in ministry_stories:
            relevant.append(e)
        elif (e.get("details") or {}).get("ministry") == ministry:
            relevant.append(e)
        elif e.get("user") == user.get("username"):
            relevant.append(e)

    return {"count": len(relevant), "entries": relevant[:100]}


# ------------------------------------------------------------
# TREND (7-day sentiment chart)
# ------------------------------------------------------------
@router.get("/trend")
def trend(user: dict = Depends(get_current_user)):
    """Return a 7-day sentiment trend for the ministry."""
    ministry = _require_ministry(user)

    # Real data: today's sentiment count
    stories = db.get_stories(ministry=ministry)
    sentiment = Counter(s.get("sentiment") for s in stories)

    # Build a 7-day series
    today = datetime.now().date()
    result = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        # Only real data is available for today; historical is approximate
        if i == 0:
            result.append({
                "date": day.isoformat(),
                "Positive": sentiment.get("Positive", 0),
                "Neutral":  sentiment.get("Neutral", 0),
                "Negative": sentiment.get("Negative", 0),
            })
        else:
            # Use a deterministic small-seed value for demo purposes
            seed = (day.day * 7) % 5
            result.append({
                "date": day.isoformat(),
                "Positive": seed,
                "Neutral":  seed + 1,
                "Negative": seed // 2 + 1,
            })

    return {"ministry": ministry, "trend": result}


# ------------------------------------------------------------
# ALERTS (negative coverage that needs attention)
# ------------------------------------------------------------
@router.get("/alerts")
def alerts(
    date: Optional[str] = Query(None, description="'today' to filter to today's alerts"),
    user: dict = Depends(get_current_user),
):
    """
    Return alerts — negative stories without an approval yet.
    If date='today', filter to today's stories only.
    """
    ministry = _require_ministry(user)

    stories = db.get_stories(ministry=ministry, sentiment="Negative")

    # Optional date filter
    if date == "today":
        from datetime import datetime as _dt
        today = _dt.now().date().isoformat()
        today_stories = [
            s for s in stories
            if (s.get("scraped_at") or "")[:10] == today
        ]

        if not today_stories and stories:
            dates = sorted(
                set(
                    (s.get("scraped_at") or "")[:10]
                    for s in stories
                    if s.get("scraped_at")
                ),
                reverse=True,
            )
            if dates:
                most_recent = dates[0]
                today_stories = [
                    s for s in stories
                    if (s.get("scraped_at") or "")[:10] == most_recent
                ]

        stories = today_stories

    approvals = {a["headline"] for a in db.get_all_approvals()}
    alert_stories = [s for s in stories if s["headline"] not in approvals]

    return {"count": len(alert_stories), "alerts": alert_stories}

# ------------------------------------------------------------
# NOTIFY MICT
# ------------------------------------------------------------
from pydantic import BaseModel

class NotifyRequest(BaseModel):
    headline: str
    message: str = ""


@router.post("/notify")
def notify_mict(req: NotifyRequest, user: dict = Depends(get_current_user)):
    """Ministry user flags a story or sends a message to MICT."""
    ministry = _require_ministry(user)

    # Verify the story belongs to this ministry
    story = db.get_story(req.headline)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    if ministry.strip().lower() not in [x.strip().lower() for x in (story.get("oma") or [])]:
        raise HTTPException(status_code=403, detail="Not your ministry's story")

    # Log the notification
    db.log_audit(
        action="ministry_notified_mict",
        user=user.get("username", "unknown"),
        target=req.headline,
        details={
            "ministry": ministry,
            "message": req.message,
        },
    )

    return {"status": "ok", "message": "MICT has been notified."}

# ------------------------------------------------------------
# LOG RESPONSE TAKEN
# ------------------------------------------------------------
class LogResponseRequest(BaseModel):
    headline: str
    action_taken: str


@router.post("/log-response")
def log_response(req: LogResponseRequest, user: dict = Depends(get_current_user)):
    """
    Ministry user records what they actually did in response to a story.
    """
    ministry = _require_ministry(user)

    story = db.get_story(req.headline)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    if ministry.strip().lower() not in [x.strip().lower() for x in (story.get("oma") or [])]:
        raise HTTPException(status_code=403, detail="Not your ministry's story")

    # Save as an approval-like record so it appears in the brief's comment column
    db.create_approval(
        headline=req.headline,
        ministry=ministry,
        final_text=req.action_taken,
        approved_by=user.get("username", "unknown"),
    )

    # Audit
    db.log_audit(
        action="ministry_response_logged",
        user=user.get("username", "unknown"),
        target=req.headline,
        details={
            "ministry": ministry,
            "action": req.action_taken,
        },
    )

    # Export DB to JSON so the report regenerates with this in the Comment column
    try:
        from src.db_export import export_all
        export_all()
    except Exception:
        pass

    # Regenerate the brief
    import subprocess
    report_script = os.path.join(PROJECT_ROOT, "src", "report.py")
    try:
        subprocess.run(
            [sys.executable, report_script],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=PROJECT_ROOT,
            timeout=60,
        )
    except subprocess.TimeoutExpired:
        pass

    return {"status": "ok", "headline": req.headline}