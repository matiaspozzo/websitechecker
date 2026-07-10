from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.deps import get_current_user, get_db
from app.models.config import GlobalConfig
from app.models.suspicious_pattern import SuspiciousPattern
from app.models.trusted_domain import TrustedDomain
from app.scheduler import reload_digest_job
from app.schemas.config import (
    GlobalConfigOut,
    GlobalConfigUpdate,
    SuspiciousPatternCreate,
    SuspiciousPatternOut,
    SuspiciousPatternUpdate,
    TrustedDomainCreate,
    TrustedDomainOut,
    TrustedDomainUpdate,
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


@router.get("/trusted-domains", response_model=list[TrustedDomainOut])
def list_trusted_domains(db: Session = Depends(get_db)) -> list[TrustedDomain]:
    return db.query(TrustedDomain).order_by(TrustedDomain.domain).all()


@router.post("/trusted-domains", response_model=TrustedDomainOut, status_code=status.HTTP_201_CREATED)
def create_trusted_domain(payload: TrustedDomainCreate, db: Session = Depends(get_db)) -> TrustedDomain:
    existing = db.query(TrustedDomain).filter(TrustedDomain.domain == payload.domain).first()
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Domain already trusted")
    domain = TrustedDomain(**payload.model_dump())
    db.add(domain)
    db.commit()
    db.refresh(domain)
    return domain


@router.put("/trusted-domains/{domain_id}", response_model=TrustedDomainOut)
def update_trusted_domain(domain_id: int, payload: TrustedDomainUpdate, db: Session = Depends(get_db)) -> TrustedDomain:
    domain = db.get(TrustedDomain, domain_id)
    if domain is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trusted domain not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(domain, field, value)
    db.commit()
    db.refresh(domain)
    return domain


@router.delete("/trusted-domains/{domain_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_trusted_domain(domain_id: int, db: Session = Depends(get_db)) -> None:
    domain = db.get(TrustedDomain, domain_id)
    if domain is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trusted domain not found")
    db.delete(domain)
    db.commit()
