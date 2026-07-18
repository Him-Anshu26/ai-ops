import logging

from celery import shared_task
from django.core.exceptions import ObjectDoesNotExist

from monitoring.models import Log
from monitoring.services.alert_service import process_log_for_alerts

from monitoring.services.cleanup_service import (
    cleanup_old_logs as cleanup_old_logs_service,
)

logger = logging.getLogger(__name__)


@shared_task(
    autoretry_for=(ConnectionError,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    retry_kwargs={"max_retries": 5},
    name="monitoring.process_log_for_alerts",
)
def process_log_for_alerts_task(log_id: int) -> None:
    """
    Background task that processes a newly created log and evaluates
    alert rules.

    Args:
        log_id (int): Primary key of the monitoring log.

    Raises:
        Retry: For configured transient failures.

    Retries:
        - ConnectionError
    """

    
    try:
        log = Log.objects.get(pk=log_id)

    except ObjectDoesNotExist:
        logger.warning(
            "Alert processing skipped. Log %s does not exist.",
            log_id,
        )
        return

    logger.info(
        "Starting alert processing for log %s",
        log.id,
    )

    process_log_for_alerts(log)

    logger.info(
        "Finished alert processing for log %s",
        log.id,
    )


@shared_task
def cleanup_old_logs():
    """
    Delete old monitoring logs.

    Intended for Celery Beat.
    """

    deleted_count = cleanup_old_logs_service()

    logger.info(
        "Deleted %s old monitoring log(s).",
        deleted_count,
    )

    return deleted_count


@shared_task
def cleanup_monitoring():
    """
    Run all monitoring cleanup jobs.

    Celery Beat only needs to schedule this task.
    """

    logger.info(
        "Starting monitoring cleanup."
    )

    logs = cleanup_old_logs()

    logger.info(
        "Monitoring cleanup finished. Logs=%s",
        logs,
    )

    return {
        "logs": logs,
    }




