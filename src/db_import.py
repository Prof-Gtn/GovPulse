"""
GovPulse — Import JSON to DB
Syncs the current pipeline output (mapped.json, responses.json, approvals.json)
into the SQLite database. Removes stories no longer present in the source JSON.
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


def import_stories(replace=True):
    """
    Sync mapped.json into the DB.
    If replace=True, delete any stories in the DB that are not in the JSON.
    """
    stories = _load_json(MAPPED_JSON, [])
    if not stories:
        print("[DB-IMPORT] mapped.json is empty — skipping to avoid wiping the DB")
        return 0

    headlines_in_json = {s.get("headline") for s in stories if s.get("headline")}

    # Upsert everything from JSON
    for s in stories:
        db.upsert_story(s)

    # Remove DB stories that no longer exist in the JSON
    if replace:
        db_stories = db.get_stories()
        removed = 0
        for ds in db_stories:
            if ds.get("headline") not in headlines_in_json:
                db.delete_story(ds["headline"])
                removed += 1
        if removed:
            print(f"[DB-IMPORT] Removed {removed} stale stories")

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
    """Approvals live in the DB. Only import from JSON if DB is empty."""
    existing = db.get_all_approvals()
    if existing:
        return 0
    approvals = _load_json(APPROVALS_JSON, {})
    count = 0
    for headline, a in approvals.items():
        db.create_approval(
            headline=headline,
            ministry=a.get("ministry", ""),
            final_text=a.get("final_text", ""),
            approved_by=a.get("approved_by", "system"),
        )
        count += 1
    return count


def import_from_json():
    """Sync everything from JSON to DB."""
    n_s = import_stories(replace=True)
    n_r = import_responses()
    n_a = import_approvals()
    total = len(db.get_stories())
    print(f"[DB-IMPORT] Stories: {n_s} (DB total: {total}), Responses: {n_r}, Approvals: {n_a}")


if __name__ == "__main__":
    import_from_json()