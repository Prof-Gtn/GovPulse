"""
GovPulse — Database helper
All SQLite access goes through this module.
"""

import os
import json
import sqlite3
from contextlib import contextmanager


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(PROJECT_ROOT, "data", "govpulse.db")
SCHEMA_PATH = os.path.join(PROJECT_ROOT, "src", "schema.sql")


# ------------------------------------------------------------
# CONNECTION
# ------------------------------------------------------------
def _connect():
    """Open a connection with row access by column name."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")   # better concurrency
    return conn


@contextmanager
def get_db():
    """Context manager — auto-commits and closes."""
    conn = _connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Create tables from schema.sql if they don't exist."""
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema = f.read()
    conn = _connect()
    try:
        conn.executescript(schema)
        conn.commit()
    finally:
        conn.close()


# ------------------------------------------------------------
# ROW HELPERS
# ------------------------------------------------------------
def row_to_dict(row):
    """Convert a sqlite3.Row into a plain dict."""
    if row is None:
        return None
    return {k: row[k] for k in row.keys()}


def parse_json_field(value, default=None):
    """Safely parse a JSON string field."""
    if not value:
        return default if default is not None else []
    try:
        return json.loads(value)
    except Exception:
        return default if default is not None else []


def to_json_field(value):
    """Serialize a Python object to a JSON string."""
    return json.dumps(value, ensure_ascii=False)


# ------------------------------------------------------------
# USERS
# ------------------------------------------------------------
def get_user(username: str):
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
        return row_to_dict(row)


def get_all_users():
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM users ORDER BY created_at DESC"
        ).fetchall()
        return [row_to_dict(r) for r in rows]


def create_user(username, email, name, password_hash, role, ministry=None):
    from datetime import datetime
    with get_db() as conn:
        conn.execute(
            """INSERT INTO users
               (username, email, name, password_hash, role, ministry, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (username, email, name, password_hash, role, ministry,
             datetime.now().isoformat()),
        )


def update_last_login(username: str):
    from datetime import datetime
    with get_db() as conn:
        conn.execute(
            "UPDATE users SET last_login = ? WHERE username = ?",
            (datetime.now().isoformat(), username),
        )


def delete_user(username: str):
    with get_db() as conn:
        conn.execute("DELETE FROM users WHERE username = ?", (username,))


# ------------------------------------------------------------
# STORIES
def get_stories(sentiment=None, source=None, ministry=None, limit=None):
    """
    Return stories, optionally filtered.
    If 'ministry' is provided, only stories tagged to that ministry.
    """
    query = "SELECT * FROM stories WHERE 1=1"
    params = []
    if sentiment:
        query += " AND sentiment = ?"
        params.append(sentiment)
    if source:
        query += " AND source = ?"
        params.append(source)
    query += " ORDER BY created_at DESC"
    if limit:
        query += f" LIMIT {int(limit)}"

    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
        stories = [row_to_dict(r) for r in rows]

    # Deserialize JSON fields
    for s in stories:
        s["oma"] = parse_json_field(s.get("oma"), [])
        s["entities"] = parse_json_field(s.get("entities"), {})

    # Filter by ministry in Python (oma is stored as a JSON array in a text column)
    if ministry:
        target = ministry.strip().lower()
        stories = [
            s for s in stories
            if any(
                (oma or "").strip().lower() == target
                for oma in (s.get("oma") or [])
            )
        ]

    return stories


def get_story(headline: str):
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM stories WHERE headline = ?", (headline,)
        ).fetchone()
        story = row_to_dict(row)
        if story:
            story["oma"] = parse_json_field(story.get("oma"), [])
            story["entities"] = parse_json_field(story.get("entities"), {})
        return story


def upsert_story(story: dict):
    """Insert or update a story by headline."""
    from datetime import datetime

    with get_db() as conn:
        existing = conn.execute(
            "SELECT id FROM stories WHERE headline = ?",
            (story.get("headline"),),
        ).fetchone()

        oma_json = to_json_field(story.get("oma") or [])
        entities_json = to_json_field(story.get("entities") or {})

        if existing:
            conn.execute(
                """UPDATE stories SET
                    source = ?, url = ?, body = ?, page = ?,
                    ai_summary = ?, sentiment = ?, sentiment_confidence = ?,
                    government_source = ?, oma = ?, entities = ?, scraped_at = ?
                WHERE headline = ?""",
                (
                    story.get("source"),
                    story.get("url"),
                    story.get("body"),
                    story.get("page"),
                    story.get("ai_summary"),
                    story.get("sentiment"),
                    story.get("sentiment_confidence"),
                    story.get("government_source"),
                    oma_json,
                    entities_json,
                    story.get("scraped_at"),
                    story.get("headline"),
                ),
            )
        else:
            conn.execute(
                """INSERT INTO stories
                   (source, headline, url, body, page, ai_summary,
                    sentiment, sentiment_confidence, government_source,
                    oma, entities, scraped_at, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    story.get("source"),
                    story.get("headline"),
                    story.get("url"),
                    story.get("body"),
                    story.get("page"),
                    story.get("ai_summary"),
                    story.get("sentiment"),
                    story.get("sentiment_confidence"),
                    story.get("government_source"),
                    oma_json,
                    entities_json,
                    story.get("scraped_at"),
                    datetime.now().isoformat(),
                ),
            )


def update_story_fields(headline: str, fields: dict):
    """Update specific fields on a story."""
    if not fields:
        return
    # Serialize any JSON fields
    if "oma" in fields:
        fields = dict(fields)
        fields["oma"] = to_json_field(fields["oma"])
    if "entities" in fields:
        fields = dict(fields)
        fields["entities"] = to_json_field(fields["entities"])

    keys = list(fields.keys())
    values = [fields[k] for k in keys]
    set_clause = ", ".join(f"{k} = ?" for k in keys)
    values.append(headline)

    with get_db() as conn:
        conn.execute(
            f"UPDATE stories SET {set_clause} WHERE headline = ?",
            values,
        )


def delete_story(headline: str):
    with get_db() as conn:
        conn.execute("DELETE FROM stories WHERE headline = ?", (headline,))


# ------------------------------------------------------------
# RESPONSES
# ------------------------------------------------------------
def get_response(headline: str):
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM responses WHERE headline = ?", (headline,)
        ).fetchone()
        response = row_to_dict(row)
        if response:
            response["precedents"] = parse_json_field(response.get("precedents"), [])
        return response


def get_all_responses():
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM responses").fetchall()
        result = [row_to_dict(r) for r in rows]
    for r in result:
        r["precedents"] = parse_json_field(r.get("precedents"), [])
    return result


def upsert_response(headline, ministry, draft, status, precedents=None, generated_at=None):
    from datetime import datetime
    precedents_json = to_json_field(precedents or [])
    ts = generated_at or datetime.now().isoformat()

    with get_db() as conn:
        existing = conn.execute(
            "SELECT id FROM responses WHERE headline = ?", (headline,)
        ).fetchone()
        if existing:
            conn.execute(
                """UPDATE responses SET ministry = ?, draft = ?, status = ?,
                   precedents = ?, generated_at = ? WHERE headline = ?""",
                (ministry, draft, status, precedents_json, ts, headline),
            )
        else:
            conn.execute(
                """INSERT INTO responses
                   (headline, ministry, draft, status, precedents, generated_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (headline, ministry, draft, status, precedents_json, ts),
            )


# ------------------------------------------------------------
# APPROVALS
# ------------------------------------------------------------
def get_approval(headline: str):
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM approvals WHERE headline = ?", (headline,)
        ).fetchone()
        return row_to_dict(row)


def get_all_approvals():
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM approvals ORDER BY approved_at DESC"
        ).fetchall()
        return [row_to_dict(r) for r in rows]


def get_approvals_as_dict():
    """Return approvals as {headline: {...}} for compatibility with old code."""
    approvals = get_all_approvals()
    return {a["headline"]: a for a in approvals}


def create_approval(headline, ministry, final_text, approved_by):
    from datetime import datetime
    with get_db() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO approvals
               (headline, ministry, final_text, approved_at, approved_by)
               VALUES (?, ?, ?, ?, ?)""",
            (headline, ministry, final_text,
             datetime.now().isoformat(), approved_by),
        )


def delete_approval(headline: str):
    with get_db() as conn:
        conn.execute("DELETE FROM approvals WHERE headline = ?", (headline,))


# ------------------------------------------------------------
# AUDIT LOG
# ------------------------------------------------------------
def log_audit(action, user, target="", details=None):
    from datetime import datetime
    details_json = to_json_field(details or {})
    with get_db() as conn:
        conn.execute(
            """INSERT INTO audit_log (timestamp, action, user, target, details)
               VALUES (?, ?, ?, ?, ?)""",
            (datetime.now().isoformat(), action, user, target, details_json),
        )


def get_audit_entries(limit=200, action=None, user=None):
    query = "SELECT * FROM audit_log WHERE 1=1"
    params = []
    if action:
        query += " AND action = ?"
        params.append(action)
    if user:
        query += " AND user = ?"
        params.append(user)
    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)

    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
        result = [row_to_dict(r) for r in rows]
    for entry in result:
        entry["details"] = parse_json_field(entry.get("details"), {})
    return result


# ------------------------------------------------------------
# SOURCES
# ------------------------------------------------------------
def get_sources(active_only=False):
    query = "SELECT * FROM sources"
    if active_only:
        query += " WHERE active = 1"
    query += " ORDER BY name"
    with get_db() as conn:
        rows = conn.execute(query).fetchall()
        return [row_to_dict(r) for r in rows]


def upsert_source(name, url, type_="online", active=1):
    from datetime import datetime
    with get_db() as conn:
        existing = conn.execute(
            "SELECT id FROM sources WHERE name = ?", (name,)
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE sources SET url = ?, type = ?, active = ? WHERE name = ?",
                (url, type_, active, name),
            )
        else:
            conn.execute(
                """INSERT INTO sources (name, url, type, active, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (name, url, type_, active, datetime.now().isoformat()),
            )