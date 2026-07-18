import logging
from datetime import timedelta

from django.utils import timezone

from alerts.models import Alert, AlertStatus


logger = logging.getLogger(__name__)


# Retention period for resolved alerts
RESOLVED_ALERT_RETENTION_DAYS = 90


# Cleanup resolved alerts
class CleanupResolvedAlertsService:
    """
    Delete resolved alerts older than the configured
    retention period.

    This keeps the alerts table from growing indefinitely.
    """

    def __call__(self) -> int:

        # Calculate retention cutoff
        retention_date = timezone.now() - timedelta(
            days=RESOLVED_ALERT_RETENTION_DAYS,
        )

        # Delete old resolved alerts
        deleted_count, _ = Alert.objects.filter(
            status=AlertStatus.RESOLVED,
            resolved_at__lt=retention_date,
        ).delete()

        logger.info(
            "Deleted %s resolved alert(s).",
            deleted_count,
        )

        return deleted_count


# Service instance
cleanup_resolved_alerts = CleanupResolvedAlertsService()


# Cleanup alerts
class CleanupAlertsService:
    """
    Run all alert cleanup services.

    Acts as a single entry point for Celery Beat.
    """

    def __call__(self) -> dict:

        logger.info("Starting alerts cleanup.")

        resolved_alerts = cleanup_resolved_alerts()

        logger.info(
            (
                "Alerts cleanup completed. "
                "Resolved Alerts=%s"
            ),
            resolved_alerts,
        )

        return {
            "resolved_alerts": resolved_alerts,
        }


# Service instance
cleanup_alerts = CleanupAlertsService()