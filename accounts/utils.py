import secrets
import hashlib
from django.core.mail import send_mail
from django.conf import settings


def generate_token():
    return secrets.token_urlsafe(32)

def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()

def send_email(subject: str,message: str,recipient_list: list[str],) -> None:

    # This Will be Used in Production, For Now We Just Print the Email Content to the Console for Debugging
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, recipient_list, fail_silently=False)


    if settings.DEBUG:
        # This is for the Development Environment, to see the email content in the console
        print("\n========== RAW EMAIL ==========")
        print("TO:", recipient_list)
        print("SUBJECT:", subject)
        print(message)
        print("================================\n")



def build_verification_link(token):
    return f"{settings.FRONTEND_URL}/verify-email/?token={token}"

def build_reset_link(token):
    return f"{settings.FRONTEND_URL}/reset-password/?token={token}"
