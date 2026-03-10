from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Source
from ..schemas import SourceCreate, SourceOut

router = APIRouter(prefix="/api/v1/sources", tags=["sources"])


@router.get("", response_model=list[SourceOut])
def list_sources(db: Session = Depends(get_db)):
    return db.query(Source).order_by(Source.id).all()


@router.post("/register", response_model=SourceOut, status_code=201)
def register_source(body: SourceCreate, db: Session = Depends(get_db)):
    existing = db.query(Source).filter(Source.slug == body.slug).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Source '{body.slug}' already registered")
    source = Source(**body.model_dump())
    db.add(source)
    db.commit()
    db.refresh(source)
    return source
