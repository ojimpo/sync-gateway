"""Seed script: registers sources and inserts sample records for bookmeter & filmarks."""
import json
import os
import sys
from pathlib import Path

# Allow running from repo root
sys.path.insert(0, str(Path(__file__).parent))

os.environ.setdefault("DB_PATH", "./data/arigato.db")

from app.database import engine, SessionLocal, Base
from app.models import Source, Run, Record
from datetime import datetime, timezone

Base.metadata.create_all(bind=engine)

SOURCES = [
    {"slug": "bookmeter", "display_name": "読書メーター", "description": "bookmeter.com の読書記録"},
    {"slug": "filmarks", "display_name": "Filmarks", "description": "filmarks.com の映画・ドラマ鑑賞記録"},
]

SAMPLES_DIR = Path(__file__).parent.parent / "samples"


def seed():
    db = SessionLocal()
    try:
        # Sources
        source_map: dict[str, Source] = {}
        for s in SOURCES:
            existing = db.query(Source).filter(Source.slug == s["slug"]).first()
            if not existing:
                src = Source(**s)
                db.add(src)
                db.flush()
                print(f"  + source: {s['slug']}")
                source_map[s["slug"]] = src
            else:
                print(f"  ~ source exists: {s['slug']}")
                source_map[s["slug"]] = existing

        # Seed run + records from sample payloads
        for payload_file in sorted(SAMPLES_DIR.glob("*.json")):
            data = json.loads(payload_file.read_text())
            records_list = data if isinstance(data, list) else data.get("records", [])
            if not records_list:
                continue
            slug = records_list[0].get("source_slug", "")
            source = source_map.get(slug)
            if not source:
                print(f"  ! unknown source slug in {payload_file.name}, skipping")
                continue

            run = Run(source_id=source.id, status="success",
                      finished_at=datetime.now(timezone.utc),
                      records_processed=len(records_list),
                      records_created=len(records_list))
            db.add(run)
            db.flush()

            for r in records_list:
                rec = Record(
                    source_id=source.id,
                    run_id=run.id,
                    external_id=r.get("external_id"),
                    record_type=r.get("record_type", "unknown"),
                    title=r.get("title"),
                    author=r.get("author"),
                    rating=r.get("rating"),
                    status=r.get("status"),
                    event_date=datetime.fromisoformat(r["event_date"]) if r.get("event_date") else None,
                    payload=r.get("payload", {}),
                )
                db.add(rec)
            print(f"  + {len(records_list)} records from {payload_file.name}")

        db.commit()
        print("Seed complete.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
