"""
GovPulse — Migration script
Loads data from config.yaml and existing JSON files into SQLite.
Run once.
"""

import json
import os
import sys
from datetime import datetime

import yaml


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from src import db


# ------------------------------------------------------------
# PATHS
# ------------------------------------------------------------
CONFIG_YAML    = os.path.join(PROJECT_ROOT, "app", "config.yaml")
MAPPED_JSON    = os.path.join(PROJECT_ROOT, "data", "processed", "mapped.json")
RESPONSES_JSON = os.path.join(PROJECT_ROOT, "data", "processed", "responses.json")
APPROVALS_JSON = os.path.join(PROJECT_ROOT, "data", "processed", "approvals.json")
SOURCES_JSON   = os.path.join(PROJECT_ROOT, "data", "sources.json")


def _load_json(path, default=None):
    if not os.path.exists(path):
        return default if default is not None else []
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    except Exception as e:
        print(f"[WARN] Could not load {path}: {e}")
        return default if default is not None else []


# ------------------------------------------------------------
# MIGRATE USERS
# ------------------------------------------------------------
def migrate_users():
    print("\n[1/5] Migrating users from config.yaml...")

    if not os.path.exists(CONFIG_YAML):
        print("  [WARN] config.yaml not found, skipping users")
        return

    with open(CONFIG_YAML, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    users = config.get("credentials", {}).get("usernames", {})

    for username, u in users.items():
        existing = db.get_user(username)
        if existing:
            print(f"  [SKIP] {username} (already exists)")
            continue

        # Map "ministry" role if the config has an explicit role
        role = u.get("role", "admin")

        db.create_user(
            username=username,
            email=u.get("email", ""),
            name=u.get("name", username),
            password_hash=u.get("password", ""),
            role=role,
            ministry=u.get("ministry"),
        )
        print(f"  [OK] {username} ({role})")


# ------------------------------------------------------------
# MIGRATE STORIES
# ------------------------------------------------------------
def migrate_stories():
    print("\n[2/5] Migrating stories from mapped.json...")

    stories = _load_json(MAPPED_JSON, [])
    if not stories:
        print("  [WARN] No stories found")
        return

    count = 0
    for story in stories:
        try:
            db.upsert_story(story)
            count += 1
        except Exception as e:
            print(f"  [ERR] {story.get('headline', '?')[:50]}: {e}")

    print(f"  [OK] Migrated {count} stories")


# ------------------------------------------------------------
# MIGRATE RESPONSES
# ------------------------------------------------------------
def migrate_responses():
    print("\n[3/5] Migrating responses from responses.json...")

    responses = _load_json(RESPONSES_JSON, [])
    if not responses:
        print("  [WARN] No responses found")
        return

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

    print(f"  [OK] Migrated {count} responses")


# ------------------------------------------------------------
# MIGRATE APPROVALS
# ------------------------------------------------------------
def migrate_approvals():
    print("\n[4/5] Migrating approvals from approvals.json...")

    approvals = _load_json(APPROVALS_JSON, {})
    if not approvals:
        print("  [WARN] No approvals found")
        return

    count = 0
    for headline, a in approvals.items():
        try:
            db.create_approval(
                headline=headline,
                ministry=a.get("ministry", ""),
                final_text=a.get("final_text", ""),
                approved_by=a.get("approved_by", "system"),
            )
            count += 1
        except Exception as e:
            print(f"  [ERR] {headline[:50]}: {e}")

    print(f"  [OK] Migrated {count} approvals")


# ------------------------------------------------------------
# MIGRATE SOURCES
# ------------------------------------------------------------
def migrate_sources():
    print("\n[5/5] Migrating sources from sources.json...")

    sources = _load_json(SOURCES_JSON, {})
    enabled = sources.get("enabled", []) if isinstance(sources, dict) else []

    if not enabled:
        # Fallback — seed defaults
        enabled = [
            {"name": "The Namibian", "url": "https://www.namibian.com.na/",
             "type": "online", "active": True},
            {"name": "New Era", "url": "https://neweralive.na/",
             "type": "online", "active": True},
            {"name": "NBC Digital", "url": "https://www.nbc.na/news",
             "type": "online", "active": False},
        ]

    count = 0
    for s in enabled:
        db.upsert_source(
            name=s.get("name"),
            url=s.get("url"),
            type_=s.get("type", "online"),
            active=1 if s.get("active") else 0,
        )
        count += 1

    print(f"  [OK] Migrated {count} sources")


# ------------------------------------------------------------
# MAIN
# ------------------------------------------------------------
def run_migration():
    print("=" * 60)
    print("  GovPulse — Database Migration")
    print("=" * 60)

    print(f"\nDatabase: {db.DB_PATH}")
    print(f"Started:  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Create tables
    print("\n[0/5] Initializing schema...")
    db.init_db()
    print("  [OK] Schema created")

    # Migrate data
    migrate_users()
    migrate_stories()
    migrate_responses()
    migrate_approvals()
    migrate_sources()

    # Summary
    print("\n" + "=" * 60)
    print("  Migration complete")
    print("=" * 60)

    # Print counts
    users      = db.get_all_users()
    stories    = db.get_stories()
    responses  = db.get_all_responses()
    approvals  = db.get_all_approvals()
    sources    = db.get_sources()

    print(f"\nDatabase contents:")
    print(f"  Users:       {len(users)}")
    print(f"  Stories:     {len(stories)}")
    print(f"  Responses:   {len(responses)}")
    print(f"  Approvals:   {len(approvals)}")
    print(f"  Sources:     {len(sources)}")

    print(f"\nDone: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    run_migration()