"""
GovPulse API — Pipeline trigger endpoints
"""

import os
import subprocess
import sys
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.config import PROJECT_ROOT
from api.auth import require_admin


router = APIRouter(prefix="/pipeline", tags=["pipeline"])


STAGES = [
    {"id": "scraper",       "label": "Scraping news sources",  "script": "src/scraper.py",        "timeout": 600},
    {"id": "analyzer",      "label": "Analyzing stories",      "script": "src/analyzer.py",       "timeout": 600},
    {"id": "mapper",        "label": "Mapping to government",  "script": "src/mapper.py",         "timeout": 300},
    {"id": "report",        "label": "Generating daily brief", "script": "src/report.py",         "timeout": 300},
    {"id": "response_desk", "label": "Drafting responses",     "script": "src/response_desk.py",  "timeout": 600},
]


@router.get("/stages")
def list_stages(user: dict = Depends(require_admin)):
    """Return the list of pipeline stages so the frontend can render them."""
    return {
        "stages": [
            {"id": s["id"], "label": s["label"]}
            for s in STAGES
        ]
    }


class StageRequest(BaseModel):
    stage_id: str


@router.post("/run-step")
def run_step(req: StageRequest, admin: dict = Depends(require_admin)):
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

    return {
        "stage_id": stage["id"],
        "label": stage["label"],
        "status": "ok",
    }


@router.post("/run")
def run_all(admin: dict = Depends(require_admin)):
    """Run all stages at once (kept for backwards compatibility)."""
    results = []
    for stage in STAGES:
        script_path = os.path.join(PROJECT_ROOT, stage["script"])
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

        results.append({"id": stage["id"], "status": "ok"})

    return {"status": "complete", "stages": results}