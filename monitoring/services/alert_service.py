from datetime import timedelta
from django.utils import timezone
from django.db import transaction, IntegrityError
from django.db.models import F


from alerts.models import Alert, AlertType, AlertStatus, AlertSeverity
from monitoring.models import Log, LogStatus

from alerts.tasks import dispatch_alert_notifications_task


import logging

logger = logging.getLogger(__name__)


ERROR_STATUS_CODE_THRESHOLD = 500
LATENCY_THRESHOLD = 1000  # ms
ALERT_COOLDOWN_SECONDS = 30


def _build_alert_key(alert_type, log):
    service_id = log.service_id

    if alert_type == AlertType.ERROR:
        return f"error:{service_id}:{log.status_code or 'unknown'}"

    if alert_type == AlertType.HIGH_LATENCY:
        if log.response_time_ms > 5000:
            bucket = "very_high"
        elif log.response_time_ms > 2000:
            bucket = "high"
        else:
            bucket = "medium"

        return f"latency:{service_id}:{bucket}"

    if alert_type == AlertType.DOWNTIME:
        return f"downtime:{service_id}"

    return f"{alert_type}:{service_id}"



def process_log_for_alerts(log: Log):
    """
    Main entry point for alert processing.

    Responsibilities:
        1. Determine which alert rules match the incoming log.
        2. Process each matching rule.
        3. Queue notifications (placeholder for future integrations).

    This function intentionally contains no business logic.
    It only orchestrates the workflow.
    """

    logger.info(
        "Starting alert processing for log %s",
        log.id,
    )



    matching_rules = _get_matching_rules(log)

    logger.info(
        "Found %s matching alert rule(s) for log %s",
        len(matching_rules),
        log.id,
    )

    if not matching_rules:
        logger.info(
            "No alert rules matched for log %s",
            log.id,
        )
        return

    for rule in matching_rules:
        logger.info(
            "Processing %s rule for log %s",
            rule["type"],
            log.id,
        )

        alert = _process_rule(log, rule)

        if alert:
            _queue_notifications(alert)



    logger.info(
        "Finished alert processing for log %s",
        log.id,
    )


def _get_matching_rules(log: Log):
    """
    Evaluate the incoming log against all alert rules.

    Returns:
        list[dict]
    """

    rules = []

    # ERROR RULE    
    if (
        log.status == LogStatus.ERROR
        or (
            log.status_code
            and log.status_code >= ERROR_STATUS_CODE_THRESHOLD
        )
    ):
        rules.append(
            {
                "type": AlertType.ERROR,
            }
        )


    # HIGH LATENCY RULE
    if (
        log.response_time_ms
        and log.response_time_ms > LATENCY_THRESHOLD
    ):
        rules.append(
            {
                "type": AlertType.HIGH_LATENCY,
            }
        )

    return rules


def _process_rule(log: Log, rule):
    """
    Process one matched alert rule.

    Responsible for:
        • determining severity
        • generating alert key
        • building alert message
        • delegating persistence
    """

    alert_type = rule["type"]

    if alert_type == AlertType.ERROR:

        severity = _determine_error_severity(log)

        alert_key = _build_alert_key(
            AlertType.ERROR,
            log,
        )

        message = (
            f"Error {log.status_code or ''} "
            f"in {log.service.name}"
        ).strip()

    elif alert_type == AlertType.HIGH_LATENCY:

        severity = (
            AlertSeverity.HIGH
            if log.response_time_ms > 3000
            else AlertSeverity.MEDIUM
        )

        alert_key = _build_alert_key(
            AlertType.HIGH_LATENCY,
            log,
        )

        message = (
            f"High latency "
            f"({log.response_time_ms} ms)"
        )

    else:
        return None

    alert = _create_or_update_alert(
        service=log.service,
        log=log,
        alert_type=alert_type,
        severity=severity,
        alert_key=alert_key,
        message=message,
    )

    if alert:
        logger.info(
            "Successfully processed %s alert for log %s (alert=%s)",
            alert_type,
            log.id,
            alert.id,
        )

    return alert


def _queue_notifications(alert):
    """
    Placeholder.

    Future integrations may include:
        - Email
        - Slack
        - Microsoft Teams
        - Webhooks
        - Celery background tasks
        - SMS

    Keeping this function here avoids modifying the
    orchestration flow when notification support is added.
    """

    logger.info(
        "Dispatching Notifications for alert %s",
        alert.id,
    )

    transaction.on_commit(
        lambda: dispatch_alert_notifications_task.delay(alert.id)
    )

    return None


def _determine_error_severity(log: Log):
    if log.status_code == 503:
        return AlertSeverity.CRITICAL
    if log.status_code and log.status_code >= 500:
        return AlertSeverity.HIGH
    return AlertSeverity.MEDIUM


def _create_or_update_alert(service, log, alert_type, severity, alert_key, message):
    """
    Create a new alert or update an existing active alert.

    Uses:
    - row-level locking
    - cooldown window
    - atomic updates
    - race-condition recovery
    """

    now = timezone.now()

    logger.info(
        "Evaluating %s alert for service %s",
        alert_type,
        service.id,
    )

    try:
        with transaction.atomic():

            alert = (
                Alert.objects.select_for_update()
                .filter(
                    service=service,
                    alert_type=alert_type,
                    alert_key=alert_key,
                    status__in=[AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED],
                )
                .first()
            )

            if alert:
                # cooldown
                if alert.last_triggered_at and (
                    now - alert.last_triggered_at < timedelta(seconds=ALERT_COOLDOWN_SECONDS)
                ):
                    
                    logger.info(
                        "Alert %s is in cooldown. Skipping.",
                        alert.id,
                    )
                    return alert

                # atomic update
                Alert.objects.filter(pk=alert.pk).update(
                    trigger_count=F('trigger_count') + 1,
                    last_triggered_at=now,
                    log=log,
                    severity=severity,
                )

                logger.info(
                    "Updated existing alert %s",
                    alert.id,
                )

                return alert

            # CREATE
            alert = Alert.objects.create(
                service=service,
                log=log,
                alert_type=alert_type,
                alert_key=alert_key,
                message=message,
                severity=severity,
                last_triggered_at=now,
            )

            logger.info(
                "Created new alert %s",
                alert.id,
            )

            return alert

    except IntegrityError:
        logger.warning(
            "IntegrityError while processing alert for log %s. Recovering from race condition.",
            log.id,
        )

        # fallback (race condition)
        alert = Alert.objects.filter(
            service=service,
            alert_type=alert_type,
            alert_key=alert_key,
            status__in=[AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED],
        ).first()

        if alert:
            Alert.objects.filter(pk=alert.pk).update(
                trigger_count=F('trigger_count') + 1,
                last_triggered_at=now,
                log=log,
                severity=severity,
            )

            logger.info(
                "Recovered existing alert %s after IntegrityError",
                alert.id,
            )

            return alert

        alert = Alert.objects.create(
            service=service,
            log=log,
            alert_type=alert_type,
            alert_key=alert_key,
            message=message,
            severity=severity,
            last_triggered_at=now,
        )

        logger.info(
            "Recovered by creating alert %s after IntegrityError",
            alert.id,
        )

        return alert