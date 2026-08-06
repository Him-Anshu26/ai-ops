from unittest.mock import MagicMock, patch

from django.test import TestCase

from alerts.tasks import (
    cleanup_alerts_task,
    dispatch_alert_notifications_task,
)

from tests.factories import AlertFactory

from django.db import DatabaseError


# ============================================================
# dispatch_alert_notifications_task Tests
# ============================================================


class DispatchAlertNotificationsTaskTests(TestCase):
    """
    Unit tests for dispatch_alert_notifications_task.
    """

    @patch("alerts.tasks.dispatch_alert_notifications")
    @patch("alerts.tasks.Alert.objects.select_related")
    def test_loads_alert_by_id(
        self,
        mock_select_related,
        mock_dispatch,
    ):
        alert = AlertFactory()

        mock_select_related.return_value.get.return_value = alert

        dispatch_alert_notifications_task(
            alert.id,
        )

        mock_select_related.return_value.get.assert_called_once_with(
            pk=alert.id,
        )

    @patch("alerts.tasks.dispatch_alert_notifications")
    @patch("alerts.tasks.Alert.objects.select_related")
    def test_select_related_used(
        self,
        mock_select_related,
        mock_dispatch,
    ):
        alert = AlertFactory()

        mock_select_related.return_value.get.return_value = alert

        dispatch_alert_notifications_task(
            alert.id,
        )

        mock_select_related.assert_called_once_with(
            "service",
            "log",
        )

    @patch("alerts.tasks.dispatch_alert_notifications")
    @patch("alerts.tasks.Alert.objects.select_related")
    def test_dispatch_service_called(
        self,
        mock_select_related,
        mock_dispatch,
    ):
        alert = AlertFactory()

        mock_select_related.return_value.get.return_value = alert

        dispatch_alert_notifications_task(
            alert.id,
        )

        mock_dispatch.assert_called_once_with(
            alert,
        )

    @patch("alerts.tasks.dispatch_alert_notifications")
    @patch("alerts.tasks.Alert.objects.select_related")
    def test_dispatch_receives_same_alert(
        self,
        mock_select_related,
        mock_dispatch,
    ):
        alert = AlertFactory()

        mock_select_related.return_value.get.return_value = alert

        dispatch_alert_notifications_task(
            alert.id,
        )

        dispatched_alert = (
            mock_dispatch.call_args.args[0]
        )

        self.assertIs(
            dispatched_alert,
            alert,
        )

    @patch("alerts.tasks.logger")
    @patch("alerts.tasks.dispatch_alert_notifications")
    @patch("alerts.tasks.Alert.objects.select_related")
    def test_logs_task_start(
        self,
        mock_select_related,
        mock_dispatch,
        mock_logger,
    ):
        alert = AlertFactory()

        mock_select_related.return_value.get.return_value = alert

        dispatch_alert_notifications_task(
            alert.id,
        )

        mock_logger.info.assert_any_call(
            "Starting notification task for alert %s",
            alert.id,
        )

    @patch("alerts.tasks.logger")
    @patch("alerts.tasks.dispatch_alert_notifications")
    @patch("alerts.tasks.Alert.objects.select_related")
    def test_logs_task_finish(
        self,
        mock_select_related,
        mock_dispatch,
        mock_logger,
    ):
        alert = AlertFactory()

        mock_select_related.return_value.get.return_value = alert

        dispatch_alert_notifications_task(
            alert.id,
        )

        mock_logger.info.assert_any_call(
            "Finished notification task for alert %s",
            alert.id,
        )

    @patch("alerts.tasks.logger")
    @patch("alerts.tasks.dispatch_alert_notifications")
    @patch("alerts.tasks.Alert.objects.select_related")
    def test_missing_alert_logs_warning(
        self,
        mock_select_related,
        mock_dispatch,
        mock_logger,
    ):
        mock_select_related.return_value.get.side_effect = (
            AlertFactory._meta.model.DoesNotExist
        )

        dispatch_alert_notifications_task(
            999,
        )

        mock_logger.warning.assert_called_once_with(
            "Alert %s no longer exists. Skipping notification.",
            999,
        )

    @patch("alerts.tasks.dispatch_alert_notifications")
    @patch("alerts.tasks.Alert.objects.select_related")
    def test_missing_alert_returns_none(
        self,
        mock_select_related,
        mock_dispatch,
    ):
        mock_select_related.return_value.get.side_effect = (
            AlertFactory._meta.model.DoesNotExist
        )

        result = dispatch_alert_notifications_task(
            999,
        )

        self.assertIsNone(
            result,
        )

    @patch("alerts.tasks.dispatch_alert_notifications")
    @patch("alerts.tasks.Alert.objects.select_related")
    def test_missing_alert_does_not_dispatch(
        self,
        mock_select_related,
        mock_dispatch,
    ):
        mock_select_related.return_value.get.side_effect = (
            AlertFactory._meta.model.DoesNotExist
        )

        dispatch_alert_notifications_task(
            999,
        )

        mock_dispatch.assert_not_called()


    # ============================================================
    # Retry Behaviour
    # ============================================================

    @patch("alerts.tasks.Alert.objects.select_related")
    def test_database_error_propagates_for_retry(
        self,
        mock_select_related,
    ):
        mock_select_related.side_effect = DatabaseError()

        with self.assertRaises(
            DatabaseError,
        ):
            dispatch_alert_notifications_task(
                1,
            )

    @patch("alerts.tasks.Alert.objects.select_related")
    def test_connection_error_propagates_for_retry(
        self,
        mock_select_related,
    ):
        mock_select_related.side_effect = ConnectionError()

        with self.assertRaises(
            ConnectionError,
        ):
            dispatch_alert_notifications_task(
                1,
            )


# ============================================================
# cleanup_alerts_task Tests
# ============================================================


class CleanupAlertsTaskTests(TestCase):
    """
    Unit tests for cleanup_alerts_task.
    """

    @patch("alerts.tasks.cleanup_alerts")
    def test_cleanup_service_called(
        self,
        mock_cleanup,
    ):
        mock_cleanup.return_value = {
            "resolved_alerts": 5,
        }

        cleanup_alerts_task()

        mock_cleanup.assert_called_once_with()

    @patch("alerts.tasks.cleanup_alerts")
    def test_returns_cleanup_result(
        self,
        mock_cleanup,
    ):
        mock_cleanup.return_value = {
            "resolved_alerts": 8,
        }

        result = cleanup_alerts_task()

        self.assertEqual(
            result,
            {
                "resolved_alerts": 8,
            },
        )

    @patch("alerts.tasks.cleanup_alerts")
    def test_returns_empty_result(
        self,
        mock_cleanup,
    ):
        mock_cleanup.return_value = {}

        result = cleanup_alerts_task()

        self.assertEqual(
            result,
            {},
        )

    @patch("alerts.tasks.cleanup_alerts")
    def test_cleanup_called_once(
        self,
        mock_cleanup,
    ):
        mock_cleanup.return_value = {
            "resolved_alerts": 1,
        }

        cleanup_alerts_task()

        self.assertEqual(
            mock_cleanup.call_count,
            1,
        )



# ============================================================
# Celery Task Configuration Tests
# ============================================================


class TaskConfigurationTests(TestCase):
    """
    Verify Celery task configuration.
    """

    def test_dispatch_task_name(
        self,
    ):
        self.assertEqual(
            dispatch_alert_notifications_task.name,
            "alerts.dispatch_alert_notifications",
        )

    def test_cleanup_task_name(
        self,
    ):
        self.assertEqual(
            cleanup_alerts_task.name,
            "alerts.cleanup",
        )

    def test_dispatch_task_is_bound(
        self,
    ):
        self.assertTrue(
            dispatch_alert_notifications_task.bind,
        )

    def test_dispatch_task_autoretry_for(
        self,
    ):
        self.assertEqual(
            dispatch_alert_notifications_task.autoretry_for,
            (
                DatabaseError,
                ConnectionError,
            ),
        )

    def test_dispatch_task_retry_backoff_enabled(
        self,
    ):
        self.assertTrue(
            dispatch_alert_notifications_task.retry_backoff,
        )

    def test_dispatch_task_max_retries(
        self,
    ):

        self.assertIn(
            "max_retries",
            dispatch_alert_notifications_task.retry_kwargs,
        )
        
        self.assertEqual(
            dispatch_alert_notifications_task.retry_kwargs[
                "max_retries"
            ],
            5,
        )