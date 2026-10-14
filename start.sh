#!/bin/bash
set -e

echo "[START] Working directory: $(pwd)"
echo "[START] Python version: $(python --version)"

# ============================================================
# Redirect /app/data to the Railway volume (if one is mounted)
# ============================================================
# Every pipeline script writes to paths like `data/processed/mapped.json`
# relative to the project root. Without this symlink, those paths resolve
# to the container's ephemeral filesystem, and any file written by one
# script is invisible to the next script that runs as a separate process.
if [ -n "$RAILWAY_VOLUME_MOUNT_PATH" ]; then
    echo "[START] Volume detected at $RAILWAY_VOLUME_MOUNT_PATH"

    # Create the full data folder structure on the volume
    mkdir -p "$RAILWAY_VOLUME_MOUNT_PATH/data/processed"
    mkdir -p "$RAILWAY_VOLUME_MOUNT_PATH/data/raw"
    mkdir -p "$RAILWAY_VOLUME_MOUNT_PATH/data/processed/briefs"

    # If /app/data exists and isn't a symlink yet, migrate its contents
    # to the volume then remove it so we can replace it with a symlink.
    if [ -d "/app/data" ] && [ ! -L "/app/data" ]; then
        echo "[START] Migrating existing /app/data -> volume"
        cp -rn /app/data/. "$RAILWAY_VOLUME_MOUNT_PATH/data/" 2>/dev/null || true
        rm -rf /app/data
    fi

    # Create the symlink so /app/data points at the volume
    if [ ! -e "/app/data" ]; then
        ln -s "$RAILWAY_VOLUME_MOUNT_PATH/data" /app/data
    fi

    echo "[START] /app/data -> $(readlink /app/data)"
else
    echo "[START] No volume detected — using container-local /app/data"
fi

# ============================================================
# Initialize the database schema
# ============================================================
echo "[START] Initializing database schema..."
python -c "from src.db import init_db; init_db()"

# ============================================================
# Seed demo users if they don't exist
# ============================================================
echo "[START] Ensuring demo users exist..."
python - <<'PY'
import os
import bcrypt
from src import db

# Default demo users — override any via env vars or remove for production
DEMO_USERS = [
    {"username": "lucia",         "name": "Lucia Witbooi",                "role": "admin",     "ministry": None},
    {"username": "given",         "name": "Given Amupolo",                "role": "admin",     "ministry": None},
    {"username": "likius",        "name": "Likius Haufiku",               "role": "analyst",   "ministry": None},
    {"username": "mict_director", "name": "MICT Director of Communications", "role": "oversight", "ministry": None},
    {"username": "health_officer",         "name": "Health Comms Officer",         "role": "ministry", "ministry": "Ministry of Health and Social Services"},
    {"username": "finance_officer",        "name": "Finance Comms Officer",        "role": "ministry", "ministry": "Ministry of Finance"},
    {"username": "education_officer",      "name": "Education Comms Officer",      "role": "ministry", "ministry": "Ministry of Education, Innovation, Youth, Sports, Arts and Culture"},
    {"username": "agriculture_officer",    "name": "Agriculture Comms Officer",    "role": "ministry", "ministry": "Ministry of Agriculture, Fisheries, Water and Land Reform"},
    {"username": "home_affairs_officer",   "name": "Home Affairs Comms Officer",   "role": "ministry", "ministry": "Ministry of Home Affairs, Immigration, Safety and Security"},
]

DEFAULT_PASSWORD = os.getenv("DEMO_PASSWORD", "changeme123")
hashed = bcrypt.hashpw(DEFAULT_PASSWORD.encode("utf-8")[:72], bcrypt.gensalt()).decode("utf-8")

created = 0
for u in DEMO_USERS:
    if not db.get_user(u["username"]):
        db.create_user(
            username=u["username"],
            email=f"{u['username']}@mict.gov.na",
            name=u["name"],
            password_hash=hashed,
            role=u["role"],
            ministry=u["ministry"],
        )
        created += 1
        print(f"[START] + created user {u['username']} ({u['role']})")
    else:
        print(f"[START] = user {u['username']} already exists")
print(f"[START] Users created this boot: {created}")
print(f"[START] Total users now: {len(db.get_all_users())}")
PY

# ============================================================
# Launch the API
# ============================================================
echo "[START] Launching uvicorn on port $PORT..."
exec uvicorn api.main:app --host 0.0.0.0 --port "${PORT:-8000}"