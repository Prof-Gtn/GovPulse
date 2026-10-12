"""
GovPulse — Cleanup duplicate stories
Removes duplicate rows, keeping the earliest by id.
"""

import os
import sys


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src import db


def cleanup():
    with db.get_db() as conn:
        before = conn.execute("SELECT COUNT(*) FROM stories").fetchone()[0]

        conn.execute("""
            DELETE FROM stories
            WHERE id NOT IN (
                SELECT MIN(id) FROM stories GROUP BY headline
            )
        """)

        after = conn.execute("SELECT COUNT(*) FROM stories").fetchone()[0]

    print(f"Before: {before}")
    print(f"After:  {after}")
    print(f"Removed: {before - after} duplicates")


if __name__ == "__main__":
    cleanup()