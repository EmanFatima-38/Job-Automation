from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.crawl import CrawlRunRead
from app.services.crawl_service import CrawlAlreadyRunningError, CrawlNotEnabledError, list_crawl_runs, run_crawl_now

router = APIRouter(prefix="/crawl", tags=["crawl"])


@router.post("/run", response_model=CrawlRunRead)
def trigger_crawl(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> CrawlRunRead:
    try:
        return run_crawl_now(db, current_user)
    except (CrawlNotEnabledError, CrawlAlreadyRunningError) as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/runs", response_model=list[CrawlRunRead])
def get_crawl_runs(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> list[CrawlRunRead]:
    return list_crawl_runs(db, current_user.id)
