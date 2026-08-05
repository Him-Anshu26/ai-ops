from django.contrib.auth import get_user_model
from django.test import TestCase

from monitoring.models import (
    Log,
    LogStatus,
    Service,
)
from monitoring.pagination import LogCursorPagination
from monitoring.serializers.log_serializer import LogReadSerializer

from rest_framework.request import Request
from rest_framework.test import APIRequestFactory


User = get_user_model()


class LogCursorPaginationTests(TestCase):
    """
    Tests for LogCursorPagination.
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

    def _create_log(
        self,
        status=LogStatus.SUCCESS,
        status_code=200,
        response_time_ms=100,
        message="Test log",
    ):
        return Log.objects.create(
            service=self.service,
            status=status,
            status_code=status_code,
            response_time_ms=response_time_ms,
            message=message,
        )

    # ---------------------------------------------------------
    # Configuration
    # ---------------------------------------------------------

    def test_default_page_size(self):
        self.assertEqual(
            LogCursorPagination.page_size,
            20,
        )

    def test_page_size_query_param(self):
        self.assertEqual(
            LogCursorPagination.page_size_query_param,
            "page_size",
        )

    def test_max_page_size(self):
        self.assertEqual(
            LogCursorPagination.max_page_size,
            100,
        )

    def test_default_ordering(self):
        self.assertEqual(
            LogCursorPagination.ordering,
            "-created_at",
        )


class LogCursorPaginationBehaviorTests(TestCase):
    """
    Behavioral tests for LogCursorPagination.
    """

    def setUp(self):
        self.factory = APIRequestFactory()

        self.user = User.objects.create_user(
            email="owner@example.com",
            password="Password@123",
        )

        self.service = Service.objects.create(
            name="Monitoring API",
            created_by=self.user,
        )

    def _create_logs(self, count):
        logs = []

        for index in range(count):
            logs.append(
                Log.objects.create(
                    service=self.service,
                    status=LogStatus.SUCCESS,
                    status_code=200,
                    response_time_ms=index,
                    message=f"Log {index}",
                )
            )

        return logs

    # ---------------------------------------------------------
    # Default page size
    # ---------------------------------------------------------

    def test_default_page_contains_20_results(self):
        self._create_logs(30)

        request = Request(self.factory.get("/api/v1/monitoring/logs/"))

        paginator = LogCursorPagination()

        queryset = Log.objects.all().order_by("-created_at")

        page = paginator.paginate_queryset(
            queryset,
            request,
        )

        self.assertEqual(
            len(page),
            20,
        )

    # ---------------------------------------------------------
    # Less than page size
    # ---------------------------------------------------------

    def test_returns_all_results_when_less_than_page_size(self):
        self._create_logs(8)

        request = Request(self.factory.get("/api/v1/monitoring/logs/"))

        paginator = LogCursorPagination()

        queryset = Log.objects.all().order_by("-created_at")

        page = paginator.paginate_queryset(
            queryset,
            request,
        )

        self.assertEqual(
            len(page),
            8,
        )

    # ---------------------------------------------------------
    # Exactly page size
    # ---------------------------------------------------------

    def test_returns_exact_page_size(self):
        self._create_logs(20)

        request = Request(self.factory.get("/api/v1/monitoring/logs/"))

        paginator = LogCursorPagination()

        queryset = Log.objects.all().order_by("-created_at")

        page = paginator.paginate_queryset(
            queryset,
            request,
        )

        self.assertEqual(
            len(page),
            20,
        )


        # ---------------------------------------------------------
    # page_size query parameter
    # ---------------------------------------------------------

    def test_custom_page_size(self):
        self._create_logs(40)

        request = Request(
            self.factory.get(
                "/api/v1/monitoring/logs/",
                {
                    "page_size": 10,
                },
            )
        )

        paginator = LogCursorPagination()

        queryset = Log.objects.all().order_by("-created_at")

        page = paginator.paginate_queryset(
            queryset,
            request,
        )

        self.assertEqual(
            len(page),
            10,
        )

    # ---------------------------------------------------------
    # max_page_size enforcement
    # ---------------------------------------------------------

    def test_page_size_is_limited_to_max_page_size(self):
        self._create_logs(150)

        request = Request(
            self.factory.get(
                "/api/v1/monitoring/logs/",
                {
                    "page_size": 999,
                },
            )
        )

        paginator = LogCursorPagination()

        queryset = Log.objects.all().order_by("-created_at")

        page = paginator.paginate_queryset(
            queryset,
            request,
        )

        self.assertEqual(
            len(page),
            paginator.max_page_size,
        )

    # ---------------------------------------------------------
    # Ordering
    # ---------------------------------------------------------

    def test_results_are_ordered_by_created_at_descending(self):
        self._create_logs(5)

        request = Request(self.factory.get("/api/v1/monitoring/logs/"))

        paginator = LogCursorPagination()

        queryset = Log.objects.all()

        page = paginator.paginate_queryset(
            queryset,
            request,
        )

        created_times = [
            log.created_at
            for log in page
        ]

        self.assertEqual(
            created_times,
            sorted(
                created_times,
                reverse=True,
            ),
        )

    # ---------------------------------------------------------
    # Ordering configuration
    # ---------------------------------------------------------

    def test_ordering_configuration(self):
        paginator = LogCursorPagination()

        self.assertEqual(
            paginator.ordering,
            "-created_at",
        )


        # ---------------------------------------------------------
    # Empty queryset
    # ---------------------------------------------------------

    def test_empty_queryset_returns_empty_page(self):
        request = Request(self.factory.get("/api/v1/monitoring/logs/"))

        paginator = LogCursorPagination()

        queryset = Log.objects.none()

        page = paginator.paginate_queryset(
            queryset,
            request,
        )

        self.assertEqual(
            page,
            [],
        )

    # ---------------------------------------------------------
    # Paginated response
    # ---------------------------------------------------------

    def test_get_paginated_response_contains_results(self):
        self._create_logs(5)

        request = Request(self.factory.get("/api/v1/monitoring/logs/"))

        paginator = LogCursorPagination()

        queryset = Log.objects.all().order_by("-created_at")

        page = paginator.paginate_queryset(
            queryset,
            request,
        )

        serializer = LogReadSerializer(
            page,
            many=True,
        )

        response = paginator.get_paginated_response(
            serializer.data,
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertIn(
            "results",
            response.data,
        )

        self.assertEqual(
            len(response.data["results"]),
            5,
        )

    # ---------------------------------------------------------
    # Invalid page_size falls back safely
    # ---------------------------------------------------------

    def test_invalid_page_size_uses_default(self):
        self._create_logs(30)

        request = Request(
            self.factory.get(
                "/api/v1/monitoring/logs/",
                {
                    "page_size": "invalid",
                },
            )
        )

        paginator = LogCursorPagination()

        queryset = Log.objects.all().order_by("-created_at")

        page = paginator.paginate_queryset(
            queryset,
            request,
        )

        self.assertEqual(
            len(page),
            paginator.page_size,
        )