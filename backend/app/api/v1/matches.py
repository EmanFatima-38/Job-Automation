import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.ai.client import AIParseError, AIRefusalError
from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.match import MatchRead
from app.services.match_service import (
    MatchInputNotReadyError,
    MatchNotFoundError,
    compute_match,
    get_match,
    list_matches,
)

router = APIRouter(tags=["matches"])


@router.post("/jobs/{job_id}/match", response_model=MatchRead)
def create_match(
    job_id: uuid.UUID,
    resume_id: uuid.UUID = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MatchRead:
    try:
        return compute_match(db, current_user.id, job_id, resume_id)
    except MatchInputNotReadyError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except AIRefusalError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except AIParseError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/jobs/{job_id}/match", response_model=MatchRead)
def read_match(
    job_id: uuid.UUID,
    resume_id: uuid.UUID = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MatchRead:
    try:
        return get_match(db, current_user.id, job_id, resume_id)
    except MatchNotFoundError:
        raise HTTPException(status_code=404, detail="Match not found")


@router.get("/matches", response_model=list[MatchRead])
def get_matches(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> list[MatchRead]:
    return list_matches(db, current_user.id)
