from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from monitoring.models import (
    Log,
    Service,
)
from monitoring.services.cleanup_service import (
    CleanupOldLogsService,
    cleanup_old_logs,
    LOG_RETENTION_DAYS,
)

User = get_user_model()


class CleanupOldLogsServiceTests(TestCase):
    """
    Unit tests for CleanupOldLogsService.

    Covers:
    - Deleting expired logs
    - Preserving recent logs
    - Boundary conditions
    - Return values
    - Logger
    - Callable instance
    """

    def setUp(self):
        self.user = User.objects.create_user(
            email="owner@example.com",
            password="Password@123",
        )

        self.service = Service.objects.create(
            name="Monitoring API",
            created_by=self.user,
        )

    # ---------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------

    def _create_log(self, created_at):
        log = Log.objects.create(
            service=self.service,
            message="Health log",
        )

        Log.objects.filter(pk=log.pk).update(
            created_at=created_at,
        )

        log.refresh_from_db()

        return log

    # ---------------------------------------------------------
    # Cleanup
    # ---------------------------------------------------------

    def test_deletes_logs_older_than_retention(self):
        cutoff = timezone.now() - timedelta(days=LOG_RETENTION_DAYS)

        self._create_log(
            cutoff - timedelta(days=5),
        )

        self._create_log(
            cutoff - timedelta(days=10),
        )

        self._create_log(
            cutoff + timedelta(days=1),
        )

        self._create_log(
            timezone.now(),
        )

        deleted = CleanupOldLogsService()()

        self.assertEqual(deleted, 2)
        self.assertEqual(Log.objects.count(), 2)

    def test_returns_zero_when_nothing_to_delete(self):
        self._create_log(timezone.now())
        self._create_log(
            timezone.now() - timedelta(days=5),
        )

        deleted = CleanupOldLogsService()()

        self.assertEqual(deleted, 0)
        self.assertEqual(Log.objects.count(), 2)

    def test_deletes_all_old_logs(self):
        cutoff = timezone.now() - timedelta(days=LOG_RETENTION_DAYS)

        for _ in range(5):
            self._create_log(
                cutoff - timedelta(days=30),
            )

        deleted = CleanupOldLogsService()()

        self.assertEqual(deleted, 5)
        self.assertEqual(Log.objects.count(), 0)

    # ---------------------------------------------------------
    # Boundary
    # ---------------------------------------------------------

    def test_log_exactly_on_retention_boundary_is_not_deleted(self):
        fixed_now = timezone.now()

        cutoff = fixed_now - timedelta(days=LOG_RETENTION_DAYS)

        log = self._create_log(cutoff)

        with patch(
            "monitoring.services.cleanup_service.timezone.now",
            return_value=fixed_now,
        ):
            deleted = CleanupOldLogsService()()

        self.assertEqual(deleted, 0)

        self.assertTrue(
            Log.objects.filter(pk=log.pk).exists()
        )

    def test_recent_logs_are_preserved(self):
        self._create_log(
            timezone.now(),
        )

        self._create_log(
            timezone.now() - timedelta(days=1),
        )

        self._create_log(
            timezone.now() - timedelta(days=7),
        )

        deleted = CleanupOldLogsService()()

        self.assertEqual(deleted, 0)
        self.assertEqual(Log.objects.count(), 3)

    # ---------------------------------------------------------
    # Logger
    # ---------------------------------------------------------

    @patch("monitoring.services.cleanup_service.logger.info")
    def test_logger_called(self, mock_logger):
        cutoff = timezone.now() - timedelta(days=LOG_RETENTION_DAYS)

        self._create_log(
            cutoff - timedelta(days=1),
        )

        deleted = CleanupOldLogsService()()

        mock_logger.assert_called_once_with(
            "Deleted %s old monitoring log(s).",
            deleted,
        )

    # ---------------------------------------------------------
    # Callable instance
    # ---------------------------------------------------------

    def test_callable_instance(self):
        cutoff = timezone.now() - timedelta(days=LOG_RETENTION_DAYS)

        self._create_log(
            cutoff - timedelta(days=2),
        )

        deleted = cleanup_old_logs()

        self.assertEqual(deleted, 1)

    # ---------------------------------------------------------
    # Return Type
    # ---------------------------------------------------------

    def test_returns_integer(self):
        deleted = cleanup_old_logs()

        self.assertIsInstance(
            deleted,
            int,
        )