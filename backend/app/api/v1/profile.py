from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.profile import ProfileRead, ProfileUpdate
from app.services.profile_service import update_profile

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("", response_model=ProfileRead)
def read_profile(current_user: User = Depends(get_current_user)) -> ProfileRead:
    return current_user


@router.patch("", response_model=ProfileRead)
def patch_profile(
    data: ProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProfileRead:
    return update_profile(db, current_user, data)
