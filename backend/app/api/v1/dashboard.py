from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.dashboard import DashboardJobRow, DashboardStats
from app.services.dashboard_service import get_dashboard_jobs, get_stats

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStats)
def read_stats(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> DashboardStats:
    return get_stats(db, current_user.id)


@router.get("/jobs", response_model=list[DashboardJobRow])
def read_jobs(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> list[DashboardJobRow]:
    return get_dashboard_jobs(db, current_user.id)
