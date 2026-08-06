from unittest.mock import MagicMock, patch

import pytest

from django.urls import reverse

from rest_framework import mixins, status
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import IsAuthenticated

from django_filters.rest_framework import DjangoFilterBackend

from monitoring.models import (
    Log,
    LogStatus,
)
from monitoring.serializers.log_serializer import (
    LogReadSerializer,
    LogWriteSerializer,
)
from monitoring.views import LogViewSet
from monitoring.filters import LogFilter
from monitoring.pagination import LogCursorPagination

from tests.factories import LogFactory, ServiceFactory
from tests.monitoring.conftest import make_log


# ============================================================
# Health Check API Tests
# ============================================================

@pytest.mark.django_db
class TestHealthCheckAPIView:
    """
    Tests for HealthCheckAPIView.
    """

    @pytest.fixture()
    def url(self):
        return reverse("health-check")

    # ---------------------------------------------------------
    # Healthy response
    # ---------------------------------------------------------

    @patch("monitoring.views.get_health_status")
    def test_returns_200_when_healthy(
        self,
        mock_health,
        api_client,
        url,
    ):
        mock_health.return_value = {
            "status": "healthy",
            "database": {
                "status": "healthy",
            },
        }

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "healthy"
        assert response["Cache-Control"] == "no-store"
        mock_health.assert_called_once()

    # ---------------------------------------------------------
    # Unhealthy response
    # ---------------------------------------------------------

    @patch("monitoring.views.get_health_status")
    def test_returns_503_when_unhealthy(
        self,
        mock_health,
        api_client,
        url,
    ):
        mock_health.return_value = {
            "status": "unhealthy",
            "database": {
                "status": "unhealthy",
            },
        }

        response = api_client.get(url)

        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert response.data["status"] == "unhealthy"
        mock_health.assert_called_once()

    # ---------------------------------------------------------
    # Endpoint is public
    # ---------------------------------------------------------

    @patch("monitoring.views.get_health_status")
    def test_endpoint_does_not_require_authentication(
        self,
        mock_health,
        api_client,
        url,
    ):
        mock_health.return_value = {
            "status": "healthy",
        }

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK

    # ---------------------------------------------------------
    # Cache-Control header
    # ---------------------------------------------------------

    @patch("monitoring.views.get_health_status")
    def test_sets_cache_control_header(
        self,
        mock_health,
        api_client,
        url,
    ):
        mock_health.return_value = {
            "status": "healthy",
        }

        response = api_client.get(url)

        assert response["Cache-Control"] == "no-store"

    # ---------------------------------------------------------
    # Payload passthrough
    # ---------------------------------------------------------

    @patch("monitoring.views.get_health_status")
    def test_returns_service_payload_without_modification(
        self,
        mock_health,
        api_client,
        url,
    ):
        payload = {
            "status": "healthy",
            "hostname": "server-01",
            "environment": "development",
            "database": {
                "status": "healthy",
            },
            "redis": {
                "status": "healthy",
            },
        }

        mock_health.return_value = payload

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data == payload

    # ---------------------------------------------------------
    # Health service called exactly once
    # ---------------------------------------------------------

    @patch("monitoring.views.get_health_status")
    def test_calls_health_service_once(
        self,
        mock_health,
        api_client,
        url,
    ):
        mock_health.return_value = {
            "status": "healthy",
        }

        api_client.get(url)

        mock_health.assert_called_once()


# ============================================================
# LogViewSet Authentication Tests
# ============================================================

@pytest.mark.django_db
class TestLogAuthentication:
    """
    Authentication and permission tests for LogViewSet.
    """

    # ---------------------------------------------------------
    # List
    # ---------------------------------------------------------

    def test_list_requires_authentication(self, api_client, log_list_url):
        response = api_client.get(log_list_url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    # ---------------------------------------------------------
    # Retrieve
    # ---------------------------------------------------------

    def test_retrieve_requires_authentication(self, api_client, service):
        log = make_log(service)

        response = api_client.get(
            reverse("logs-detail", kwargs={"pk": log.pk})
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    # ---------------------------------------------------------
    # Create
    # ---------------------------------------------------------

    def test_create_requires_authentication(self, api_client, service, log_list_url):
        payload = {
            "service": service.id,
            "status": LogStatus.SUCCESS,
            "status_code": 200,
            "response_time_ms": 120,
            "message": "Backend healthy",
        }

        response = api_client.post(
            log_list_url,
            payload,
            format="json",
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    # ---------------------------------------------------------
    # Authenticated list succeeds
    # ---------------------------------------------------------

    def test_authenticated_user_can_access_list(
        self, authenticated_api_client, log_list_url
    ):
        response = authenticated_api_client.get(log_list_url)

        assert response.status_code == status.HTTP_200_OK

    # ---------------------------------------------------------
    # Authenticated retrieve succeeds
    # ---------------------------------------------------------

    def test_authenticated_user_can_retrieve_log(
        self, authenticated_api_client, service
    ):
        log = make_log(service)

        response = authenticated_api_client.get(
            reverse("logs-detail", kwargs={"pk": log.pk})
        )

        assert response.status_code == status.HTTP_200_OK

    # ---------------------------------------------------------
    # Authenticated create succeeds
    # ---------------------------------------------------------

    @patch("monitoring.views.transaction.on_commit")
    def test_authenticated_user_can_create_log(
        self,
        mock_on_commit,
        authenticated_api_client,
        service,
        log_list_url,
    ):
        payload = {
            "service": service.id,
            "status": LogStatus.SUCCESS,
            "status_code": 200,
            "response_time_ms": 95,
            "message": "Everything OK",
        }

        response = authenticated_api_client.post(
            log_list_url,
            payload,
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert Log.objects.count() == 1
        mock_on_commit.assert_called_once()


# ============================================================
# LogViewSet List API Tests
# ============================================================

@pytest.mark.django_db
class TestLogListAPI:
    """
    Tests for GET /api/v1/monitoring/logs/
    """

    # ---------------------------------------------------------
    # Empty list
    # ---------------------------------------------------------

    def test_returns_empty_list(self, authenticated_api_client, log_list_url):
        response = authenticated_api_client.get(log_list_url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["results"] == []

    # ---------------------------------------------------------
    # Multiple logs
    # ---------------------------------------------------------

    def test_returns_all_logs(
        self, authenticated_api_client, service, log_list_url
    ):
        make_log(service, message="Log 1")
        make_log(service, message="Log 2")
        make_log(service, message="Log 3")

        response = authenticated_api_client.get(log_list_url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 3

    # ---------------------------------------------------------
    # Read serializer fields
    # ---------------------------------------------------------

    def test_list_uses_read_serializer(
        self, authenticated_api_client, service, log_list_url
    ):
        log = make_log(service, message="Backend OK")

        response = authenticated_api_client.get(log_list_url)

        item = response.data["results"][0]

        assert item["id"] == log.id
        assert item["message"] == "Backend OK"
        assert item["service"] == service.id
        assert item["service_name"] == service.name
        assert "created_at" in item

    # ---------------------------------------------------------
    # Default ordering
    # ---------------------------------------------------------

    def test_latest_log_is_first(
        self, authenticated_api_client, service, log_list_url
    ):
        older = make_log(service, message="Old")
        newer = make_log(service, message="New")

        response = authenticated_api_client.get(log_list_url)

        results = response.data["results"]

        assert results[0]["id"] == newer.id
        assert results[1]["id"] == older.id

    # ---------------------------------------------------------
    # Pagination keys
    # ---------------------------------------------------------

    def test_paginated_response_contains_expected_keys(
        self, authenticated_api_client, service, log_list_url
    ):
        make_log(service)

        response = authenticated_api_client.get(log_list_url)

        assert response.status_code == status.HTTP_200_OK
        assert "results" in response.data
        assert "next" in response.data
        assert "previous" in response.data

    # ---------------------------------------------------------
    # Ordering by response time
    # ---------------------------------------------------------

    def test_can_order_by_response_time(
        self, authenticated_api_client, service, log_list_url
    ):
        make_log(service, response_time_ms=400, message="Slow")
        make_log(service, response_time_ms=100, message="Fast")

        response = authenticated_api_client.get(
            log_list_url,
            {"ordering": "response_time_ms"},
        )

        results = response.data["results"]

        assert results[0]["response_time_ms"] == 100
        assert results[1]["response_time_ms"] == 400

    # ---------------------------------------------------------
    # Reverse ordering
    # ---------------------------------------------------------

    def test_can_reverse_order_by_response_time(
        self, authenticated_api_client, service, log_list_url
    ):
        make_log(service, response_time_ms=100, message="Fast")
        make_log(service, response_time_ms=500, message="Slow")

        response = authenticated_api_client.get(
            log_list_url,
            {"ordering": "-response_time_ms"},
        )

        results = response.data["results"]

        assert results[0]["response_time_ms"] == 500
        assert results[1]["response_time_ms"] == 100


# ============================================================
# LogViewSet Retrieve API Tests
# ============================================================

@pytest.mark.django_db
class TestLogRetrieveAPI:
    """
    Tests for GET /api/v1/monitoring/logs/{id}/
    """

    # ---------------------------------------------------------
    # Existing log
    # ---------------------------------------------------------

    def test_retrieve_existing_log(
        self, authenticated_api_client, service
    ):
        log = make_log(
            service,
            message="Retrieve me",
            response_time_ms=250,
        )

        response = authenticated_api_client.get(
            reverse("logs-detail", kwargs={"pk": log.pk})
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == log.id
        assert response.data["message"] == "Retrieve me"
        assert response.data["service"] == service.id
        assert response.data["service_name"] == service.name
        assert response.data["response_time_ms"] == 250

    # ---------------------------------------------------------
    # Missing log
    # ---------------------------------------------------------

    def test_retrieve_non_existing_log_returns_404(
        self, authenticated_api_client
    ):
        response = authenticated_api_client.get(
            reverse("logs-detail", kwargs={"pk": 999999})
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    # ---------------------------------------------------------
    # Read serializer fields
    # ---------------------------------------------------------

    def test_retrieve_contains_all_read_only_fields(
        self, authenticated_api_client, service
    ):
        log = make_log(service)

        response = authenticated_api_client.get(
            reverse("logs-detail", kwargs={"pk": log.pk})
        )

        expected_fields = {
            "id",
            "service",
            "service_name",
            "status",
            "status_code",
            "response_time_ms",
            "message",
            "created_at",
        }

        assert expected_fields.issubset(response.data.keys())

    # ---------------------------------------------------------
    # Correct serializer
    # ---------------------------------------------------------

    def test_retrieve_uses_read_serializer(
        self, authenticated_api_client, service
    ):
        log = make_log(service)

        response = authenticated_api_client.get(
            reverse("logs-detail", kwargs={"pk": log.pk})
        )

        serializer = LogReadSerializer(log)

        assert set(response.data.keys()) == set(serializer.data.keys())

    # ---------------------------------------------------------
    # Retrieve preserves values
    # ---------------------------------------------------------

    def test_retrieve_returns_correct_status_fields(
        self, authenticated_api_client, service
    ):
        log = make_log(
            service,
            status=LogStatus.ERROR,
            status_code=500,
            response_time_ms=1500,
            message="Internal Server Error",
        )

        response = authenticated_api_client.get(
            reverse("logs-detail", kwargs={"pk": log.pk})
        )

        assert response.data["status"] == LogStatus.ERROR
        assert response.data["status_code"] == 500
        assert response.data["response_time_ms"] == 1500
        assert response.data["message"] == "Internal Server Error"

    # ---------------------------------------------------------
    # HTTP method
    # ---------------------------------------------------------

    def test_retrieve_only_accepts_get(
        self, authenticated_api_client, service
    ):
        log = make_log(service)

        url = reverse("logs-detail", kwargs={"pk": log.pk})

        response = authenticated_api_client.post(
            url,
            {},
            format="json",
        )

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


# ============================================================
# LogViewSet Create API Tests
# ============================================================

@pytest.mark.django_db
class TestLogCreateAPI:
    """
    Tests for POST /api/v1/monitoring/logs/
    """

    @staticmethod
    def _valid_payload(service):
        return {
            "service": service.id,
            "status": LogStatus.SUCCESS,
            "status_code": 200,
            "response_time_ms": 125,
            "message": "Everything OK",
        }

    # ---------------------------------------------------------
    # Successful create
    # ---------------------------------------------------------

    @patch("monitoring.views.transaction.on_commit")
    def test_create_log_returns_201(
        self,
        mock_on_commit,
        authenticated_api_client,
        service,
        log_list_url,
    ):
        response = authenticated_api_client.post(
            log_list_url,
            self._valid_payload(service),
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert Log.objects.count() == 1

        created = Log.objects.first()

        assert created.message == "Everything OK"
        mock_on_commit.assert_called_once()

    # ---------------------------------------------------------
    # Serializer validation
    # ---------------------------------------------------------

    def test_invalid_payload_returns_400(
        self, authenticated_api_client, service, log_list_url
    ):
        payload = {
            "service": service.id,
            "status": "",
            "message": "",
        }

        response = authenticated_api_client.post(
            log_list_url,
            payload,
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert Log.objects.count() == 0

    # ---------------------------------------------------------
    # Missing required fields
    # ---------------------------------------------------------

    def test_missing_required_fields(
        self, authenticated_api_client, log_list_url
    ):
        response = authenticated_api_client.post(
            log_list_url,
            {},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    # ---------------------------------------------------------
    # Invalid service id
    # ---------------------------------------------------------

    def test_invalid_service_returns_400(
        self, authenticated_api_client, service, log_list_url
    ):
        payload = self._valid_payload(service)
        payload["service"] = 999999

        response = authenticated_api_client.post(
            log_list_url,
            payload,
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    # ---------------------------------------------------------
    # perform_create schedules Celery task
    # ---------------------------------------------------------

    @patch("monitoring.views.process_log_for_alerts_task.delay")
    def test_celery_task_is_registered_after_commit(
        self,
        mock_delay,
        authenticated_api_client,
        service,
        log_list_url,
    ):
        callbacks = []

        def fake_on_commit(callback):
            callbacks.append(callback)

        with patch(
            "monitoring.views.transaction.on_commit",
            side_effect=fake_on_commit,
        ):
            response = authenticated_api_client.post(
                log_list_url,
                self._valid_payload(service),
                format="json",
            )

        assert response.status_code == status.HTTP_201_CREATED
        assert len(callbacks) == 1

        created_log = Log.objects.first()

        callbacks[0]()

        mock_delay.assert_called_once_with(created_log.id)

    # ---------------------------------------------------------
    # Object stored correctly
    # ---------------------------------------------------------

    @patch("monitoring.views.transaction.on_commit")
    def test_created_log_contains_correct_values(
        self,
        mock_on_commit,
        authenticated_api_client,
        service,
        log_list_url,
    ):
        payload = {
            "service": service.id,
            "status": LogStatus.ERROR,
            "status_code": 500,
            "response_time_ms": 987,
            "message": "Server crashed",
        }

        response = authenticated_api_client.post(
            log_list_url,
            payload,
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED

        log = Log.objects.get()

        assert log.status == LogStatus.ERROR
        assert log.status_code == 500
        assert log.response_time_ms == 987
        assert log.message == "Server crashed"

    # ---------------------------------------------------------
    # POST only
    # ---------------------------------------------------------

    def test_put_not_allowed(self, authenticated_api_client, service):
        log = make_log(service)

        response = authenticated_api_client.put(
            reverse("logs-detail", kwargs={"pk": log.pk}),
            {},
            format="json",
        )

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_patch_not_allowed(self, authenticated_api_client, service):
        log = make_log(service)

        response = authenticated_api_client.patch(
            reverse("logs-detail", kwargs={"pk": log.pk}),
            {},
            format="json",
        )

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_delete_not_allowed(self, authenticated_api_client, service):
        log = make_log(service)

        response = authenticated_api_client.delete(
            reverse("logs-detail", kwargs={"pk": log.pk})
        )

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


# ============================================================
# LogViewSet Internal Methods
# ============================================================

@pytest.mark.django_db
class TestLogViewSetInternalMethods:
    """
    Unit tests for LogViewSet helper methods.
    """

    # ---------------------------------------------------------
    # get_serializer_class()
    # ---------------------------------------------------------

    def test_get_serializer_returns_write_serializer_for_create(self):
        view = LogViewSet()
        view.action = "create"

        serializer = view.get_serializer_class()

        assert serializer is LogWriteSerializer

    def test_get_serializer_returns_read_serializer_for_list(self):
        view = LogViewSet()
        view.action = "list"

        serializer = view.get_serializer_class()

        assert serializer is LogReadSerializer

    def test_get_serializer_returns_read_serializer_for_retrieve(self):
        view = LogViewSet()
        view.action = "retrieve"

        serializer = view.get_serializer_class()

        assert serializer is LogReadSerializer

    def test_get_serializer_returns_read_serializer_for_unknown_action(self):
        view = LogViewSet()
        view.action = "something_else"

        serializer = view.get_serializer_class()

        assert serializer is LogReadSerializer

    @patch("monitoring.views.transaction.on_commit")
    def test_perform_create_registers_transaction_callback(
        self,
        mock_on_commit,
        service,
    ):
        serializer = MagicMock()

        log = make_log(service)

        serializer.save.return_value = log

        view = LogViewSet()

        view.perform_create(serializer)

        serializer.save.assert_called_once()
        mock_on_commit.assert_called_once()

    # ---------------------------------------------------------
    # get_queryset()
    # ---------------------------------------------------------

    def test_get_queryset_returns_all_logs(self, service):
        log1 = make_log(service, message="Log 1")
        log2 = make_log(service, message="Log 2")

        view = LogViewSet()
        view.request = MagicMock()

        queryset = view.get_queryset()

        assert log1 in queryset
        assert log2 in queryset

    def test_get_queryset_is_ordered_by_created_at_desc(self, service):
        older = make_log(service, message="Older")
        newer = make_log(service, message="Newer")

        view = LogViewSet()
        view.request = MagicMock()

        queryset = list(view.get_queryset())

        assert queryset[0].id == newer.id
        assert queryset[1].id == older.id

    def test_get_queryset_uses_select_related(self):
        view = LogViewSet()
        view.request = MagicMock()

        queryset = view.get_queryset()

        # Ensure the queryset can be evaluated without errors
        assert queryset is not None

        # Check that the expected joins are configured
        assert "service" in queryset.query.select_related
        assert "created_by" in queryset.query.select_related["service"]

    # ---------------------------------------------------------
    # View configuration
    # ---------------------------------------------------------

    def test_http_methods_are_restricted(self):
        view = LogViewSet()

        assert view.http_method_names == ["get", "post"]

    def test_permission_classes(self):
        view = LogViewSet()

        assert view.permission_classes == [IsAuthenticated]

    def test_filterset_configuration(self):
        view = LogViewSet()

        assert view.filterset_class is LogFilter

    def test_pagination_configuration(self):
        view = LogViewSet()

        assert view.pagination_class is LogCursorPagination

    def test_default_ordering_configuration(self):
        view = LogViewSet()

        assert view.ordering == ["-created_at"]

    def test_ordering_fields_configuration(self):
        view = LogViewSet()

        assert view.ordering_fields == [
            "created_at",
            "response_time_ms",
        ]


# ============================================================
# LogViewSet Integration Tests
# ============================================================

@pytest.mark.django_db
class TestLogViewSetIntegration:
    """
    Integration tests covering filtering, ordering and pagination.
    """

    # ---------------------------------------------------------
    # Filter by status
    # ---------------------------------------------------------

    def test_filter_by_status(
        self, authenticated_api_client, service, log_list_url
    ):
        make_log(service, status=LogStatus.SUCCESS, message="Success")
        make_log(service, status=LogStatus.ERROR, message="Error")

        response = authenticated_api_client.get(
            log_list_url,
            {"status": LogStatus.ERROR},
        )

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["status"] == LogStatus.ERROR

    # ---------------------------------------------------------
    # Filter by status code
    # ---------------------------------------------------------

    def test_filter_by_status_code(
        self, authenticated_api_client, service, log_list_url
    ):
        make_log(service, status_code=200)
        make_log(service, status_code=500)

        response = authenticated_api_client.get(
            log_list_url,
            {"status_code": 500},
        )

        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["status_code"] == 500

    # ---------------------------------------------------------
    # Search message
    # ---------------------------------------------------------

    def test_filter_by_message(
        self, authenticated_api_client, service, log_list_url
    ):
        make_log(service, message="Database connection failed")
        make_log(service, message="Everything OK")

        response = authenticated_api_client.get(
            log_list_url,
            {"message": "database"},
        )

        assert len(response.data["results"]) == 1
        assert "Database" in response.data["results"][0]["message"]

    # ---------------------------------------------------------
    # Response time filtering
    # ---------------------------------------------------------

    def test_filter_by_response_time(
        self, authenticated_api_client, service, log_list_url
    ):
        make_log(service, response_time_ms=100)
        make_log(service, response_time_ms=900)

        response = authenticated_api_client.get(
            log_list_url,
            {"min_response_time": 500},
        )

        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["response_time_ms"] == 900

    def test_filter_created_after(
        self, authenticated_api_client, service, log_list_url
    ):
        older = make_log(service, message="Older")
        newer = make_log(service, message="Newer")

        response = authenticated_api_client.get(
            log_list_url,
            {"created_after": older.created_at.isoformat()},
        )

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) >= 1

    def test_filter_created_before(
        self, authenticated_api_client, service, log_list_url
    ):
        older = make_log(service, message="Older")
        newer = make_log(service, message="Newer")

        response = authenticated_api_client.get(
            log_list_url,
            {"created_before": newer.created_at.isoformat()},
        )

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) >= 1

    # ---------------------------------------------------------
    # Service filter
    # ---------------------------------------------------------

    def test_filter_by_service(
        self, authenticated_api_client, service, log_list_url
    ):
        another_service = ServiceFactory(
            created_by=service.created_by,
        )

        make_log(service, message="A")

        LogFactory(
            service=another_service,
            status=LogStatus.SUCCESS,
            status_code=200,
            response_time_ms=50,
            message="B",
        )

        response = authenticated_api_client.get(
            log_list_url,
            {"service": service.id},
        )

        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["service"] == service.id


# ============================================================
# LogViewSet Configuration Tests
# ============================================================

class TestLogViewConfiguration:
    """
    Final configuration verification.
    """

    def test_queryset_exists(self):
        assert LogViewSet.queryset is not None

    def test_http_method_names(self):
        assert LogViewSet.http_method_names == ["get", "post"]

    def test_permission_classes(self):
        assert LogViewSet.permission_classes == [IsAuthenticated]

    def test_filter_backends(self):
        assert DjangoFilterBackend in LogViewSet.filter_backends
        assert OrderingFilter in LogViewSet.filter_backends

    def test_filterset(self):
        assert LogViewSet.filterset_class is LogFilter

    def test_pagination(self):
        assert LogViewSet.pagination_class is LogCursorPagination

    def test_default_ordering(self):
        assert LogViewSet.ordering == ["-created_at"]

    def test_ordering_fields(self):
        assert LogViewSet.ordering_fields == [
            "created_at",
            "response_time_ms",
        ]

    def test_only_expected_mixins_are_used(self):
        assert issubclass(LogViewSet, mixins.CreateModelMixin)
        assert issubclass(LogViewSet, mixins.ListModelMixin)
        assert issubclass(LogViewSet, mixins.RetrieveModelMixin)
        assert not hasattr(LogViewSet, "update")
        assert not hasattr(LogViewSet, "destroy")