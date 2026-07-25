import secrets
import hashlib
from django.core.mail import send_mail
from django.conf import settings

import logging

logger = logging.getLogger(__name__)


def generate_token():
    return secrets.token_urlsafe(32)

def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()

# def send_email(subject: str,message: str,recipient_list: list[str],) -> None:

#     # This Will be Used in Production, For Now We Just Print the Email Content to the Console for Debugging
#     send_mail(subject=subject, message=message, 
#               from_email=settings.DEFAULT_FROM_EMAIL, 
#               recipient_list=recipient_list, fail_silently=False, 
#               timeout=20,
#             )


#     if settings.DEBUG:
#         # This is for the Development Environment, to see the email content in the console
#         logger.debug("\n========== RAW EMAIL ==========")
#         logger.debug("TO: %s", recipient_list)
#         logger.debug("SUBJECT: %s", subject)
#         logger.debug("MESSAGE: %s", message)
#         logger.debug("================================\n")


def send_email(subject, message, recipient_list):

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipient_list,
            fail_silently=False,
        )

    except Exception:
        logger.exception("EMAIL SENDING FAILED")
        raise



def build_verification_link(token):
    return f"{settings.FRONTEND_URL}/verify-email/?token={token}"

def build_reset_link(token):
    return f"{settings.FRONTEND_URL}/reset-password/?token={token}"
