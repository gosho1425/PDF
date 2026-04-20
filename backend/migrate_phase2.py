"""
migrate_phase2.py — Phase 2 database migration.

Run this ONCE after pulling the Phase 2 update:

  cd backend
  .venv\\Scripts\\activate.bat      (Windows)
  python migrate_phase2.py

What it does:
  1. Creates the 6 new optimization tables if they don't exist.
  2. Does NOT touch any existing tables (papers, app_settings are safe).
  3. Reports what was created vs what already existed.

This is safe to run multiple times (idempotent).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.db.database import get_engine, init_db
from sqlalchemy import inspect, text


PHASE2_TABLES = [
    "optimization_projects",
    "project_variables",
    "user_experiments",
    "experiment_measurements",
    "recommendation_runs",
    "recommended_candidates",
]


def main():
    print("PaperLens Phase 2 — Database Migration")
    print("=" * 50)

    # init_db() calls create_all() which is safe (CREATE TABLE IF NOT EXISTS)
    init_db()

    engine   = get_engine()
    insp     = inspect(engine)
    existing = insp.get_table_names()

    print("\nExisting tables:")
    for t in existing:
        status = "✓ already exists" if t in PHASE2_TABLES else "(Phase 1)"
        print(f"  {t:40s}  {status}")

    created  = [t for t in PHASE2_TABLES if t in existing]
    print(f"\nPhase 2 tables verified: {len(created)}/{len(PHASE2_TABLES)}")

    missing  = [t for t in PHASE2_TABLES if t not in existing]
    if missing:
        print(f"\nWARNING: These tables are missing: {missing}")
        print("This should not happen — check for import errors above.")
    else:
        print("\nAll Phase 2 tables are present.")
        print("\nMigration complete.")
        print("\nNext steps:")
        print("  1. Restart the backend (start-backend.bat)")
        print("  2. Navigate to http://localhost:3000/optimization")
        print("  3. Create a project and add variables")
        print("  4. Run a scan or add experiments, then click 'Recommend'")


if __name__ == "__main__":
    main()
