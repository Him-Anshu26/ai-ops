import logging

from celery import shared_task

from accounts.services import (
    cleanup_expired_verification_tokens as cleanup_expired_verification_tokens_service,
    cleanup_expired_password_reset_tokens as cleanup_expired_password_reset_tokens_service,
    cleanup_inactive_sessions as cleanup_inactive_sessions_service,
)


logger = logging.getLogger(__name__)


@shared_task
def cleanup_expired_email_verification_tokens():
    """
    Delete expired email verification tokens.

    Intended for Celery Beat.
    """

    deleted_count = (
        cleanup_expired_verification_tokens_service()
    )

    logger.info(
        "Deleted %s expired email verification token(s).",
        deleted_count,
    )

    return deleted_count


@shared_task
def cleanup_expired_password_reset_tokens():
    """
    Delete expired password reset tokens.

    Intended for Celery Beat.
    """

    deleted_count = (
        cleanup_expired_password_reset_tokens_service()
    )

    logger.info(
        "Deleted %s expired password reset token(s).",
        deleted_count,
    )

    return deleted_count


@shared_task
def cleanup_inactive_sessions():
    """
    Remove old inactive user sessions.

    Intended for Celery Beat.
    """

    deleted_count = (
        cleanup_inactive_sessions_service()
    )

    logger.info(
        "Deleted %s inactive session(s).",
        deleted_count,
    )

    return deleted_count


@shared_task
def cleanup_accounts():
    """
    Run all account cleanup jobs.

    Celery Beat only needs to schedule this task.
    """

    logger.info("Starting accounts cleanup.")

    email_tokens = (
        cleanup_expired_email_verification_tokens()
    )

    password_tokens = (
        cleanup_expired_password_reset_tokens()
    )

    sessions = (
        cleanup_inactive_sessions()
    )

    logger.info(
        (
            "Accounts cleanup finished. "
            "Email Tokens=%s, "
            "Password Reset Tokens=%s, "
            "Sessions=%s"
        ),
        email_tokens,
        password_tokens,
        sessions,
    )

    return {
        "email_verification_tokens": email_tokens,
        "password_reset_tokens": password_tokens,
        "inactive_sessions": sessions,
    }