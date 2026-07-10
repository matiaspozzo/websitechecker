from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import scheduler
from app.deps import get_current_user, get_db
from app.models.site import Site
from app.models.silence import Silence
from app.models.user import User
from app.schemas.site import SilenceRequest, SiteCreate, SiteOut, SiteUpdate

router = APIRouter(prefix="/api/sites", tags=["sites"], dependencies=[Depends(get_current_user)])


def _domain_from_url(url: str) -> str:
    hostname = urlparse(url).hostname
    if not hostname:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid URL")
    return hostname


@router.get("", response_model=list[SiteOut])
def list_sites(db: Session = Depends(get_db)) -> list[Site]:
    return db.query(Site).order_by(Site.name).all()


@router.post("", response_model=SiteOut, status_code=status.HTTP_201_CREATED)
def create_site(payload: SiteCreate, db: Session = Depends(get_db)) -> Site:
    site = Site(**payload.model_dump(), expected_domain=_domain_from_url(payload.url))
    db.add(site)
    db.commit()
    db.refresh(site)
    scheduler.reload_site(db, site.id)
    return site


@router.get("/{site_id}", response_model=SiteOut)
def get_site(site_id: int, db: Session = Depends(get_db)) -> Site:
    site = db.get(Site, site_id)
    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")
    return site


@router.put("/{site_id}", response_model=SiteOut)
def update_site(site_id: int, payload: SiteUpdate, db: Session = Depends(get_db)) -> Site:
    site = db.get(Site, site_id)
    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(site, field, value)
    if "url" in updates:
        site.expected_domain = _domain_from_url(site.url)

    db.commit()
    db.refresh(site)
    scheduler.reload_site(db, site.id)
    return site


@router.delete("/{site_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_site(site_id: int, db: Session = Depends(get_db)) -> None:
    site = db.get(Site, site_id)
    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")
    db.delete(site)
    db.commit()
    scheduler.remove_site_jobs(site_id)


@router.post("/{site_id}/pause", response_model=SiteOut)
def pause_site(site_id: int, db: Session = Depends(get_db)) -> Site:
    site = db.get(Site, site_id)
    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")
    site.active = False
    db.commit()
    db.refresh(site)
    scheduler.reload_site(db, site.id)
    return site


@router.post("/{site_id}/resume", response_model=SiteOut)
def resume_site(site_id: int, db: Session = Depends(get_db)) -> Site:
    site = db.get(Site, site_id)
    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")
    site.active = True
    db.commit()
    db.refresh(site)
    scheduler.reload_site(db, site.id)
    return site


@router.post("/{site_id}/check-now", status_code=status.HTTP_202_ACCEPTED)
def check_now(site_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)) -> dict:
    site = db.get(Site, site_id)
    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")

    async def _run() -> None:
        from app.checks.runner import run_all_checks_for_site
        from app.database import SessionLocal

        run_db = SessionLocal()
        try:
            fresh_site = run_db.get(Site, site_id)
            if fresh_site is not None:
                await run_all_checks_for_site(fresh_site, run_db)
        finally:
            run_db.close()

    background_tasks.add_task(_run)
    return {"status": "started"}


@router.post("/{site_id}/silence", response_model=SiteOut)
def silence_site(site_id: int, payload: SilenceRequest, db: Session = Depends(get_db)) -> Site:
    site = db.get(Site, site_id)
    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")
    db.add(Silence(site_id=site_id, until=datetime.now(timezone.utc) + timedelta(hours=payload.hours)))
    db.commit()
    db.refresh(site)
    return site
