from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from monitoring.filters import LogFilter
from monitoring.models import (
    Log,
    LogStatus,
    Service,
)

User = get_user_model()


class LogFilterTests(TestCase):
    """
    Tests for LogFilter.
    """

    def setUp(self):
        self.user = User.objects.create_user(
            email="owner@example.com",
            password="Password@123",
        )

        self.service1 = Service.objects.create(
            name="Backend API",
            created_by=self.user,
        )

        self.service2 = Service.objects.create(
            name="Frontend API",
            created_by=self.user,
        )

    def _create_log(
        self,
        *,
        service=None,
        status=LogStatus.SUCCESS,
        status_code=200,
        response_time_ms=100,
        message="Request completed",
        created_at=None,
    ):
        log = Log.objects.create(
            service=service or self.service1,
            status=status,
            status_code=status_code,
            response_time_ms=response_time_ms,
            message=message,
        )

        if created_at:
            Log.objects.filter(pk=log.pk).update(
                created_at=created_at,
            )
            log.refresh_from_db()

        return log

    # ---------------------------------------------------------
    # Service Filter
    # ---------------------------------------------------------

    def test_filter_by_service(self):
        log1 = self._create_log(
            service=self.service1,
        )

        self._create_log(
            service=self.service2,
        )

        queryset = LogFilter(
            data={
                "service": self.service1.id,
            },
            queryset=Log.objects.all(),
        ).qs

        self.assertEqual(queryset.count(), 1)
        self.assertEqual(queryset.first(), log1)

    # ---------------------------------------------------------
    # Status Filter
    # ---------------------------------------------------------

    def test_filter_status_case_insensitive(self):
        log = self._create_log(
            status=LogStatus.ERROR,
        )

        self._create_log(
            status=LogStatus.SUCCESS,
        )

        queryset = LogFilter(
            data={
                "status": "ERROR",
            },
            queryset=Log.objects.all(),
        ).qs

        self.assertEqual(queryset.count(), 1)
        self.assertEqual(queryset.first(), log)

    def test_filter_status_no_match(self):
        self._create_log(
            status=LogStatus.SUCCESS,
        )

        queryset = LogFilter(
            data={
                "status": "warning",
            },
            queryset=Log.objects.all(),
        ).qs

        self.assertEqual(queryset.count(), 0)

    # ---------------------------------------------------------
    # Status Code
    # ---------------------------------------------------------

    def test_filter_status_code(self):
        log = self._create_log(
            status_code=500,
        )

        self._create_log(
            status_code=404,
        )

        queryset = LogFilter(
            data={
                "status_code": 500,
            },
            queryset=Log.objects.all(),
        ).qs

        self.assertEqual(queryset.count(), 1)
        self.assertEqual(queryset.first(), log)


        # ---------------------------------------------------------
    # Created At Filters
    # ---------------------------------------------------------

    def test_filter_created_after(self):
        now = timezone.now()

        old_log = self._create_log(
            created_at=now - timedelta(days=5),
        )

        recent_log = self._create_log(
            created_at=now - timedelta(days=1),
        )

        queryset = LogFilter(
            data={
                "created_after": (now - timedelta(days=2)).isoformat(),
            },
            queryset=Log.objects.all(),
        ).qs

        self.assertEqual(queryset.count(), 1)
        self.assertEqual(queryset.first(), recent_log)
        self.assertNotIn(old_log, queryset)

    def test_filter_created_before(self):
        now = timezone.now()

        old_log = self._create_log(
            created_at=now - timedelta(days=5),
        )

        self._create_log(
            created_at=now - timedelta(hours=2),
        )

        queryset = LogFilter(
            data={
                "created_before": (now - timedelta(days=2)).isoformat(),
            },
            queryset=Log.objects.all(),
        ).qs

        self.assertEqual(queryset.count(), 1)
        self.assertEqual(queryset.first(), old_log)

    def test_filter_created_between_range(self):
        now = timezone.now()

        old_log = self._create_log(
            created_at=now - timedelta(days=10),
        )

        middle_log = self._create_log(
            created_at=now - timedelta(days=5),
        )

        recent_log = self._create_log(
            created_at=now - timedelta(days=1),
        )

        queryset = LogFilter(
            data={
                "created_after": (
                    now - timedelta(days=7)
                ).isoformat(),
                "created_before": (
                    now - timedelta(days=2)
                ).isoformat(),
            },
            queryset=Log.objects.all(),
        ).qs

        self.assertEqual(queryset.count(), 1)
        self.assertEqual(queryset.first(), middle_log)

        self.assertNotIn(old_log, queryset)
        self.assertNotIn(recent_log, queryset)

    # ---------------------------------------------------------
    # Response Time Filters
    # ---------------------------------------------------------

    def test_filter_min_response_time(self):
        self._create_log(
            response_time_ms=100,
        )

        slow_log = self._create_log(
            response_time_ms=1500,
        )

        queryset = LogFilter(
            data={
                "min_response_time": 1000,
            },
            queryset=Log.objects.all(),
        ).qs

        self.assertEqual(queryset.count(), 1)
        self.assertEqual(queryset.first(), slow_log)

    def test_filter_max_response_time(self):
        fast_log = self._create_log(
            response_time_ms=100,
        )

        self._create_log(
            response_time_ms=2500,
        )

        queryset = LogFilter(
            data={
                "max_response_time": 500,
            },
            queryset=Log.objects.all(),
        ).qs

        self.assertEqual(queryset.count(), 1)
        self.assertEqual(queryset.first(), fast_log)

    def test_filter_response_time_range(self):
        self._create_log(
            response_time_ms=100,
        )

        middle_log = self._create_log(
            response_time_ms=900,
        )

        self._create_log(
            response_time_ms=3000,
        )

        queryset = LogFilter(
            data={
                "min_response_time": 500,
                "max_response_time": 1000,
            },
            queryset=Log.objects.all(),
        ).qs

        self.assertEqual(queryset.count(), 1)
        self.assertEqual(queryset.first(), middle_log)


        # ---------------------------------------------------------
    # Message Filter
    # ---------------------------------------------------------

    def test_filter_message_contains(self):
        matching_log = self._create_log(
            message="Database connection failed",
        )

        self._create_log(
            message="Everything is working",
        )

        queryset = LogFilter(
            data={
                "message": "connection",
            },
            queryset=Log.objects.all(),
        ).qs

        self.assertEqual(queryset.count(), 1)
        self.assertEqual(queryset.first(), matching_log)

    def test_filter_message_case_insensitive(self):
        matching_log = self._create_log(
            message="Server ERROR occurred",
        )

        self._create_log(
            message="Request completed successfully",
        )

        queryset = LogFilter(
            data={
                "message": "error",
            },
            queryset=Log.objects.all(),
        ).qs

        self.assertEqual(queryset.count(), 1)
        self.assertEqual(queryset.first(), matching_log)

    def test_filter_message_no_match(self):
        self._create_log(
            message="Authentication success",
        )

        queryset = LogFilter(
            data={
                "message": "payment",
            },
            queryset=Log.objects.all(),
        ).qs

        self.assertEqual(queryset.count(), 0)

    # ---------------------------------------------------------
    # Combined Filters
    # ---------------------------------------------------------

    def test_multiple_filters_together(self):
        target_log = self._create_log(
            service=self.service1,
            status=LogStatus.ERROR,
            status_code=500,
            response_time_ms=1800,
            message="Database timeout",
        )

        self._create_log(
            service=self.service1,
            status=LogStatus.SUCCESS,
            status_code=200,
            response_time_ms=100,
            message="Success",
        )

        self._create_log(
            service=self.service2,
            status=LogStatus.ERROR,
            status_code=500,
            response_time_ms=1800,
            message="Database timeout",
        )

        queryset = LogFilter(
            data={
                "service": self.service1.id,
                "status": "error",
                "status_code": 500,
                "min_response_time": 1000,
                "message": "database",
            },
            queryset=Log.objects.all(),
        ).qs

        self.assertEqual(queryset.count(), 1)
        self.assertEqual(queryset.first(), target_log)

    # ---------------------------------------------------------
    # Empty Filters
    # ---------------------------------------------------------

    def test_empty_filter_returns_all_logs(self):
        self._create_log()
        self._create_log()
        self._create_log()

        queryset = LogFilter(
            data={},
            queryset=Log.objects.all(),
        ).qs

        self.assertEqual(
            queryset.count(),
            Log.objects.count(),
        )

    # ---------------------------------------------------------
    # Unknown Parameters
    # ---------------------------------------------------------

    def test_unknown_parameter_is_ignored(self):
        log = self._create_log()

        queryset = LogFilter(
            data={
                "random_parameter": "value",
            },
            queryset=Log.objects.all(),
        ).qs

        self.assertEqual(queryset.count(), 1)
        self.assertEqual(queryset.first(), log)


        # ---------------------------------------------------------
    # Meta
    # ---------------------------------------------------------

    def test_meta_model(self):
        self.assertEqual(
            LogFilter._meta.model,
            Log,
        )

    def test_meta_fields(self):
        expected_fields = [
            "service",
            "status",
            "status_code",
            "created_after",
            "created_before",
            "min_response_time",
            "max_response_time",
            "message",
        ]

        self.assertEqual(
            list(LogFilter._meta.fields),
            expected_fields,
        )