from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Record, Source
from ..schemas import RecordOut

router = APIRouter(prefix="/api/v1/records", tags=["records"])


@router.get("", response_model=list[RecordOut])
def list_records(
    source: str | None = Query(None, description="Filter by source slug"),
    from_: datetime | None = Query(None, alias="from"),
    to: datetime | None = Query(None),
    limit: int = Query(50, le=500),
    db: Session = Depends(get_db),
):
    q = db.query(Record)
    if source:
        src = db.query(Source).filter(Source.slug == source).first()
        if src:
            q = q.filter(Record.source_id == src.id)
        else:
            return []
    if from_:
        q = q.filter(Record.ingested_at >= from_)
    if to:
        q = q.filter(Record.ingested_at <= to)
    return q.order_by(Record.ingested_at.desc()).limit(limit).all()
