"""Outbound email through the company SMTP relay."""
import smtplib
from email.message import EmailMessage

SMTP_HOST = "smtp.internal.example"


def send(to: str, subject: str, body: str) -> None:
    msg = EmailMessage()
    msg["From"] = "no-reply@portal.example"
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    with smtplib.SMTP(SMTP_HOST, 587, timeout=10) as s:
        s.starttls()
        s.send_message(msg)
