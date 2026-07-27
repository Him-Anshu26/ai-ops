import secrets
import hashlib
from django.core.mail import send_mail
from django.conf import settings
import resend

import logging

logger = logging.getLogger(__name__)


def generate_token():
    return secrets.token_urlsafe(32)

def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()

def send_email(
    subject: str,
    message: str,
    recipient_list: list[str],
) -> None:
    """
    Send email using the Resend API.

    Raises:
        Exception:
            Re-raises any Resend exception so the caller
            can decide how to handle failures.
    """

    resend.api_key = settings.RESEND_API_KEY

    params = {
        "from": settings.DEFAULT_FROM_EMAIL,
        "to": recipient_list,
        "subject": subject,
        "text": message,
    }

    try:

        response = resend.Emails.send(params)

        logger.info(
            "Email sent successfully",
            extra={
                "provider": "resend",
                "recipient_count": len(recipient_list),
                "subject": subject,
                "response": response,
            },
        )

    except Exception:

        logger.exception(
            "Failed to send email using Resend",
            extra={
                "provider": "resend",
                "recipient_count": len(recipient_list),
                "subject": subject,
            },
        )

        raise



def build_verification_link(token):
    return f"{settings.FRONTEND_URL}/verify-email/?token={token}"

def build_reset_link(token):
    return f"{settings.FRONTEND_URL}/reset-password/?token={token}"
