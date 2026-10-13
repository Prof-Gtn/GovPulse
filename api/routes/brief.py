"""
GovPulse API — Daily Brief endpoints
"""

import os
import sys
import subprocess
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from api.config import XLSX_FILE, PDF_FILE
from api.auth import get_current_user, decode_token_for_download, require_admin_or_analyst
from src import db

router = APIRouter(prefix="/brief", tags=["brief"])


@router.get("/pdf")
def download_pdf(token: Optional[str] = Query(None)):
    """Download the current PDF brief."""
    decode_token_for_download(token)
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
    decode_token_for_download(token)
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
def regenerate_brief(user: dict = Depends(require_admin_or_analyst)):
    """Regenerate the brief from the existing data."""
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

@router.post("/regenerate")
def regenerate_brief(user: dict = Depends(require_admin_or_analyst)):
    """
    Regenerate the daily brief from existing processed data.
    Does NOT re-scrape or re-analyze — just rebuilds the Excel + PDF.
    """
    import subprocess
    import sys

    report_script = os.path.join(PROJECT_ROOT, "src", "report.py")
    if not os.path.exists(report_script):
        raise HTTPException(status_code=500, detail="report.py not found")

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
        raise HTTPException(
            status_code=500,
            detail=f"Report generation failed: {r.stderr[-400:]}",
        )

    # Audit
    try:
        db.log_audit(
            action="brief_regenerated",
            user=user.get("username", "unknown"),
            target="daily_brief",
            details={"source": "regenerate_button"},
        )
    except Exception:
        pass

    return {
        "status": "ok",
        "message": "Brief regenerated from existing data",
        "stdout": r.stdout[-500:],
    }