from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from alerts.models import (
    AlertStatus,
)

from alerts.services.cleanup_service import (
    CleanupAlertsService,
    CleanupResolvedAlertsService,
    RESOLVED_ALERT_RETENTION_DAYS,
)

from tests.factories import AlertFactory

# ============================================================
# CleanupResolvedAlertsService Tests
# ============================================================


class CleanupResolvedAlertsServiceTests(TestCase):
    """
    Unit tests for CleanupResolvedAlertsService.
    """

    def setUp(self):
        self.service = CleanupResolvedAlertsService()

    def test_deletes_old_resolved_alert(
        self,
    ):
        alert = AlertFactory(
            status=AlertStatus.RESOLVED,
        )

        alert.resolved_at = (
            timezone.now()
            - timedelta(
                days=RESOLVED_ALERT_RETENTION_DAYS + 1,
            )
        )

        alert.save(
            update_fields=[
                "resolved_at",
            ]
        )

        deleted = self.service()

        self.assertEqual(
            deleted,
            1,
        )

        self.assertFalse(
            alert.__class__.objects.filter(
                pk=alert.pk,
            ).exists()
        )

    def test_does_not_delete_recent_resolved_alert(
        self,
    ):
        alert = AlertFactory(
            status=AlertStatus.RESOLVED,
        )

        alert.resolved_at = (
            timezone.now()
            - timedelta(
                days=30,
            )
        )

        alert.save(
            update_fields=[
                "resolved_at",
            ]
        )

        deleted = self.service()

        self.assertEqual(
            deleted,
            0,
        )

        self.assertTrue(
            alert.__class__.objects.filter(
                pk=alert.pk,
            ).exists()
        )

    def test_does_not_delete_open_alert(
        self,
    ):
        alert = AlertFactory(
            status=AlertStatus.OPEN,
        )

        deleted = self.service()

        self.assertEqual(
            deleted,
            0,
        )

        self.assertTrue(
            alert.__class__.objects.filter(
                pk=alert.pk,
            ).exists()
        )

    def test_does_not_delete_acknowledged_alert(
        self,
    ):
        alert = AlertFactory(
            status=AlertStatus.ACKNOWLEDGED,
        )

        deleted = self.service()

        self.assertEqual(
            deleted,
            0,
        )

        self.assertTrue(
            alert.__class__.objects.filter(
                pk=alert.pk,
            ).exists()
        )

    def test_returns_deleted_count(
        self,
    ):
        for _ in range(3):

            alert = AlertFactory(
                status=AlertStatus.RESOLVED,
            )

            alert.resolved_at = (
                timezone.now()
                - timedelta(
                    days=120,
                )
            )

            alert.save(
                update_fields=[
                    "resolved_at",
                ]
            )

        deleted = self.service()

        self.assertEqual(
            deleted,
            3,
        )

    @patch(
        "alerts.services.cleanup_service.logger"
    )
    def test_logs_deleted_count(
        self,
        mock_logger,
    ):
        alert = AlertFactory(
            status=AlertStatus.RESOLVED,
        )

        alert.resolved_at = (
            timezone.now()
            - timedelta(
                days=120,
            )
        )

        alert.save(
            update_fields=[
                "resolved_at",
            ]
        )

        self.service()

        mock_logger.info.assert_called_once_with(
            "Deleted %s resolved alert(s).",
            1,
        )


    def test_boundary_alert_is_not_deleted(
        self,
    ):
        alert = AlertFactory(
            status=AlertStatus.RESOLVED,
        )

        fixed_now = timezone.now()

        retention_date = (
            fixed_now
            - timedelta(
                days=RESOLVED_ALERT_RETENTION_DAYS,
            )
        )

        alert.resolved_at = retention_date

        alert.save(
            update_fields=[
                "resolved_at",
            ]
        )

        with patch(
            "alerts.services.cleanup_service.timezone.now",
            return_value=fixed_now,
        ):
            deleted = self.service()

        self.assertEqual(
            deleted,
            0,
        )

        self.assertTrue(
            alert.__class__.objects.filter(
                pk=alert.pk,
            ).exists()
        )

    def test_multiple_old_resolved_alerts_deleted(
        self,
    ):
        alerts = []

        for _ in range(5):

            alert = AlertFactory(
                status=AlertStatus.RESOLVED,
            )

            alert.resolved_at = (
                timezone.now()
                - timedelta(
                    days=150,
                )
            )

            alert.save(
                update_fields=[
                    "resolved_at",
                ]
            )

            alerts.append(
                alert.pk,
            )

        deleted = self.service()

        self.assertEqual(
            deleted,
            5,
        )

        self.assertFalse(
            alert.__class__.objects.filter(
                pk__in=alerts,
            ).exists()
        )

    def test_returns_zero_when_nothing_to_delete(
        self,
    ):
        AlertFactory(
            status=AlertStatus.OPEN,
        )

        AlertFactory(
            status=AlertStatus.ACKNOWLEDGED,
        )

        deleted = self.service()

        self.assertEqual(
            deleted,
            0,
        )

    def test_old_and_recent_resolved_alerts(
        self,
    ):
        old_alert = AlertFactory(
            status=AlertStatus.RESOLVED,
        )

        recent_alert = AlertFactory(
            status=AlertStatus.RESOLVED,
        )

        old_alert.resolved_at = (
            timezone.now()
            - timedelta(
                days=150,
            )
        )

        recent_alert.resolved_at = (
            timezone.now()
            - timedelta(
                days=15,
            )
        )

        old_alert.save(
            update_fields=[
                "resolved_at",
            ]
        )

        recent_alert.save(
            update_fields=[
                "resolved_at",
            ]
        )

        deleted = self.service()

        self.assertEqual(
            deleted,
            1,
        )

        self.assertFalse(
            old_alert.__class__.objects.filter(
                pk=old_alert.pk,
            ).exists()
        )

        self.assertTrue(
            recent_alert.__class__.objects.filter(
                pk=recent_alert.pk,
            ).exists()
        )

    def test_only_resolved_alerts_are_deleted(
        self,
    ):
        resolved = AlertFactory(
            status=AlertStatus.RESOLVED,
        )

        open_alert = AlertFactory(
            status=AlertStatus.OPEN,
        )

        acknowledged = AlertFactory(
            status=AlertStatus.ACKNOWLEDGED,
        )

        resolved.resolved_at = (
            timezone.now()
            - timedelta(
                days=120,
            )
        )

        resolved.save(
            update_fields=[
                "resolved_at",
            ]
        )

        deleted = self.service()

        self.assertEqual(
            deleted,
            1,
        )

        self.assertFalse(
            resolved.__class__.objects.filter(
                pk=resolved.pk,
            ).exists()
        )

        self.assertTrue(
            open_alert.__class__.objects.filter(
                pk=open_alert.pk,
            ).exists()
        )

        self.assertTrue(
            acknowledged.__class__.objects.filter(
                pk=acknowledged.pk,
            ).exists()
        )

    @patch(
        "alerts.services.cleanup_service.logger"
    )
    def test_logs_zero_deleted_alerts(
        self,
        mock_logger,
    ):
        deleted = self.service()

        self.assertEqual(
            deleted,
            0,
        )

        mock_logger.info.assert_called_once_with(
            "Deleted %s resolved alert(s).",
            0,
        )



class CleanupAlertsServiceTests(TestCase):
    """
    Unit tests for CleanupAlertsService.
    """

    def setUp(self):
        self.service = CleanupAlertsService()

    @patch(
        "alerts.services.cleanup_service.cleanup_resolved_alerts"
    )
    def test_calls_cleanup_resolved_alerts(
        self,
        mock_cleanup,
    ):
        mock_cleanup.return_value = 5

        self.service()

        mock_cleanup.assert_called_once_with()

    @patch(
        "alerts.services.cleanup_service.cleanup_resolved_alerts"
    )
    def test_returns_expected_dictionary(
        self,
        mock_cleanup,
    ):
        mock_cleanup.return_value = 7

        result = self.service()

        self.assertEqual(
            result,
            {
                "resolved_alerts": 7,
            },
        )

    @patch(
        "alerts.services.cleanup_service.logger"
    )
    @patch(
        "alerts.services.cleanup_service.cleanup_resolved_alerts"
    )
    def test_logs_cleanup_start(
        self,
        mock_cleanup,
        mock_logger,
    ):
        mock_cleanup.return_value = 2

        self.service()

        mock_logger.info.assert_any_call(
            "Starting alerts cleanup.",
        )

    @patch(
        "alerts.services.cleanup_service.logger"
    )
    @patch(
        "alerts.services.cleanup_service.cleanup_resolved_alerts"
    )
    def test_logs_cleanup_completion(
        self,
        mock_cleanup,
        mock_logger,
    ):
        mock_cleanup.return_value = 4

        self.service()

        mock_logger.info.assert_any_call(
            (
                "Alerts cleanup completed. "
                "Resolved Alerts=%s"
            ),
            4,
        )

    @patch(
        "alerts.services.cleanup_service.cleanup_resolved_alerts"
    )
    def test_returns_zero_when_no_alerts_deleted(
        self,
        mock_cleanup,
    ):
        mock_cleanup.return_value = 0

        result = self.service()

        self.assertEqual(
            result["resolved_alerts"],
            0,
        )

    @patch(
        "alerts.services.cleanup_service.cleanup_resolved_alerts"
    )
    def test_returns_deleted_count(
        self,
        mock_cleanup,
    ):
        mock_cleanup.return_value = 12

        result = self.service()

        self.assertEqual(
            result["resolved_alerts"],
            12,
        )

    @patch(
        "alerts.services.cleanup_service.logger"
    )
    @patch(
        "alerts.services.cleanup_service.cleanup_resolved_alerts"
    )
    def test_logger_info_called_twice(
        self,
        mock_cleanup,
        mock_logger,
    ):
        mock_cleanup.return_value = 3

        self.service()

        self.assertEqual(
            mock_logger.info.call_count,
            2,
        )

    @patch(
        "alerts.services.cleanup_service.cleanup_resolved_alerts"
    )
    def test_cleanup_result_used_in_response(
        self,
        mock_cleanup,
    ):
        mock_cleanup.return_value = 25

        result = self.service()

        self.assertEqual(
            result,
            {
                "resolved_alerts": 25,
            },
        )