"""
GovPulse API — Daily Brief endpoints
"""

import os
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse

from api.config import XLSX_FILE, PDF_FILE
from api.auth import get_current_user, decode_token, load_users


router = APIRouter(prefix="/brief", tags=["brief"])


def _get_user_from_query_or_header(token: Optional[str] = None):
    """Accept a token from the query string (for browser downloads)."""
    if not token:
        raise HTTPException(status_code=401, detail="Missing token")
    try:
        payload = decode_token(token)
        username = payload.get("sub")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid token")
        users = load_users()
        user = users.get(username)
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return {"username": username, **user}
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")


@router.get("/pdf")
def download_pdf(token: Optional[str] = Query(None)):
    """Download the current PDF brief."""
    _get_user_from_query_or_header(token)
    if not os.path.exists(PDF_FILE):
        raise HTTPException(status_code=404, detail="PDF not generated yet.")
    return FileResponse(
        PDF_FILE,
        media_type="application/pdf",
        filename="daily_brief.pdf",
    )


@router.get("/xlsx")
def download_xlsx(token: Optional[str] = Query(None)):
    """Download the current Excel brief."""
    _get_user_from_query_or_header(token)
    if not os.path.exists(XLSX_FILE):
        raise HTTPException(status_code=404, detail="Excel not generated yet.")
    return FileResponse(
        XLSX_FILE,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename="daily_brief.xlsx",
    )


@router.get("/exists")
def brief_exists(user: dict = Depends(get_current_user)):
    """Check if the brief files exist."""
    return {
        "pdf": os.path.exists(PDF_FILE),
        "xlsx": os.path.exists(XLSX_FILE),
    }

@router.post("/regenerate")
def regenerate_brief(user: dict = Depends(get_current_user)):
    """Regenerate the brief from the existing analyzed data."""
    import subprocess
    import sys
    from api.config import PROJECT_ROOT

    report_script = os.path.join(PROJECT_ROOT, "src", "report.py")
    try:
        r = subprocess.run(
            [sys.executable, report_script],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=PROJECT_ROOT,
            timeout=60,
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Brief regeneration timed out")

    if r.returncode != 0:
        raise HTTPException(status_code=500, detail=f"Report failed: {r.stderr[-300:]}")

    return {"status": "ok"}