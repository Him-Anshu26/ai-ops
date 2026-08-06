from unittest.mock import patch

import pytest

from monitoring.models import LogStatus
from monitoring.tasks import (
    process_log_for_alerts_task,
    cleanup_old_logs,
    cleanup_monitoring,
)

from tests.monitoring.conftest import make_log


# ============================================================
# process_log_for_alerts_task()
# ============================================================


@pytest.mark.django_db
class TestProcessLogForAlertsTask:
    """
    Tests for process_log_for_alerts_task.
    """

    @patch("monitoring.tasks.process_log_for_alerts")
    @patch("monitoring.tasks.logger")
    def test_processes_existing_log(self, mock_logger, mock_process, service):
        """
        Existing log should be processed.
        """
        log = make_log(service)

        process_log_for_alerts_task(log.id)

        mock_process.assert_called_once_with(log)
        mock_logger.info.assert_any_call("Starting alert processing for log %s", log.id)
        mock_logger.info.assert_any_call("Finished alert processing for log %s", log.id)

    @patch("monitoring.tasks.process_log_for_alerts")
    def test_process_called_exactly_once(self, mock_process, service):
        """
        Alert service should execute exactly once.
        """
        log = make_log(service)

        process_log_for_alerts_task(log.id)

        assert mock_process.call_count == 1

    @patch("monitoring.tasks.process_log_for_alerts")
    def test_process_receives_correct_log(self, mock_process, service):
        """
        Correct Log instance is passed.
        """
        log = make_log(service, message="Critical Error")

        process_log_for_alerts_task(log.id)

        called_log = mock_process.call_args.args[0]
        assert called_log.id == log.id
        assert called_log.message == "Critical Error"

    @patch("monitoring.tasks.process_log_for_alerts")
    @patch("monitoring.tasks.logger")
    def test_missing_log_is_handled_gracefully(self, mock_logger, mock_process):
        """
        Missing log should not raise an exception.
        """
        process_log_for_alerts_task(999999)

        mock_process.assert_not_called()
        mock_logger.warning.assert_called_once_with(
            "Alert processing skipped. Log %s does not exist.",
            999999,
        )

    @patch("monitoring.tasks.process_log_for_alerts")
    def test_missing_log_returns_none(self, mock_process):
        """
        Missing log should simply return.
        """
        result = process_log_for_alerts_task(999999)

        assert result is None
        mock_process.assert_not_called()

    @patch("monitoring.tasks.process_log_for_alerts")
    def test_uses_select_related_query(self, mock_process, service):
        """
        Task should fetch logs using select_related.
        """
        log = make_log(service)

        with patch("monitoring.tasks.Log.objects") as mock_manager:
            queryset = mock_manager.select_related.return_value
            queryset.get.return_value = log

            process_log_for_alerts_task(log.id)

            mock_manager.select_related.assert_called_once_with("service")
            queryset.get.assert_called_once_with(pk=log.id)

    @patch("monitoring.tasks.process_log_for_alerts")
    @patch("monitoring.tasks.logger")
    def test_logger_messages_are_written(self, mock_logger, mock_process, service):
        """
        Start and finish log messages should be emitted.
        """
        log = make_log(service)

        process_log_for_alerts_task(log.id)

        assert mock_logger.info.call_count == 2


# ============================================================
# cleanup_old_logs()
# ============================================================


class TestCleanupOldLogsTask:
    """
    Tests for cleanup_old_logs task.
    """

    @patch("monitoring.tasks.cleanup_old_logs_service")
    @patch("monitoring.tasks.logger")
    def test_cleanup_returns_deleted_count(self, mock_logger, mock_cleanup):
        """
        Deleted count should be returned.
        """
        mock_cleanup.return_value = 12

        result = cleanup_old_logs()

        assert result == 12
        mock_cleanup.assert_called_once()
        mock_logger.info.assert_called_once_with(
            "Deleted %s old monitoring log(s).",
            12,
        )

    @patch("monitoring.tasks.cleanup_old_logs_service")
    def test_cleanup_service_called_once(self, mock_cleanup):
        """
        Cleanup service should execute once.
        """
        mock_cleanup.return_value = 5

        cleanup_old_logs()

        assert mock_cleanup.call_count == 1

    @patch("monitoring.tasks.cleanup_old_logs_service")
    @patch("monitoring.tasks.logger")
    def test_zero_deleted_logs(self, mock_logger, mock_cleanup):
        """
        Zero deletions should still be logged.
        """
        mock_cleanup.return_value = 0

        result = cleanup_old_logs()

        assert result == 0
        mock_logger.info.assert_called_once_with(
            "Deleted %s old monitoring log(s).",
            0,
        )


# ============================================================
# cleanup_monitoring()
# ============================================================


class TestCleanupMonitoringTask:
    """
    Tests for cleanup_monitoring task.
    """

    @patch("monitoring.tasks.cleanup_old_logs")
    @patch("monitoring.tasks.logger")
    def test_cleanup_monitoring_returns_summary(self, mock_logger, mock_cleanup_logs):
        """
        Task should return cleanup summary.
        """
        mock_cleanup_logs.return_value = 15

        result = cleanup_monitoring()

        assert result == {"logs": 15}
        mock_cleanup_logs.assert_called_once()

    @patch("monitoring.tasks.cleanup_old_logs")
    @patch("monitoring.tasks.logger")
    def test_cleanup_monitoring_logs_start_and_finish(
        self, mock_logger, mock_cleanup_logs
    ):
        """
        Start and finish log messages should be emitted.
        """
        mock_cleanup_logs.return_value = 8

        cleanup_monitoring()

        mock_logger.info.assert_any_call("Starting monitoring cleanup.")
        mock_logger.info.assert_any_call(
            "Monitoring cleanup finished. Logs=%s",
            8,
        )

    @patch("monitoring.tasks.cleanup_old_logs")
    def test_cleanup_monitoring_calls_cleanup_logs_once(self, mock_cleanup_logs):
        """
        cleanup_old_logs should execute exactly once.
        """
        mock_cleanup_logs.return_value = 20

        cleanup_monitoring()

        assert mock_cleanup_logs.call_count == 1

    @patch("monitoring.tasks.cleanup_old_logs")
    def test_cleanup_monitoring_handles_zero_deleted_logs(self, mock_cleanup_logs):
        """
        Zero deleted logs should still return correctly.
        """
        mock_cleanup_logs.return_value = 0

        result = cleanup_monitoring()

        assert result == {"logs": 0}


# ============================================================
# Task Integration Tests
# ============================================================


@pytest.mark.django_db
class TestMonitoringTaskIntegration:
    """
    Integration-oriented task tests.
    """

    @patch("monitoring.tasks.process_log_for_alerts")
    def test_process_log_task_returns_none(self, mock_process, service):
        """
        Celery task should not return any value.
        """
        log = make_log(service)

        result = process_log_for_alerts_task(log.id)

        assert result is None

    @patch("monitoring.tasks.cleanup_old_logs_service")
    def test_cleanup_old_logs_returns_integer(self, mock_cleanup):
        """
        Cleanup task should return integer count.
        """
        mock_cleanup.return_value = 42

        result = cleanup_old_logs()

        assert isinstance(result, int)

    @patch("monitoring.tasks.cleanup_old_logs")
    def test_cleanup_monitoring_return_structure(self, mock_cleanup_logs):
        """
        Returned structure should always contain logs key.
        """
        mock_cleanup_logs.return_value = 9

        result = cleanup_monitoring()

        assert "logs" in result
        assert result["logs"] == 9

    @patch("monitoring.tasks.process_log_for_alerts")
    def test_task_can_process_error_log(self, mock_process, service):
        """
        Error logs should be processed exactly like success logs.
        """
        log = make_log(
            service,
            status=LogStatus.ERROR,
            status_code=500,
            response_time_ms=1800,
            message="Internal Server Error",
        )

        process_log_for_alerts_task(log.id)

        mock_process.assert_called_once_with(log)

    @patch("monitoring.tasks.process_log_for_alerts")
    def test_task_can_process_warning_log(self, mock_process, service):
        """
        Warning logs should also be processed.
        """
        log = make_log(
            service,
            status=LogStatus.WARNING,
            status_code=429,
            response_time_ms=900,
            message="Rate limit exceeded",
        )

        process_log_for_alerts_task(log.id)

        mock_process.assert_called_once_with(log)