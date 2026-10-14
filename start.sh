#!/bin/bash
set -e

echo "[START] Working directory: $(pwd)"
echo "[START] Python version: $(python --version)"

echo "[START] Initializing database schema..."
python -c "from src.db import init_db; init_db()"

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

echo "[START] Launching uvicorn on port $PORT..."
exec uvicorn api.main:app --host 0.0.0.0 --port "${PORT:-8000}"