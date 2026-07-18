import logging

from alerts.models import Alert


logger = logging.getLogger(__name__)


def send_slack_notification(alert: Alert) -> None:
    """
    Placeholder for Slack notification delivery.

    This function will be implemented after production deployment.

    Future implementation:
        - Read Slack webhook URL from settings.
        - Build Slack message payload.
        - Send message using Slack Incoming Webhooks.
        - Handle retries and transient failures.
        - Log request/response details.
    """

    logger.info(
        "Slack notification placeholder reached for alert %s",
        alert.id,
    )

    # Placeholder.
    return None