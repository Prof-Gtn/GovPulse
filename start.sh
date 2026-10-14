#!/bin/bash
set -e

echo "[START] Working directory: $(pwd)"
echo "[START] Python version: $(python --version)"

echo "[START] Initializing database schema..."
python -c "from src.db import init_db; init_db()"

echo "[START] Seeding users if DB is empty..."
python - <<'PY'
from src import db
if not db.get_all_users():
    print("[START] No users found — running migration to seed from config.yaml")
    try:
        from src.migrate import run_migration
        run_migration()
    except Exception as e:
        print(f"[START] Migration failed (non-fatal): {e}")
else:
    print(f"[START] DB already has {len(db.get_all_users())} users — skipping seed")
PY

echo "[START] Launching uvicorn on port $PORT..."
exec uvicorn api.main:app --host 0.0.0.0 --port "${PORT:-8000}"