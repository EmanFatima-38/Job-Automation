import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.models.crawl_run import CrawlRun
from app.models.job import Job
from app.models.opportunity_delivery import OpportunityDelivery
from app.schemas.discovery import SearchRequest
from app.schemas.crawl import CrawlRunRead
from app.services.crawl_service import enqueue_search, list_crawl_runs, CrawlAlreadyRunningError
from app.services.portfolio_service import refresh_portfolio
from app.services.job_quality import now_iso
from sqlalchemy import select

router = APIRouter(tags=['discovery'])


@router.post('/search', response_model=CrawlRunRead, status_code=202)
def search(data: SearchRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    try:
        return enqueue_search(db, user, data.intent, data.force)
    except CrawlAlreadyRunningError as exc:
        raise HTTPException(409, str(exc))


@router.get('/search/history', response_model=list[CrawlRunRead])
def history(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return list_crawl_runs(db, user.id)


@router.post('/search/{run_id}/cancel', response_model=CrawlRunRead)
def cancel(run_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    run = db.scalar(select(CrawlRun).where(CrawlRun.id == run_id, CrawlRun.user_id == user.id))
    if not run:
        raise HTTPException(404, 'Search not found')
    if run.status in ('queued', 'running'):
        run.status = 'cancelled' if run.status == 'queued' else 'cancelling'
        if run.status == 'cancelled':
            run.finished_at = datetime.now(timezone.utc)
        db.commit()
    return run


@router.post('/profile/portfolio/refresh')
def portfolio(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return refresh_portfolio(db, user)


@router.post('/jobs/{job_id}/viewed')
def viewed(job_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    job = db.scalar(select(Job).where(Job.id == job_id, Job.user_id == user.id))
    if not job:
        raise HTTPException(404, 'Job not found')
    job.research = {**(job.research or {}), 'viewed_at': now_iso()}
    db.commit()
    return {'ok': True}


@router.get('/notifications/history')
def notifications(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.scalars(select(OpportunityDelivery).where(OpportunityDelivery.user_id == user.id).order_by(OpportunityDelivery.created_at.desc()).limit(50))
    return [{'job_id': row.job_id, 'status': row.status, 'created_at': row.created_at, 'error': row.error} for row in rows]
