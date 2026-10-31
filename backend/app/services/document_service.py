import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.generate_content import generate_cover_letter, generate_resume_bullets
from app.ai.schemas.resume_profile_schema import ResumeProfile
from app.config import get_settings
from app.models.generated_document import GeneratedDocument
from app.models.job import Job
from app.models.resume import Resume
from app.schemas.document import DocumentCreate
from app.services.job_mapping import job_to_extraction

settings = get_settings()


class DocumentInputNotReadyError(Exception):
    pass


class DocumentNotFoundError(Exception):
    pass


def generate_document(
    db: Session, user_id: uuid.UUID, job_id: uuid.UUID, data: DocumentCreate
) -> GeneratedDocument:
    job = db.scalar(select(Job).where(Job.id == job_id, Job.user_id == user_id))
    resume = db.scalar(
        select(Resume).where(Resume.id == data.resume_id, Resume.user_id == user_id)
    )

    if job is None or resume is None:
        raise DocumentInputNotReadyError("Job or resume not found")
    if job.extraction_status != "extracted":
        raise DocumentInputNotReadyError("Job has not been successfully extracted yet")
    if resume.parse_status != "parsed":
        raise DocumentInputNotReadyError("Resume has not been successfully parsed yet")

    profile = ResumeProfile(**resume.structured_profile)
    job_extraction = job_to_extraction(job)

    if data.doc_type == "cover_letter":
        content = generate_cover_letter(profile, job_extraction)
    else:
        bullets = generate_resume_bullets(profile, job_extraction)
        content = "\n".join(f"- {b}" for b in bullets)

    document = GeneratedDocument(
        job_id=job_id,
        resume_id=data.resume_id,
        doc_type=data.doc_type,
        content=content,
        model_used=settings.generation_model,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


def list_documents(db: Session, user_id: uuid.UUID, job_id: uuid.UUID) -> list[GeneratedDocument]:
    return list(
        db.scalars(
            select(GeneratedDocument)
            .join(Job, GeneratedDocument.job_id == Job.id)
            .where(GeneratedDocument.job_id == job_id, Job.user_id == user_id)
        )
    )


def get_document(db: Session, user_id: uuid.UUID, document_id: uuid.UUID) -> GeneratedDocument:
    document = db.scalar(
        select(GeneratedDocument)
        .join(Job, GeneratedDocument.job_id == Job.id)
        .where(GeneratedDocument.id == document_id, Job.user_id == user_id)
    )
    if document is None:
        raise DocumentNotFoundError
    return document
