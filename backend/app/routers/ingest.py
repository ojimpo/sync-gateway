from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..auth import require_api_key
from ..database import get_db
from ..models import Source, Record, Run, IngestError
from ..schemas import IngestBatch, IngestRecord, IngestResponse

router = APIRouter(prefix="/api/v1/ingest", tags=["ingest"])


def _upsert_source(slug: str, db: Session) -> Source | None:
    return db.query(Source).filter(Source.slug == slug).first()


def _ingest_one(rec: IngestRecord, db: Session) -> tuple[bool, str, bool | None]:
    """Upsert a single record.

    Returns (ok, error_msg, was_created).
    was_created is True for new records, False for updates, None on failure.
    """
    source = _upsert_source(rec.source_slug, db)
    if not source:
        return False, f"Unknown source slug: {rec.source_slug}", None

    # Upsert-like behavior by (source_id, external_id)
    existing: Record | None = None
    if rec.external_id:
        existing = (
            db.query(Record)
            .filter(Record.source_id == source.id, Record.external_id == rec.external_id)
            .first()
        )

    if existing:
        existing.run_id = rec.run_id if rec.run_id is not None else existing.run_id
        existing.record_type = rec.record_type if rec.record_type is not None else existing.record_type
        existing.title = rec.title if rec.title is not None else existing.title
        existing.author = rec.author if rec.author is not None else existing.author
        existing.rating = rec.rating if rec.rating is not None else existing.rating
        existing.status = rec.status if rec.status is not None else existing.status
        existing.event_date = rec.event_date if rec.event_date is not None else existing.event_date
        if rec.payload:
            merged = dict(existing.payload or {})
            merged.update(rec.payload)
            existing.payload = merged
        return True, "", False
    else:
        record = Record(
            source_id=source.id,
            run_id=rec.run_id,
            external_id=rec.external_id,
            record_type=rec.record_type,
            title=rec.title,
            author=rec.author,
            rating=rec.rating,
            status=rec.status,
            event_date=rec.event_date,
            payload=rec.payload,
        )
        db.add(record)
        return True, "", True


def _update_run_stats(run_id: int, was_created: bool | None, db: Session) -> None:
    """Increment run counters. was_created=None means failure."""
    run = db.get(Run, run_id)
    if not run:
        return
    run.records_processed += 1
    if was_created is True:
        run.records_created += 1
    elif was_created is False:
        run.records_updated += 1
    else:
        run.records_failed += 1


@router.post("/events", response_model=IngestResponse, status_code=202)
def ingest_events(body: IngestBatch, db: Session = Depends(get_db), _key: str = Depends(require_api_key)):
    accepted = 0
    failed = 0
    errors: list[str] = []

    for rec in body.records:
        try:
            ok, msg, was_created = _ingest_one(rec, db)
            if ok:
                accepted += 1
            else:
                failed += 1
                errors.append(msg)
                if rec.run_id:
                    db.add(IngestError(
                        run_id=rec.run_id,
                        raw_payload=rec.model_dump(mode="json"),
                        error_message=msg,
                    ))
            if rec.run_id:
                _update_run_stats(rec.run_id, was_created if ok else None, db)
        except Exception as e:
            failed += 1
            errors.append(str(e))
            if rec.run_id:
                _update_run_stats(rec.run_id, None, db)

    db.commit()
    return IngestResponse(accepted=accepted, failed=failed, errors=errors)
