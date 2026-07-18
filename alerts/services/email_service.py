import logging

from django.conf import settings
from django.core.mail import send_mail

from alerts.models import Alert


logger = logging.getLogger(__name__)


def send_alert_email(alert: Alert) -> bool:
    """
    Send an email notification for an alert.

    Responsibilities:
        1. Build the email subject.
        2. Build the email body.
        3. Send the email.
        4. Log success or failure.

    Returns:
        True if the email was sent successfully.

    Raises:
        Exception:
            Re-raised so Celery can retry transient failures.
    """

    logger.info(
        "Preparing email notification for alert %s",
        alert.id,
    )

    subject = _build_subject(alert)
    body = _build_body(alert)

    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=settings.ALERT_EMAIL_RECIPIENTS,
            fail_silently=False,
        )

        logger.info(
            "Email notification sent successfully for alert %s",
            alert.id,
        )

        return True

    except Exception:
        logger.exception(
            "Failed to send email notification for alert %s",
            alert.id,
        )
        raise


def _build_subject(alert: Alert) -> str:
    """
    Build the email subject.
    """

    return (
        f"[{alert.severity.upper()}] "
        f"{alert.get_alert_type_display()} - "
        f"{alert.service.name}"
    )


def _build_body(alert: Alert) -> str:
    """
    Build the plain-text email body.
    """

    return f"""
            AI Ops Monitoring Alert

            Alert ID:
            {alert.id}

            Service:
            {alert.service.name}

            Alert Type:
            {alert.get_alert_type_display()}

            Severity:
            {alert.get_severity_display()}

            Status:
            {alert.get_status_display()}

            Message:
            {alert.message}

            Trigger Count:
            {alert.trigger_count}

            Created At:
            {alert.created_at}

            Last Triggered:
            {alert.last_triggered_at}
            """.strip()