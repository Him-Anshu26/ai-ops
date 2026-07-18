import logging

from django.conf import settings

from alerts.models import Alert
from alerts.services.email_service import send_alert_email
from alerts.services.slack_service import send_slack_notification


logger = logging.getLogger(__name__)


def dispatch_alert_notifications(alert: Alert) -> None:
    """
    Dispatch notifications for a newly created or updated alert.

    Responsibilities:
        - Orchestrate notification providers.
        - Keep providers isolated from each other.
        - Log notification flow.
        - Never interrupt alert processing if a provider fails.

    Notification providers:
        - Email
        - Slack (placeholder)
        - Future:
            - Microsoft Teams
            - Discord
            - SMS
            - Webhooks
            - PagerDuty
    """

    logger.info(
        "Starting notification dispatch for alert %s",
        alert.id,
    )

    # Email Notifications
    if getattr(settings, "EMAIL_NOTIFICATIONS_ENABLED", False):
        try:
            logger.info(
                "Dispatching email notification for alert %s",
                alert.id,
            )

            send_alert_email(alert)

            logger.info(
                "Email notification dispatched for alert %s",
                alert.id,
            )

        except Exception:
            logger.exception(
                "Failed to send email notification for alert %s",
                alert.id,
            )

    else:
        logger.info(
            "Email notifications are disabled.",
        )


    # Slack Notifications (Placeholder)
    if getattr(settings, "SLACK_NOTIFICATIONS_ENABLED", False):
        try:
            logger.info(
                "Dispatching Slack notification for alert %s",
                alert.id,
            )

            send_slack_notification(alert)

            logger.info(
                "Slack notification dispatched for alert %s",
                alert.id,
            )

        except Exception:
            logger.exception(
                "Failed to send Slack notification for alert %s",
                alert.id,
            )

    else:
        logger.info(
            "Slack notifications are disabled.",
        )

    logger.info(
        "Finished notification dispatch for alert %s",
        alert.id,
    )