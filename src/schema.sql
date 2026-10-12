-- ============================================================
-- GovPulse Database Schema
-- SQLite
-- ============================================================

PRAGMA foreign_keys = ON;

-- ------------------------------------------------------------
-- USERS
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    username      TEXT PRIMARY KEY,
    email         TEXT NOT NULL,
    name          TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL CHECK(role IN ('admin', 'analyst', 'ministry', 'oversight')),
    ministry      TEXT,
    created_at    TEXT NOT NULL,
    last_login    TEXT
);

-- ------------------------------------------------------------
-- STORIES
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS stories (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    source                TEXT NOT NULL,
    headline              TEXT NOT NULL UNIQUE,
    url                   TEXT,
    body                  TEXT,
    page                  TEXT,
    ai_summary            TEXT,
    sentiment             TEXT,
    sentiment_confidence  REAL,
    government_source     TEXT,
    oma                   TEXT,       -- JSON array as string
    entities              TEXT,       -- JSON object as string
    scraped_at            TEXT,
    created_at            TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_stories_sentiment ON stories(sentiment);
CREATE INDEX IF NOT EXISTS idx_stories_created   ON stories(created_at);

-- ------------------------------------------------------------
-- RESPONSES (AI-drafted)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS responses (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    headline       TEXT NOT NULL UNIQUE,
    ministry       TEXT,
    draft          TEXT,
    status         TEXT,       -- ok, failed, skipped
    precedents     TEXT,       -- JSON
    generated_at   TEXT
);

-- ------------------------------------------------------------
-- APPROVALS
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS approvals (
    headline       TEXT PRIMARY KEY,
    ministry       TEXT,
    final_text     TEXT,
    approved_at    TEXT NOT NULL,
    approved_by    TEXT NOT NULL
);

-- ------------------------------------------------------------
-- AUDIT LOG
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit_log (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp      TEXT NOT NULL,
    action         TEXT NOT NULL,
    user           TEXT NOT NULL,
    target         TEXT,
    details        TEXT        -- JSON
);

CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_user      ON audit_log(user);
CREATE INDEX IF NOT EXISTS idx_audit_action    ON audit_log(action);

-- ------------------------------------------------------------
-- SOURCES (managed list of scraped sources)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sources (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    name           TEXT NOT NULL UNIQUE,
    url            TEXT NOT NULL,
    type           TEXT,        -- online, print, broadcast
    active         INTEGER DEFAULT 1,
    created_at     TEXT NOT NULL
);