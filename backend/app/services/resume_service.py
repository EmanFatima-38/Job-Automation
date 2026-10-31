import uuid

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.client import AIParseError, AIRefusalError
from app.ai.parse_resume import parse_resume
from app.ai.schemas.resume_profile_schema import ResumeProfile
from app.models.resume import Resume
from app.models.user import User
from app.parsers.docx_parser import extract_text_from_docx
from app.parsers.pdf_parser import extract_text_from_pdf
from app.storage.file_storage import save_upload_file

# How many of a resume's AI-suggested target roles get joined into the profile's
# search_keywords. Matches crawl_service.MAX_ROLE_PHRASES - each role becomes a separate
# crawl query per source, so keep these two caps in sync (no point storing a role that the
# crawl will never actually search).
MAX_AUTO_SEARCH_ROLES = 4


class ResumeNotFoundError(Exception):
    pass


def _extract_text(file_path: str, file_type: str) -> str:
    if file_type == "pdf":
        return extract_text_from_pdf(file_path)
    return extract_text_from_docx(file_path)


def _apply_profile_defaults(db: Session, user_id: uuid.UUID, profile: ResumeProfile) -> None:
    """Fill in blank profile fields (Settings page) from the primary resume. Never
    overwrites a value the user already set themselves."""
    user = db.get(User, user_id)
    if user is None:
        return
    # Suggestions are exposed on the parsed CV; explicitly saved preferences are untouched.
    if not user.country and profile.country:
        user.country = profile.country
    if not user.city and profile.city:
        user.city = profile.city
    if not user.search_keywords and profile.target_roles:
        user.search_keywords = ", ".join(profile.target_roles[:MAX_AUTO_SEARCH_ROLES])


def _run_parse(db: Session, resume: Resume) -> Resume:
    resume.parse_status = "parsing"
    db.commit()

    try:
        profile = parse_resume(resume.raw_text)
    except AIRefusalError as e:
        resume.parse_status = "failed"
        resume.parse_error = str(e)
    except AIParseError as e:
        resume.parse_status = "failed"
        resume.parse_error = str(e)
    else:
        resume.structured_profile = profile.model_dump()
        resume.parse_status = "parsed"
        resume.parse_error = None
        if resume.is_primary:
            _apply_profile_defaults(db, resume.user_id, profile)

    db.commit()
    db.refresh(resume)
    return resume


def upload_resume(db: Session, user_id: uuid.UUID, file: UploadFile) -> Resume:
    file_type = "pdf" if (file.filename or "").lower().endswith(".pdf") else "docx"
    file_path = save_upload_file(file)
    raw_text = _extract_text(file_path, file_type)

    is_first_resume = db.scalar(select(Resume.id).where(Resume.user_id == user_id).limit(1)) is None

    resume = Resume(
        user_id=user_id,
        original_filename=file.filename or "resume",
        file_path=file_path,
        file_type=file_type,
        raw_text=raw_text,
        parse_status="pending",
        is_primary=is_first_resume,
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)

    return _run_parse(db, resume)


def get_resume(db: Session, user_id: uuid.UUID, resume_id: uuid.UUID) -> Resume:
    resume = db.scalar(
        select(Resume).where(Resume.id == resume_id, Resume.user_id == user_id)
    )
    if resume is None:
        raise ResumeNotFoundError
    return resume


def list_resumes(db: Session, user_id: uuid.UUID) -> list[Resume]:
    return list(db.scalars(select(Resume).where(Resume.user_id == user_id)))


def reparse_resume(db: Session, user_id: uuid.UUID, resume_id: uuid.UUID) -> Resume:
    resume = get_resume(db, user_id, resume_id)
    return _run_parse(db, resume)


def set_primary_resume(db: Session, user_id: uuid.UUID, resume_id: uuid.UUID) -> Resume:
    resume = get_resume(db, user_id, resume_id)
    db.query(Resume).filter(Resume.user_id == user_id, Resume.id != resume_id).update(
        {"is_primary": False}
    )
    resume.is_primary = True
    db.commit()
    db.refresh(resume)
    return resume


def delete_resume(db: Session, user_id: uuid.UUID, resume_id: uuid.UUID) -> None:
    resume = get_resume(db, user_id, resume_id)
    db.delete(resume)
    db.commit()
