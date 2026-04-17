"""
fix_stuck_papers.py

Run this ONCE if you see:
  "UNIQUE constraint failed: papers.file_path"
  "This Session's transaction has been rolled back"

What it does:
  1. Finds papers stuck in 'processing' status (crashed mid-scan)
  2. Marks them as 'failed' so the scanner can retry them
  3. Reports any duplicate file_path or sha256 entries

Run from the backend/ directory with the venv active:
  python fix_stuck_papers.py
"""
import sys
from pathlib import Path

# Add backend/app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.db.database import get_session_factory, init_db
from app.models.paper import Paper, PaperStatus
from datetime import datetime


def main():
    print("PaperLens -- DB repair utility")
    print("=" * 50)

    init_db()
    db = get_session_factory()()

    try:
        # 1. Find papers stuck in 'processing'
        stuck = db.query(Paper).filter(Paper.status == PaperStatus.processing).all()
        print(f"\nFound {len(stuck)} paper(s) stuck in 'processing' status:")
        for p in stuck:
            print(f"  - {p.file_name}  (id={p.id[:8]})")
            p.status = PaperStatus.failed
            p.error_message = "Scan was interrupted — marked failed by fix_stuck_papers.py"
            p.processed_at = datetime.utcnow()

        if stuck:
            db.commit()
            print(f"  -> Reset {len(stuck)} paper(s) to 'failed'.")
            print("     Use 'Reprocess Failed' in the Scan page to retry them.")
        else:
            print("  None found — no action needed.")

        # 2. Report duplicate file_paths
        from sqlalchemy import func
        dup_paths = (
            db.query(Paper.file_path, func.count(Paper.id).label("cnt"))
            .group_by(Paper.file_path)
            .having(func.count(Paper.id) > 1)
            .all()
        )
        if dup_paths:
            print(f"\nWARNING: {len(dup_paths)} duplicate file_path(s) found:")
            for dp in dup_paths:
                papers = db.query(Paper).filter(Paper.file_path == dp.file_path).all()
                print(f"  {dp.file_path}  ({dp.cnt} records)")
                for pp in papers:
                    print(f"    id={pp.id[:8]}  status={pp.status.value}  sha={pp.sha256[:16]}")
                # Keep the 'done' one if possible, delete the rest
                done = [pp for pp in papers if pp.status == PaperStatus.done]
                others = [pp for pp in papers if pp.status != PaperStatus.done]
                if done and others:
                    for pp in others:
                        print(f"    -> Deleting duplicate id={pp.id[:8]} (status={pp.status.value})")
                        db.delete(pp)
                    db.commit()
                    print(f"    -> Kept id={done[0].id[:8]} (status=done)")
        else:
            print("\nNo duplicate file_path entries found — DB is clean.")

        # 3. Report duplicate sha256s
        dup_shas = (
            db.query(Paper.sha256, func.count(Paper.id).label("cnt"))
            .group_by(Paper.sha256)
            .having(func.count(Paper.id) > 1)
            .all()
        )
        if dup_shas:
            print(f"\nWARNING: {len(dup_shas)} duplicate sha256(s) found:")
            for ds in dup_shas:
                papers = db.query(Paper).filter(Paper.sha256 == ds.sha256).all()
                print(f"  sha={ds.sha256[:16]}...  ({ds.cnt} records)")
                for pp in papers:
                    print(f"    id={pp.id[:8]}  status={pp.status.value}  path={pp.file_name}")
        else:
            print("No duplicate sha256 entries found.")

        # 4. Summary
        total = db.query(Paper).count()
        done  = db.query(Paper).filter(Paper.status == PaperStatus.done).count()
        failed = db.query(Paper).filter(Paper.status == PaperStatus.failed).count()
        pending = db.query(Paper).filter(Paper.status == PaperStatus.pending).count()
        print(f"\nDB Summary:")
        print(f"  Total:      {total}")
        print(f"  Done:       {done}")
        print(f"  Failed:     {failed}  (use 'Reprocess Failed' to retry)")
        print(f"  Pending:    {pending}")

        print("\nRepair complete. You can now run a scan normally.")

    finally:
        db.close()


if __name__ == "__main__":
    main()
