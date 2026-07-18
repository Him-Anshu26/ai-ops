import logging
from datetime import timedelta

from django.utils import timezone

from monitoring.models import Log


logger = logging.getLogger(__name__)


LOG_RETENTION_DAYS = 120


class CleanupOldLogsService:
    """
    Delete monitoring logs older than the configured
    retention period.

    Keeping logs forever will eventually slow queries,
    increase backups and consume unnecessary storage.
    """

    def __call__(self) -> int:

        retention_date = (
            timezone.now()
            - timedelta(days=LOG_RETENTION_DAYS)
        )

        deleted_count, _ = (
            Log.objects.filter(
                created_at__lt=retention_date,
            ).delete()
        )

        logger.info(
            "Deleted %s old monitoring log(s).",
            deleted_count,
        )

        return deleted_count


cleanup_old_logs = CleanupOldLogsService()