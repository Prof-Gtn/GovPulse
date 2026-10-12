"""
GovPulse — Export DB to JSON
Keeps JSON files in sync with the database so report.py continues to work.
"""

import json
import os
import sys


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src import db


MAPPED_JSON    = os.path.join(PROJECT_ROOT, "data", "processed", "mapped.json")
RESPONSES_JSON = os.path.join(PROJECT_ROOT, "data", "processed", "responses.json")
APPROVALS_JSON = os.path.join(PROJECT_ROOT, "data", "processed", "approvals.json")


def _write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8-sig") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def export_stories():
    stories = db.get_stories()
    _write_json(MAPPED_JSON, stories)
    return len(stories)


def export_responses():
    responses = db.get_all_responses()
    formatted = []
    for r in responses:
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
    _write_json(RESPONSES_JSON, formatted)
    return len(formatted)


def export_approvals():
    approvals = db.get_approvals_as_dict()
    _write_json(APPROVALS_JSON, approvals)
    return len(approvals)


def export_all():
    n_s = export_stories()
    n_r = export_responses()
    n_a = export_approvals()
    print(f"[EXPORT] Stories: {n_s}, Responses: {n_r}, Approvals: {n_a}")


if __name__ == "__main__":
    export_all()