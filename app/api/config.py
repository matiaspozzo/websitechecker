from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.deps import get_current_user, get_db
from app.models.config import GlobalConfig
from app.models.suspicious_pattern import SuspiciousPattern
from app.scheduler import reload_digest_job
from app.schemas.config import (
    GlobalConfigOut,
    GlobalConfigUpdate,
    SuspiciousPatternCreate,
    SuspiciousPatternOut,
    SuspiciousPatternUpdate,
)

router = APIRouter(prefix="/api/config", tags=["config"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=GlobalConfigOut)
def get_config(db: Session = Depends(get_db)) -> GlobalConfig:
    config = db.get(GlobalConfig, 1)
    if config is None:
        config = GlobalConfig(id=1)
        db.add(config)
        db.commit()
        db.refresh(config)
    return config


@router.put("", response_model=GlobalConfigOut)
def update_config(payload: GlobalConfigUpdate, db: Session = Depends(get_db)) -> GlobalConfig:
    config = db.get(GlobalConfig, 1)
    if config is None:
        config = GlobalConfig(id=1)
        db.add(config)

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(config, field, value)

    db.commit()
    db.refresh(config)
    reload_digest_job(db)
    return config


@router.get("/patterns", response_model=list[SuspiciousPatternOut])
def list_patterns(db: Session = Depends(get_db)) -> list[SuspiciousPattern]:
    return db.query(SuspiciousPattern).order_by(SuspiciousPattern.id).all()


@router.post("/patterns", response_model=SuspiciousPatternOut, status_code=status.HTTP_201_CREATED)
def create_pattern(payload: SuspiciousPatternCreate, db: Session = Depends(get_db)) -> SuspiciousPattern:
    pattern = SuspiciousPattern(**payload.model_dump())
    db.add(pattern)
    db.commit()
    db.refresh(pattern)
    return pattern


@router.put("/patterns/{pattern_id}", response_model=SuspiciousPatternOut)
def update_pattern(pattern_id: int, payload: SuspiciousPatternUpdate, db: Session = Depends(get_db)) -> SuspiciousPattern:
    pattern = db.get(SuspiciousPattern, pattern_id)
    if pattern is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pattern not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(pattern, field, value)
    db.commit()
    db.refresh(pattern)
    return pattern


@router.delete("/patterns/{pattern_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_pattern(pattern_id: int, db: Session = Depends(get_db)) -> None:
    pattern = db.get(SuspiciousPattern, pattern_id)
    if pattern is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pattern not found")
    db.delete(pattern)
    db.commit()
