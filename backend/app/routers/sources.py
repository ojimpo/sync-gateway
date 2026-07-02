from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session
from ..auth import require_api_key
from ..database import get_db
from ..models import Record, Source
from ..schemas import SourceCreate, SourceOut

router = APIRouter(prefix="/api/v1/sources", tags=["sources"])


@router.get("", response_model=list[SourceOut])
def list_sources(db: Session = Depends(get_db)):
    last_update = (
        db.query(Record.source_id, func.max(Record.ingested_at).label("last_update_at"))
        .group_by(Record.source_id)
        .subquery()
    )
    latest_url_at = (
        db.query(Record.source_id, func.max(Record.ingested_at).label("latest_at"))
        .filter(Record.payload["source_url"].as_string() != None)  # noqa: E711
        .group_by(Record.source_id)
        .subquery()
    )
    rep_url = (
        db.query(
            Record.source_id,
            Record.payload["source_url"].as_string().label("representative_url"),
        )
        .join(
            latest_url_at,
            (Record.source_id == latest_url_at.c.source_id)
            & (Record.ingested_at == latest_url_at.c.latest_at),
        )
        .subquery()
    )
    rows = (
        db.query(Source, last_update.c.last_update_at, rep_url.c.representative_url)
        .outerjoin(last_update, Source.id == last_update.c.source_id)
        .outerjoin(rep_url, Source.id == rep_url.c.source_id)
        .order_by(Source.id)
        .all()
    )
    result = []
    for source, last_update_at, representative_url in rows:
        out = SourceOut.model_validate(source)
        out.last_update_at = last_update_at
        out.representative_url = representative_url
        result.append(out)
    return result


@router.post("/register", response_model=SourceOut, status_code=201)
def register_source(body: SourceCreate, db: Session = Depends(get_db), _key: str = Depends(require_api_key)):
    existing = db.query(Source).filter(Source.slug == body.slug).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Source '{body.slug}' already registered")
    source = Source(**body.model_dump())
    db.add(source)
    db.commit()
    db.refresh(source)
    return source
