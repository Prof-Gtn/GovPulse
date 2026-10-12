"""
GovPulse API — Pipeline trigger endpoints
"""

import os
import sys
import subprocess
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src import db
from api.auth import require_admin_or_analyst


router = APIRouter(prefix="/pipeline", tags=["pipeline"])


STAGES = [
    {"id": "scraper",       "label": "Scraping news sources",  "script": "src/scraper.py",        "timeout": 600},
    {"id": "analyzer",      "label": "Analyzing stories",      "script": "src/analyzer.py",       "timeout": 600},
    {"id": "mapper",        "label": "Mapping to government",  "script": "src/mapper.py",         "timeout": 300},
    {"id": "report",        "label": "Generating daily brief", "script": "src/report.py",         "timeout": 300},
    {"id": "response_desk", "label": "Drafting responses",     "script": "src/response_desk.py",  "timeout": 600},
]


@router.get("/stages")
def list_stages(user: dict = Depends(require_admin_or_analyst)):
    return {
        "stages": [{"id": s["id"], "label": s["label"]} for s in STAGES]
    }


class StageRequest(BaseModel):
    stage_id: str


@router.post("/run-step")
def run_step(req: StageRequest, user: dict = Depends(require_admin_or_analyst)):
    """Run a single pipeline stage."""
    stage = next((s for s in STAGES if s["id"] == req.stage_id), None)
    if not stage:
        raise HTTPException(status_code=400, detail=f"Unknown stage: {req.stage_id}")

    script_path = os.path.join(PROJECT_ROOT, stage["script"])
    if not os.path.exists(script_path):
        raise HTTPException(status_code=500, detail=f"Script not found: {stage['script']}")

    try:
        r = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=PROJECT_ROOT,
            timeout=stage["timeout"],
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=504,
            detail=f"Stage '{stage['label']}' timed out after {stage['timeout']}s",
        )

    if r.returncode != 0:
        raise HTTPException(
            status_code=500,
            detail=f"Stage '{stage['label']}' failed: {r.stderr[-400:]}",
        )

    # Audit
    try:
        db.log_audit(
            action="pipeline_stage",
            user=user.get("username", "unknown"),
            target=stage["id"],
            details={"label": stage["label"]},
        )
    except Exception:
        pass

    # Import DB back to JSON after pipeline (scraper updates JSON, we re-migrate)
    try:
        from src.migrate import migrate_stories, migrate_responses
        # Actually — the pipeline writes to JSON. We need to re-import from JSON to DB.
        # For now, sync stories from JSON into DB:
        from src.db_import import import_from_json
        import_from_json()
    except Exception as e:
        print(f"[PIPELINE] DB sync failed: {e}")

    return {
        "stage_id": stage["id"],
        "label": stage["label"],
        "status": "ok",
    }