import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.resume import ResumeRead, ResumeUpdate
from app.services.resume_service import (
    ResumeNotFoundError,
    delete_resume,
    get_resume,
    list_resumes,
    reparse_resume,
    set_primary_resume,
    upload_resume,
)

router = APIRouter(prefix="/resumes", tags=["resumes"])


@router.post("", response_model=ResumeRead, status_code=status.HTTP_201_CREATED)
def create_resume(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ResumeRead:
    if not (file.filename or "").lower().endswith((".pdf", ".docx")):
        raise HTTPException(status_code=400, detail="Only PDF and DOCX files are supported")
    return upload_resume(db, current_user.id, file)


@router.get("", response_model=list[ResumeRead])
def get_resumes(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> list[ResumeRead]:
    return list_resumes(db, current_user.id)


@router.get("/{resume_id}", response_model=ResumeRead)
def get_resume_by_id(
    resume_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ResumeRead:
    try:
        return get_resume(db, current_user.id, resume_id)
    except ResumeNotFoundError:
        raise HTTPException(status_code=404, detail="Resume not found")


@router.patch("/{resume_id}", response_model=ResumeRead)
def update_resume(
    resume_id: uuid.UUID,
    data: ResumeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ResumeRead:
    try:
        if data.is_primary:
            return set_primary_resume(db, current_user.id, resume_id)
        return get_resume(db, current_user.id, resume_id)
    except ResumeNotFoundError:
        raise HTTPException(status_code=404, detail="Resume not found")


@router.post("/{resume_id}/reparse", response_model=ResumeRead)
def reparse(
    resume_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ResumeRead:
    try:
        return reparse_resume(db, current_user.id, resume_id)
    except ResumeNotFoundError:
        raise HTTPException(status_code=404, detail="Resume not found")


@router.delete("/{resume_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_resume(
    resume_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    try:
        delete_resume(db, current_user.id, resume_id)
    except ResumeNotFoundError:
        raise HTTPException(status_code=404, detail="Resume not found")
