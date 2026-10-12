"""
GovPulse API — Response Drafts
Reads from SQLite. Ministry-scoped for ministry users.
"""

import os
import sys
import subprocess
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel


# Make sure src/ is on the path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src import db
from api.auth import get_current_user


router = APIRouter(prefix="/responses", tags=["responses"])


# ------------------------------------------------------------
# MODELS
# ------------------------------------------------------------
class ApproveRequest(BaseModel):
    headline: str
    ministry: str
    final_text: str


# ------------------------------------------------------------
# LIST RESPONSES
# ------------------------------------------------------------
@router.get("")
def list_responses(user: dict = Depends(get_current_user)):
    """Return all response drafts, scoped to the user's role."""
    all_responses = db.get_all_responses()

    if user.get("role") == "ministry":
        target = (user.get("ministry") or "").strip().lower()
        all_responses = [
            r for r in all_responses
            if (r.get("ministry") or "").strip().lower() == target
        ]

    # Reformat for frontend compatibility
    formatted = []
    for r in all_responses:
        formatted.append({
            "headline": r.get("headline"),
            "oma": [r.get("ministry")] if r.get("ministry") else [],
            "sentiment": "Negative",
            "response": {
                "draft": r.get("draft"),
                "status": r.get("status"),
                "ministry": r.get("ministry"),
                "precedents": r.get("precedents", []),
                "precedents_used": [
                    p.get("filename") for p in (r.get("precedents") or [])
                ],
                "generated_at": r.get("generated_at"),
            },
        })

    return {"responses": formatted}


# ------------------------------------------------------------
# LIST APPROVALS
# ------------------------------------------------------------
@router.get("/approvals")
def list_approvals(user: dict = Depends(get_current_user)):
    """Return current approvals, scoped to the user's role."""
    if user.get("role") == "ministry":
        target = (user.get("ministry") or "").strip().lower()
        approvals_list = db.get_all_approvals()
        approvals_list = [
            a for a in approvals_list
            if (a.get("ministry") or "").strip().lower() == target
        ]
        return {a["headline"]: a for a in approvals_list}
    return db.get_approvals_as_dict()


# ------------------------------------------------------------
# APPROVE
# ------------------------------------------------------------
@router.post("/approve")
def approve_response(
    req: ApproveRequest,
    user: dict = Depends(get_current_user),
):
    """
    Approve a response draft.
    - Admin/Analyst: any response
    - Ministry: only their own ministry's responses
    """
    if user.get("role") not in ("admin", "analyst", "ministry"):
        raise HTTPException(status_code=403, detail="Not allowed to approve")

    # Ministry users can only approve for their own ministry
    if user.get("role") == "ministry":
        if req.ministry != user.get("ministry"):
            raise HTTPException(
                status_code=403,
                detail="Cannot approve responses for other ministries",
            )

    # Save the approval
    db.create_approval(
        headline=req.headline,
        ministry=req.ministry,
        final_text=req.final_text,
        approved_by=user.get("username", "unknown"),
    )

    # Audit
    try:
        db.log_audit(
            action="approved",
            user=user.get("username", "unknown"),
            target=req.headline,
            details={"ministry": req.ministry},
        )
    except Exception:
        pass

    # Export DB to JSON and regenerate the brief
    try:
        from src.db_export import export_all
        export_all()
    except Exception:
        pass

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
        return {
            "status": "approved",
            "headline": req.headline,
            "warning": "Brief regeneration timed out",
        }
    except Exception as e:
        # Even if report fails, the approval is saved
        return {
            "status": "approved",
            "headline": req.headline,
            "warning": f"Brief regeneration failed: {e}",
        }

    return {"status": "approved", "headline": req.headline}