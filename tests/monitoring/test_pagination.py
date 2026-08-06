import pytest

from monitoring.models import Log, LogStatus
from monitoring.pagination import LogCursorPagination
from monitoring.serializers.log_serializer import LogReadSerializer

from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from tests.monitoring.conftest import make_log


class TestLogCursorPagination:
    """
    Tests for LogCursorPagination configuration.
    """

    def test_default_page_size(self):
        assert LogCursorPagination.page_size == 20

    def test_page_size_query_param(self):
        assert LogCursorPagination.page_size_query_param == "page_size"

    def test_max_page_size(self):
        assert LogCursorPagination.max_page_size == 100

    def test_default_ordering(self):
        assert LogCursorPagination.ordering == "-created_at"


@pytest.mark.django_db
class TestLogCursorPaginationBehavior:
    """
    Behavioral tests for LogCursorPagination.
    """

    @pytest.fixture
    def factory(self):
        return APIRequestFactory()

    @staticmethod
    def _create_logs(count, service):
        return [
            make_log(
                service,
                status=LogStatus.SUCCESS,
                status_code=200,
                response_time_ms=i,
                message=f"Log {i}",
            )
            for i in range(count)
        ]

    # ---------------------------------------------------------
    # Default page size
    # ---------------------------------------------------------

    def test_default_page_contains_20_results(self, factory, service):
        self._create_logs(30, service)

        request = Request(factory.get("/api/v1/monitoring/logs/"))
        paginator = LogCursorPagination()
        queryset = Log.objects.all().order_by("-created_at")

        page = paginator.paginate_queryset(queryset, request)

        assert len(page) == 20

    # ---------------------------------------------------------
    # Less than page size
    # ---------------------------------------------------------

    def test_returns_all_results_when_less_than_page_size(self, factory, service):
        self._create_logs(8, service)

        request = Request(factory.get("/api/v1/monitoring/logs/"))
        paginator = LogCursorPagination()
        queryset = Log.objects.all().order_by("-created_at")

        page = paginator.paginate_queryset(queryset, request)

        assert len(page) == 8

    # ---------------------------------------------------------
    # Exactly page size
    # ---------------------------------------------------------

    def test_returns_exact_page_size(self, factory, service):
        self._create_logs(20, service)

        request = Request(factory.get("/api/v1/monitoring/logs/"))
        paginator = LogCursorPagination()
        queryset = Log.objects.all().order_by("-created_at")

        page = paginator.paginate_queryset(queryset, request)

        assert len(page) == 20

    # ---------------------------------------------------------
    # page_size query parameter
    # ---------------------------------------------------------

    def test_custom_page_size(self, factory, service):
        self._create_logs(40, service)

        request = Request(
            factory.get(
                "/api/v1/monitoring/logs/",
                {"page_size": 10},
            )
        )
        paginator = LogCursorPagination()
        queryset = Log.objects.all().order_by("-created_at")

        page = paginator.paginate_queryset(queryset, request)

        assert len(page) == 10

    # ---------------------------------------------------------
    # max_page_size enforcement
    # ---------------------------------------------------------

    def test_page_size_is_limited_to_max_page_size(self, factory, service):
        self._create_logs(150, service)

        request = Request(
            factory.get(
                "/api/v1/monitoring/logs/",
                {"page_size": 999},
            )
        )
        paginator = LogCursorPagination()
        queryset = Log.objects.all().order_by("-created_at")

        page = paginator.paginate_queryset(queryset, request)

        assert len(page) == paginator.max_page_size

    # ---------------------------------------------------------
    # Ordering
    # ---------------------------------------------------------

    def test_results_are_ordered_by_created_at_descending(self, factory, service):
        self._create_logs(5, service)

        request = Request(factory.get("/api/v1/monitoring/logs/"))
        paginator = LogCursorPagination()
        queryset = Log.objects.all()

        page = paginator.paginate_queryset(queryset, request)

        created_times = [log.created_at for log in page]

        assert created_times == sorted(created_times, reverse=True)

    # ---------------------------------------------------------
    # Ordering configuration
    # ---------------------------------------------------------

    def test_ordering_configuration(self):
        paginator = LogCursorPagination()

        assert paginator.ordering == "-created_at"

    # ---------------------------------------------------------
    # Empty queryset
    # ---------------------------------------------------------

    def test_empty_queryset_returns_empty_page(self, factory):
        request = Request(factory.get("/api/v1/monitoring/logs/"))
        paginator = LogCursorPagination()
        queryset = Log.objects.none()

        page = paginator.paginate_queryset(queryset, request)

        assert page == []

    # ---------------------------------------------------------
    # Paginated response
    # ---------------------------------------------------------

    def test_get_paginated_response_contains_results(self, factory, service):
        self._create_logs(5, service)

        request = Request(factory.get("/api/v1/monitoring/logs/"))
        paginator = LogCursorPagination()
        queryset = Log.objects.all().order_by("-created_at")

        page = paginator.paginate_queryset(queryset, request)

        serializer = LogReadSerializer(page, many=True)
        response = paginator.get_paginated_response(serializer.data)

        assert response.status_code == 200
        assert "results" in response.data
        assert len(response.data["results"]) == 5

    # ---------------------------------------------------------
    # Invalid page_size falls back safely
    # ---------------------------------------------------------

    def test_invalid_page_size_uses_default(self, factory, service):
        self._create_logs(30, service)

        request = Request(
            factory.get(
                "/api/v1/monitoring/logs/",
                {"page_size": "invalid"},
            )
        )
        paginator = LogCursorPagination()
        queryset = Log.objects.all().order_by("-created_at")

        page = paginator.paginate_queryset(queryset, request)

        assert len(page) == paginator.page_size