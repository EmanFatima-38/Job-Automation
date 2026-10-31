import smtplib
from email.message import EmailMessage

from app.core.crypto import decrypt_secret
from app.models.email_account import EmailAccount


class EmailSendError(Exception):
    pass


def send_email(account: EmailAccount, to_email: str, subject: str, body: str) -> None:
    message = EmailMessage()
    from_header = f"{account.from_name} <{account.from_email}>" if account.from_name else account.from_email
    message["From"] = from_header
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body)

    password = decrypt_secret(account.encrypted_password)

    try:
        with smtplib.SMTP(account.smtp_host, account.smtp_port, timeout=15) as smtp:
            if account.use_tls:
                smtp.starttls()
            smtp.login(account.smtp_username, password)
            smtp.send_message(message)
    except (smtplib.SMTPException, OSError, ValueError) as e:
        raise EmailSendError(str(e)) from e
