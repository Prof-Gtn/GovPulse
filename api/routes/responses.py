"""
GovPulse API — Response Drafts endpoints
"""

import json
import os
from fastapi import APIRouter, Depends, HTTPException

from api.config import RESPONSES_FILE, APPROVALS_FILE
from api.auth import get_current_user, require_admin
from api.models import ApproveRequest


router = APIRouter(prefix="/responses", tags=["responses"])


def _load_responses() -> list:
    if not os.path.exists(RESPONSES_FILE):
        return []
    with open(RESPONSES_FILE, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def _load_approvals() -> dict:
    if not os.path.exists(APPROVALS_FILE):
        return {}
    with open(APPROVALS_FILE, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def _save_approvals(data: dict):
    os.makedirs(os.path.dirname(APPROVALS_FILE), exist_ok=True)
    with open(APPROVALS_FILE, "w", encoding="utf-8-sig") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


@router.get("")
def list_responses(user: dict = Depends(get_current_user)):
    """Return all response drafts."""
    return {"responses": _load_responses()}


@router.get("/approvals")
def list_approvals(user: dict = Depends(get_current_user)):
    """Return the current approvals."""
    return _load_approvals()


@router.post("/approve")
def approve_response(
    req: ApproveRequest,
    admin: dict = Depends(require_admin),
):
    """Approve a response draft. Only admins can approve."""
    from datetime import datetime
    import subprocess
    import sys
    from api.config import PROJECT_ROOT

    approvals = _load_approvals()
    approvals[req.headline] = {
        "approved_at": datetime.now().isoformat(),
        "ministry": req.ministry,
        "final_text": req.final_text,
        "approved_by": admin.get("username"),
    }
    _save_approvals(approvals)

    # Only regenerate the report — not the whole pipeline
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
        # Report regeneration timed out — but approval is saved
        return {
            "status": "approved",
            "headline": req.headline,
            "warning": "Brief regeneration timed out",
        }

    return {"status": "approved", "headline": req.headline}
    """Approve a response draft. Only admins can approve."""
    from datetime import datetime

    approvals = _load_approvals()
    approvals[req.headline] = {
        "approved_at": datetime.now().isoformat(),
        "ministry": req.ministry,
        "final_text": req.final_text,
        "approved_by": admin.get("username"),
    }
    _save_approvals(approvals)

    # Regenerate the brief
    import subprocess
    import sys
    from api.config import PROJECT_ROOT
    subprocess.run(
        [sys.executable, os.path.join(PROJECT_ROOT, "src", "report.py")],
        capture_output=True,
        cwd=PROJECT_ROOT,
    )

    return {"status": "approved", "headline": req.headline}