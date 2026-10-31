import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.ai.client import AIParseError, AIRefusalError
from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.document import DocumentCreate, DocumentRead
from app.services.document_service import (
    DocumentInputNotReadyError,
    DocumentNotFoundError,
    generate_document,
    get_document,
    list_documents,
)

router = APIRouter(tags=["documents"])


@router.post("/jobs/{job_id}/documents", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
def create_document(
    job_id: uuid.UUID,
    data: DocumentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DocumentRead:
    try:
        return generate_document(db, current_user.id, job_id, data)
    except DocumentInputNotReadyError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except AIRefusalError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except AIParseError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/jobs/{job_id}/documents", response_model=list[DocumentRead])
def read_documents(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[DocumentRead]:
    return list_documents(db, current_user.id, job_id)


@router.get("/documents/{document_id}", response_model=DocumentRead)
def read_document(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DocumentRead:
    try:
        return get_document(db, current_user.id, document_id)
    except DocumentNotFoundError:
        raise HTTPException(status_code=404, detail="Document not found")
