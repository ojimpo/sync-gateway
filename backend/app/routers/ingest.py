from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..auth import require_api_key
from ..database import get_db
from ..models import Source, Record, Run, IngestError
from ..schemas import IngestBatch, IngestRecord, IngestResponse

router = APIRouter(prefix="/api/v1/ingest", tags=["ingest"])


def _upsert_source(slug: str, db: Session) -> Source | None:
    return db.query(Source).filter(Source.slug == slug).first()


def _ingest_one(rec: IngestRecord, db: Session) -> tuple[bool, str]:
    source = _upsert_source(rec.source_slug, db)
    if not source:
        return False, f"Unknown source slug: {rec.source_slug}"
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
    if rec.run_id:
        run = db.get(Run, rec.run_id)
        if run:
            run.records_ingested = (run.records_ingested or 0) + 1
    return True, ""


@router.post("/events", response_model=IngestResponse, status_code=202)
def ingest_events(body: IngestBatch, db: Session = Depends(get_db), _key: str = Depends(require_api_key)):
    accepted = 0
    failed = 0
    errors: list[str] = []

    for rec in body.records:
        try:
            ok, msg = _ingest_one(rec, db)
            if ok:
                accepted += 1
            else:
                failed += 1
                errors.append(msg)
                if rec.run_id:
                    ie = IngestError(
                        run_id=rec.run_id,
                        raw_payload=rec.model_dump(mode="json"),
                        error_message=msg,
                    )
                    db.add(ie)
        except Exception as e:
            failed += 1
            errors.append(str(e))

    db.commit()
    return IngestResponse(accepted=accepted, failed=failed, errors=errors)
