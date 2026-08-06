from datetime import timedelta
from unittest.mock import patch

import pytest

from django.utils import timezone

from monitoring.models import Log
from monitoring.services.cleanup_service import (
    CleanupOldLogsService,
    cleanup_old_logs,
    LOG_RETENTION_DAYS,
)

from tests.monitoring.conftest import make_log


@pytest.mark.django_db
class TestCleanupOldLogsService:
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

    # ---------------------------------------------------------
    # Cleanup
    # ---------------------------------------------------------

    def test_deletes_logs_older_than_retention(self, service):
        cutoff = timezone.now() - timedelta(days=LOG_RETENTION_DAYS)

        make_log(service, created_at=cutoff - timedelta(days=5))
        make_log(service, created_at=cutoff - timedelta(days=10))
        make_log(service, created_at=cutoff + timedelta(days=1))
        make_log(service, created_at=timezone.now())

        deleted = CleanupOldLogsService()()

        assert deleted == 2
        assert Log.objects.count() == 2

    def test_returns_zero_when_nothing_to_delete(self, service):
        make_log(service, created_at=timezone.now())
        make_log(service, created_at=timezone.now() - timedelta(days=5))

        deleted = CleanupOldLogsService()()

        assert deleted == 0
        assert Log.objects.count() == 2

    def test_deletes_all_old_logs(self, service):
        cutoff = timezone.now() - timedelta(days=LOG_RETENTION_DAYS)

        for _ in range(5):
            make_log(service, created_at=cutoff - timedelta(days=30))

        deleted = CleanupOldLogsService()()

        assert deleted == 5
        assert Log.objects.count() == 0

    # ---------------------------------------------------------
    # Boundary
    # ---------------------------------------------------------

    def test_log_exactly_on_retention_boundary_is_not_deleted(self, service):
        fixed_now = timezone.now()
        cutoff = fixed_now - timedelta(days=LOG_RETENTION_DAYS)

        log = make_log(service, created_at=cutoff)

        with patch(
            "monitoring.services.cleanup_service.timezone.now",
            return_value=fixed_now,
        ):
            deleted = CleanupOldLogsService()()

        assert deleted == 0
        assert Log.objects.filter(pk=log.pk).exists()

    def test_recent_logs_are_preserved(self, service):
        make_log(service, created_at=timezone.now())
        make_log(service, created_at=timezone.now() - timedelta(days=1))
        make_log(service, created_at=timezone.now() - timedelta(days=7))

        deleted = CleanupOldLogsService()()

        assert deleted == 0
        assert Log.objects.count() == 3

    # ---------------------------------------------------------
    # Logger
    # ---------------------------------------------------------

    @patch("monitoring.services.cleanup_service.logger.info")
    def test_logger_called(self, mock_logger, service):
        cutoff = timezone.now() - timedelta(days=LOG_RETENTION_DAYS)

        make_log(service, created_at=cutoff - timedelta(days=1))

        deleted = CleanupOldLogsService()()

        mock_logger.assert_called_once_with(
            "Deleted %s old monitoring log(s).",
            deleted,
        )

    # ---------------------------------------------------------
    # Callable instance
    # ---------------------------------------------------------

    def test_callable_instance(self, service):
        cutoff = timezone.now() - timedelta(days=LOG_RETENTION_DAYS)

        make_log(service, created_at=cutoff - timedelta(days=2))

        deleted = cleanup_old_logs()

        assert deleted == 1

    # ---------------------------------------------------------
    # Return Type
    # ---------------------------------------------------------

    def test_returns_integer(self):
        deleted = cleanup_old_logs()

        assert isinstance(deleted, int)