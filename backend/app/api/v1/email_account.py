from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.email_account import EmailAccountCreate, EmailAccountRead, EmailTestResult
from app.services.email_account_service import (
    EmailAccountNotFoundError,
    delete_email_account,
    get_email_account,
    send_test_email,
    upsert_email_account,
)

router = APIRouter(prefix="/email-account", tags=["email-account"])


@router.get("", response_model=EmailAccountRead)
def read_email_account(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> EmailAccountRead:
    account = get_email_account(db, current_user.id)
    if account is None:
        raise HTTPException(status_code=404, detail="No email account connected")
    return account


@router.put("", response_model=EmailAccountRead)
def save_email_account(
    data: EmailAccountCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EmailAccountRead:
    return upsert_email_account(db, current_user.id, data)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def remove_email_account(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> None:
    try:
        delete_email_account(db, current_user.id)
    except EmailAccountNotFoundError:
        raise HTTPException(status_code=404, detail="No email account connected")


@router.post("/test", response_model=EmailTestResult)
def test_email_account(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> EmailTestResult:
    try:
        return send_test_email(db, current_user.id)
    except EmailAccountNotFoundError:
        raise HTTPException(status_code=404, detail="No email account connected")
