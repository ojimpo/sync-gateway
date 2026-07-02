from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..auth import require_api_key
from ..database import get_db
from ..models import IngestError, Record, Run, Source
from ..schemas import IngestBatch, IngestRecord, IngestResponse

router = APIRouter(prefix="/api/v1/ingest", tags=["ingest"])

# 更新時に None でない値だけで既存レコードを上書きするフィールド
_UPDATABLE_FIELDS = ("record_type", "title", "author", "rating", "status", "event_date")


def _get_source_by_slug(slug: str, db: Session) -> Source | None:
    return db.query(Source).filter(Source.slug == slug).first()


def _ingest_one(rec: IngestRecord, effective_run_id: int | None, db: Session) -> tuple[bool, str, bool | None]:
    """Upsert a single record.

    Returns (ok, error_msg, was_created).
    was_created is True for new records, False for updates, None on failure.
    """
    source = _get_source_by_slug(rec.source_slug, db)
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

    if not existing:
        record = Record(
            source_id=source.id,
            run_id=effective_run_id,
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

    if effective_run_id is not None:
        existing.run_id = effective_run_id
    for field in _UPDATABLE_FIELDS:
        value = getattr(rec, field)
        if value is not None:
            setattr(existing, field, value)
    if rec.payload:
        merged = dict(existing.payload or {})
        merged.update(rec.payload)
        existing.payload = merged
    return True, "", False


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


def _create_auto_runs(records: list[IngestRecord], db: Session) -> dict[str, int]:
    """run_id を持たないレコードのために source_slug ごとに Run を自動作成する。"""
    auto_runs: dict[str, int] = {}  # source_slug -> run_id
    for rec in records:
        if rec.run_id is None and rec.source_slug not in auto_runs:
            source = _get_source_by_slug(rec.source_slug, db)
            if source:
                run = Run(source_id=source.id, status="running")
                db.add(run)
                db.flush()
                auto_runs[rec.source_slug] = run.id
    return auto_runs


def _finalize_auto_runs(run_ids, db: Session) -> None:
    """自動作成した Run を集計結果に応じて success / failed で確定する。"""
    now = datetime.now(timezone.utc)
    for run_id in run_ids:
        run = db.get(Run, run_id)
        if run:
            run.status = "success" if run.records_failed == 0 else "failed"
            run.finished_at = now


@router.post("/events", response_model=IngestResponse, status_code=202)
def ingest_events(body: IngestBatch, db: Session = Depends(get_db), _key: str = Depends(require_api_key)):
    accepted = 0
    failed = 0
    errors: list[str] = []

    auto_runs = _create_auto_runs(body.records, db)

    for rec in body.records:
        effective_run_id = rec.run_id if rec.run_id is not None else auto_runs.get(rec.source_slug)
        try:
            ok, msg, was_created = _ingest_one(rec, effective_run_id, db)
            if ok:
                accepted += 1
            else:
                failed += 1
                errors.append(msg)
                if effective_run_id:
                    db.add(IngestError(
                        run_id=effective_run_id,
                        raw_payload=rec.model_dump(mode="json"),
                        error_message=msg,
                    ))
            if effective_run_id:
                _update_run_stats(effective_run_id, was_created if ok else None, db)
        except Exception as e:
            failed += 1
            errors.append(str(e))
            if effective_run_id:
                _update_run_stats(effective_run_id, None, db)

    _finalize_auto_runs(auto_runs.values(), db)

    db.commit()
    return IngestResponse(accepted=accepted, failed=failed, errors=errors)
