from datetime import timedelta

import pytest

from django.utils import timezone

from monitoring.filters import LogFilter
from monitoring.models import (
    Log,
    LogStatus,
)

from tests.factories import ServiceFactory
from tests.monitoring.conftest import make_log


@pytest.mark.django_db
class TestLogFilter:
    """
    Tests for LogFilter.
    """

    # ---------------------------------------------------------
    # Service Filter
    # ---------------------------------------------------------

    def test_filter_by_service(self, service):
        another_service = ServiceFactory(
            created_by=service.created_by,
        )

        log1 = make_log(service)
        make_log(another_service)

        queryset = LogFilter(
            data={"service": service.id},
            queryset=Log.objects.all(),
        ).qs

        assert queryset.count() == 1
        assert queryset.first() == log1

    # ---------------------------------------------------------
    # Status Filter
    # ---------------------------------------------------------

    def test_filter_status_case_insensitive(self, service):
        log = make_log(service, status=LogStatus.ERROR)
        make_log(service, status=LogStatus.SUCCESS)

        queryset = LogFilter(
            data={"status": "ERROR"},
            queryset=Log.objects.all(),
        ).qs

        assert queryset.count() == 1
        assert queryset.first() == log

    def test_filter_status_no_match(self, service):
        make_log(service, status=LogStatus.SUCCESS)

        queryset = LogFilter(
            data={"status": "warning"},
            queryset=Log.objects.all(),
        ).qs

        assert queryset.count() == 0

    # ---------------------------------------------------------
    # Status Code
    # ---------------------------------------------------------

    def test_filter_status_code(self, service):
        log = make_log(service, status_code=500)
        make_log(service, status_code=404)

        queryset = LogFilter(
            data={"status_code": 500},
            queryset=Log.objects.all(),
        ).qs

        assert queryset.count() == 1
        assert queryset.first() == log

    # ---------------------------------------------------------
    # Created At Filters
    # ---------------------------------------------------------

    def test_filter_created_after(self, service):
        now = timezone.now()

        old_log = make_log(
            service,
            created_at=now - timedelta(days=5),
        )

        recent_log = make_log(
            service,
            created_at=now - timedelta(days=1),
        )

        queryset = LogFilter(
            data={
                "created_after": (now - timedelta(days=2)).isoformat(),
            },
            queryset=Log.objects.all(),
        ).qs

        assert queryset.count() == 1
        assert queryset.first() == recent_log
        assert old_log not in queryset

    def test_filter_created_before(self, service):
        now = timezone.now()

        old_log = make_log(
            service,
            created_at=now - timedelta(days=5),
        )

        make_log(
            service,
            created_at=now - timedelta(hours=2),
        )

        queryset = LogFilter(
            data={
                "created_before": (now - timedelta(days=2)).isoformat(),
            },
            queryset=Log.objects.all(),
        ).qs

        assert queryset.count() == 1
        assert queryset.first() == old_log

    def test_filter_created_between_range(self, service):
        now = timezone.now()

        old_log = make_log(
            service,
            created_at=now - timedelta(days=10),
        )

        middle_log = make_log(
            service,
            created_at=now - timedelta(days=5),
        )

        recent_log = make_log(
            service,
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

        assert queryset.count() == 1
        assert queryset.first() == middle_log
        assert old_log not in queryset
        assert recent_log not in queryset

    # ---------------------------------------------------------
    # Response Time Filters
    # ---------------------------------------------------------

    def test_filter_min_response_time(self, service):
        make_log(service, response_time_ms=100)
        slow_log = make_log(service, response_time_ms=1500)

        queryset = LogFilter(
            data={"min_response_time": 1000},
            queryset=Log.objects.all(),
        ).qs

        assert queryset.count() == 1
        assert queryset.first() == slow_log

    def test_filter_max_response_time(self, service):
        fast_log = make_log(service, response_time_ms=100)
        make_log(service, response_time_ms=2500)

        queryset = LogFilter(
            data={"max_response_time": 500},
            queryset=Log.objects.all(),
        ).qs

        assert queryset.count() == 1
        assert queryset.first() == fast_log

    def test_filter_response_time_range(self, service):
        make_log(service, response_time_ms=100)
        middle_log = make_log(service, response_time_ms=900)
        make_log(service, response_time_ms=3000)

        queryset = LogFilter(
            data={
                "min_response_time": 500,
                "max_response_time": 1000,
            },
            queryset=Log.objects.all(),
        ).qs

        assert queryset.count() == 1
        assert queryset.first() == middle_log

    # ---------------------------------------------------------
    # Message Filter
    # ---------------------------------------------------------

    def test_filter_message_contains(self, service):
        matching_log = make_log(
            service,
            message="Database connection failed",
        )

        make_log(service, message="Everything is working")

        queryset = LogFilter(
            data={"message": "connection"},
            queryset=Log.objects.all(),
        ).qs

        assert queryset.count() == 1
        assert queryset.first() == matching_log

    def test_filter_message_case_insensitive(self, service):
        matching_log = make_log(
            service,
            message="Server ERROR occurred",
        )

        make_log(service, message="Request completed successfully")

        queryset = LogFilter(
            data={"message": "error"},
            queryset=Log.objects.all(),
        ).qs

        assert queryset.count() == 1
        assert queryset.first() == matching_log

    def test_filter_message_no_match(self, service):
        make_log(service, message="Authentication success")

        queryset = LogFilter(
            data={"message": "payment"},
            queryset=Log.objects.all(),
        ).qs

        assert queryset.count() == 0

    # ---------------------------------------------------------
    # Combined Filters
    # ---------------------------------------------------------

    def test_multiple_filters_together(self, service):
        another_service = ServiceFactory(
            created_by=service.created_by,
        )

        target_log = make_log(
            service,
            status=LogStatus.ERROR,
            status_code=500,
            response_time_ms=1800,
            message="Database timeout",
        )

        make_log(
            service,
            status=LogStatus.SUCCESS,
            status_code=200,
            response_time_ms=100,
            message="Success",
        )

        make_log(
            another_service,
            status=LogStatus.ERROR,
            status_code=500,
            response_time_ms=1800,
            message="Database timeout",
        )

        queryset = LogFilter(
            data={
                "service": service.id,
                "status": "error",
                "status_code": 500,
                "min_response_time": 1000,
                "message": "database",
            },
            queryset=Log.objects.all(),
        ).qs

        assert queryset.count() == 1
        assert queryset.first() == target_log

    # ---------------------------------------------------------
    # Empty Filters
    # ---------------------------------------------------------

    def test_empty_filter_returns_all_logs(self, service):
        make_log(service)
        make_log(service)
        make_log(service)

        queryset = LogFilter(
            data={},
            queryset=Log.objects.all(),
        ).qs

        assert queryset.count() == Log.objects.count()

    # ---------------------------------------------------------
    # Unknown Parameters
    # ---------------------------------------------------------

    def test_unknown_parameter_is_ignored(self, service):
        log = make_log(service)

        queryset = LogFilter(
            data={"random_parameter": "value"},
            queryset=Log.objects.all(),
        ).qs

        assert queryset.count() == 1
        assert queryset.first() == log

    # ---------------------------------------------------------
    # Meta
    # ---------------------------------------------------------

    def test_meta_model(self):
        assert LogFilter._meta.model == Log

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

        assert list(LogFilter._meta.fields) == expected_fields