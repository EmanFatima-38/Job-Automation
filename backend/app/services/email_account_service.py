import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.crypto import encrypt_secret
from app.models.email_account import EmailAccount
from app.schemas.email_account import EmailAccountCreate, EmailTestResult
from app.services.email_service import EmailSendError, send_email


class EmailAccountNotFoundError(Exception):
    pass


def get_email_account(db: Session, user_id: uuid.UUID) -> EmailAccount | None:
    return db.scalar(select(EmailAccount).where(EmailAccount.user_id == user_id))


def upsert_email_account(db: Session, user_id: uuid.UUID, data: EmailAccountCreate) -> EmailAccount:
    account = get_email_account(db, user_id)
    encrypted_password = encrypt_secret(data.smtp_password)

    if account is None:
        account = EmailAccount(
            user_id=user_id,
            smtp_host=data.smtp_host,
            smtp_port=data.smtp_port,
            smtp_username=data.smtp_username,
            encrypted_password=encrypted_password,
            from_name=data.from_name,
            from_email=data.from_email,
            use_tls=data.use_tls,
        )
        db.add(account)
    else:
        account.smtp_host = data.smtp_host
        account.smtp_port = data.smtp_port
        account.smtp_username = data.smtp_username
        account.encrypted_password = encrypted_password
        account.from_name = data.from_name
        account.from_email = data.from_email
        account.use_tls = data.use_tls
        account.last_tested_at = None
        account.last_test_ok = None

    db.commit()
    db.refresh(account)
    return account


def delete_email_account(db: Session, user_id: uuid.UUID) -> None:
    account = get_email_account(db, user_id)
    if account is None:
        raise EmailAccountNotFoundError
    db.delete(account)
    db.commit()


def send_test_email(db: Session, user_id: uuid.UUID) -> EmailTestResult:
    account = get_email_account(db, user_id)
    if account is None:
        raise EmailAccountNotFoundError

    try:
        send_email(
            account,
            to_email=account.from_email,
            subject="ApplyPilot test email",
            body="This is a test email from ApplyPilot confirming your connected account can send mail.",
        )
    except EmailSendError as e:
        account.last_tested_at = datetime.now(timezone.utc)
        account.last_test_ok = False
        db.commit()
        return EmailTestResult(ok=False, error=str(e))

    account.last_tested_at = datetime.now(timezone.utc)
    account.last_test_ok = True
    db.commit()
    return EmailTestResult(ok=True)
