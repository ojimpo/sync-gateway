from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Run, Source
from ..schemas import RunCreate, RunPatch, RunOut

router = APIRouter(prefix="/api/v1/runs", tags=["runs"])


@router.get("", response_model=list[RunOut])
def list_runs(limit: int = 100, db: Session = Depends(get_db)):
    return db.query(Run).order_by(Run.started_at.desc()).limit(limit).all()


@router.post("", response_model=RunOut, status_code=201)
def create_run(body: RunCreate, db: Session = Depends(get_db)):
    source = db.get(Source, body.source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    run = Run(source_id=body.source_id, status="running")
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


@router.patch("/{run_id}", response_model=RunOut)
def finish_run(run_id: int, body: RunPatch, db: Session = Depends(get_db)):
    run = db.get(Run, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    run.status = body.status
    run.finished_at = datetime.now(timezone.utc)
    run.records_ingested = body.records_ingested
    run.records_failed = body.records_failed
    run.error_message = body.error_message
    db.commit()
    db.refresh(run)
    return run
