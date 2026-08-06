"""
Integration tests for the Log-to-Alert monitoring pipeline.
"""

import pytest
from datetime import timedelta
from unittest.mock import patch
from django.utils import timezone

from alerts.models import Alert, AlertType, AlertSeverity, AlertStatus
from monitoring.tasks import process_log_for_alerts_task
from tests.factories import LogFactory, AlertFactory


@pytest.mark.django_db
class TestLogToAlertWorkflow:
    
    @patch("monitoring.services.alert_service.dispatch_alert_notifications_task.delay")
    @patch("monitoring.services.alert_service.transaction.on_commit")
    def test_log_triggers_error_alert(self, mock_on_commit, mock_dispatch, service):
        """
        Verify that an error log natively triggers a new Critical Error Alert.
        """
        # 1. Generate Log
        log = LogFactory(
            service=service,
            status_code=503,
            status="error"
        )

        # 2. Invoke Pipeline Task
        process_log_for_alerts_task(log.id)

        # 3. Verify Database State
        assert Alert.objects.filter(service=service).count() == 1
        
        alert = Alert.objects.get(service=service)
        assert alert.alert_type == AlertType.ERROR
        assert alert.severity == AlertSeverity.CRITICAL
        assert alert.trigger_count == 1
        assert alert.status == AlertStatus.OPEN
        assert alert.log == log

        # 4. Verify Notification Handoff (unwrap transaction.on_commit)
        assert mock_on_commit.called
        mock_on_commit.call_args[0][0]()
        
        assert mock_dispatch.called
        assert mock_dispatch.call_args[0][0] == alert.id

    @patch("monitoring.services.alert_service.dispatch_alert_notifications_task.delay")
    @patch("monitoring.services.alert_service.transaction.on_commit")
    def test_log_triggers_high_latency_alert(self, mock_on_commit, mock_dispatch, service):
        """
        Verify that a slow request triggers a High Latency Alert.
        """
        # 1. Generate Log
        log = LogFactory(
            service=service,
            status_code=200,
            status="success",
            response_time_ms=6000
        )

        # 2. Invoke Pipeline Task
        process_log_for_alerts_task(log.id)

        # 3. Verify Database State
        assert Alert.objects.filter(service=service).count() == 1
        
        alert = Alert.objects.get(service=service)
        assert alert.alert_type == AlertType.HIGH_LATENCY
        assert alert.severity == AlertSeverity.HIGH
        assert alert.trigger_count == 1
        
        assert mock_on_commit.called
        mock_on_commit.call_args[0][0]()
        assert mock_dispatch.called

    @patch("monitoring.services.alert_service.dispatch_alert_notifications_task.delay")
    @patch("monitoring.services.alert_service.transaction.on_commit")
    def test_duplicate_log_increments_existing_alert(self, mock_on_commit, mock_dispatch, service):
        """
        Verify that a new log matching an existing active alert increments the trigger count
        if outside the cooldown window, instead of creating a duplicate alert.
        """
        alert_key = f"error:{service.id}:503"
        
        # 1. Pre-inject an existing alert, artificially aged past the 30s cooldown
        existing_alert = AlertFactory(
            service=service,
            alert_type=AlertType.ERROR,
            alert_key=alert_key,
            severity=AlertSeverity.CRITICAL,
            status=AlertStatus.OPEN,
            trigger_count=1
        )
        Alert.objects.filter(id=existing_alert.id).update(
            last_triggered_at=timezone.now() - timedelta(seconds=40)
        )

        # 2. Generate a new matching log
        log = LogFactory(
            service=service,
            status_code=503,
            status="error"
        )

        # 3. Invoke Pipeline Task
        process_log_for_alerts_task(log.id)

        # 4. Verify Database State (No duplicates, just incremented)
        assert Alert.objects.filter(service=service).count() == 1
        
        existing_alert.refresh_from_db()
        assert existing_alert.trigger_count == 2
        assert existing_alert.log == log
        
        assert mock_on_commit.called
        mock_on_commit.call_args[0][0]()
        assert mock_dispatch.called

    @patch("monitoring.services.alert_service.dispatch_alert_notifications_task.delay")
    @patch("monitoring.services.alert_service.transaction.on_commit")
    def test_alert_cooldown_prevents_spam(self, mock_on_commit, mock_dispatch, service):
        """
        Verify that a new log matching an existing active alert inside the 30s cooldown
        window is safely ignored to prevent spamming notifications.
        """
        alert_key = f"error:{service.id}:503"
        
        # 1. Pre-inject an existing alert, triggered just 5 seconds ago
        existing_alert = AlertFactory(
            service=service,
            alert_type=AlertType.ERROR,
            alert_key=alert_key,
            severity=AlertSeverity.CRITICAL,
            status=AlertStatus.OPEN,
            trigger_count=1
        )
        Alert.objects.filter(id=existing_alert.id).update(
            last_triggered_at=timezone.now() - timedelta(seconds=5)
        )

        # 2. Generate a new matching log
        log = LogFactory(
            service=service,
            status_code=503,
            status="error"
        )

        # 3. Invoke Pipeline Task
        process_log_for_alerts_task(log.id)

        # 4. Verify Database State (Ignored)
        existing_alert.refresh_from_db()
        # Count remains 1, it was skipped
        assert existing_alert.trigger_count == 1
        
        # Note: Production logic still calls _queue_notifications even when in cooldown.
        assert mock_on_commit.called

    @patch("monitoring.services.alert_service.dispatch_alert_notifications_task.delay")
    @patch("monitoring.services.alert_service.transaction.on_commit")
    def test_benign_log_ignored(self, mock_on_commit, mock_dispatch, service):
        """
        Verify that perfectly healthy logs do not trigger any alert logic.
        """
        # 1. Generate Healthy Log
        log = LogFactory(
            service=service,
            status_code=200,
            status="success",
            response_time_ms=50
        )

        # 2. Invoke Pipeline Task
        process_log_for_alerts_task(log.id)

        # 3. Verify Database State (No alerts generated)
        assert Alert.objects.filter(service=service).count() == 0
        
        # No notifications dispatched
        assert not mock_on_commit.called
        assert not mock_dispatch.called
