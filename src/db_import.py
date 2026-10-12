"""
GovPulse — Import JSON to DB
Reads the current JSON files (which the pipeline produces) and
syncs them into the SQLite database.
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


def _load_json(path, default=None):
    if not os.path.exists(path):
        return default if default is not None else []
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    except Exception:
        return default if default is not None else []


def import_stories():
    stories = _load_json(MAPPED_JSON, [])
    for s in stories:
        db.upsert_story(s)
    return len(stories)


def import_responses():
    responses = _load_json(RESPONSES_JSON, [])
    count = 0
    for entry in responses:
        headline = entry.get("headline")
        r = entry.get("response", {})
        if not headline:
            continue
        db.upsert_response(
            headline=headline,
            ministry=r.get("ministry", ""),
            draft=r.get("draft", ""),
            status=r.get("status", "failed"),
            precedents=r.get("precedents", []),
            generated_at=r.get("generated_at"),
        )
        count += 1
    return count


def import_approvals():
    approvals = _load_json(APPROVALS_JSON, {})
    # Approvals come from DB already; don't re-import unless JSON has newer
    # For now, skip
    return 0


def import_from_json():
    """Sync everything from JSON to DB."""
    n_s = import_stories()
    n_r = import_responses()
    print(f"[DB-IMPORT] Stories: {n_s}, Responses: {n_r}")


if __name__ == "__main__":
    import_from_json()