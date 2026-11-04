from __future__ import annotations

import smtplib
from email.message import EmailMessage

from app.config import get_settings


class EmailService:
    def send(self, recipient: str, subject: str, text_body: str) -> None:
        settings = get_settings()
        message = EmailMessage()
        message["From"] = settings.email_from
        message["To"] = recipient
        message["Subject"] = subject
        message.set_content(text_body)

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
            if settings.smtp_starttls:
                smtp.starttls()
            if settings.smtp_username:
                smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.send_message(message)


def get_email_service() -> EmailService:
    return EmailService()
