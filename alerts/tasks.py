import logging

from celery import shared_task
from django.db import DatabaseError

from alerts.models import Alert
from alerts.services.notification_service import (
    dispatch_alert_notifications,
)

from alerts.services.cleanup_service import cleanup_alerts

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    name="alerts.dispatch_alert_notifications",
    autoretry_for=(DatabaseError, ConnectionError),
    retry_kwargs={"max_retries": 5},
    retry_backoff=True,
)
def dispatch_alert_notifications_task(self, alert_id):
    """
    Background task responsible for dispatching notifications
    for a single alert.

    Responsibilities:
        - Load the alert.
        - Skip if the alert no longer exists.
        - Dispatch notifications.
        - Retry only transient failures.
    """

    logger.info(
        "Starting notification task for alert %s",
        alert_id,
    )

    try:
        alert = Alert.objects.select_related(
            "service",
            "log",
        ).get(pk=alert_id)

    except Alert.DoesNotExist:
        logger.warning(
            "Alert %s no longer exists. Skipping notification.",
            alert_id,
        )
        return

    dispatch_alert_notifications(alert)

    logger.info(
        "Finished notification task for alert %s",
        alert_id,
    )




@shared_task(name="alerts.cleanup")
def cleanup_alerts_task():
    """
    Run all alert cleanup jobs.

    Intended for Celery Beat.
    """

    return cleanup_alerts()