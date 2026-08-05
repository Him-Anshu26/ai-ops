from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import (
    APITestCase,
)

from monitoring.models import (
    Log,
    LogStatus,
    Service,
)
from monitoring.serializers.log_serializer import (
    LogReadSerializer,
    LogWriteSerializer,
)
from monitoring.views import LogViewSet


from django_filters.rest_framework import DjangoFilterBackend

from rest_framework.filters import OrderingFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework import mixins

from monitoring.filters import LogFilter
from monitoring.pagination import LogCursorPagination


User = get_user_model()


class BaseMonitoringViewTestCase(APITestCase):
    """
    Shared setup for all monitoring view tests.
    """

    def setUp(self):
        self.user = User.objects.create_user(
            email="owner@example.com",
            password="Password@123",
            is_verified=True,
        )

        self.other_user = User.objects.create_user(
            email="another@example.com",
            password="Password@123",
            is_verified=True,
        )

        self.service = Service.objects.create(
            name="Monitoring API",
            created_by=self.user,
        )

        self.list_url = reverse("logs-list")

    def authenticate(self):
        self.client.force_authenticate(
            user=self.user,
        )

    def create_log(
        self,
        *,
        status_value=LogStatus.SUCCESS,
        status_code=200,
        response_time_ms=100,
        message="Test log",
    ):
        return Log.objects.create(
            service=self.service,
            status=status_value,
            status_code=status_code,
            response_time_ms=response_time_ms,
            message=message,
        )


# ============================================================
# Health Check API Tests
# ============================================================

class HealthCheckAPIViewTests(APITestCase):
    """
    Tests for HealthCheckAPIView.
    """

    def setUp(self):
        self.url = reverse("health-check")

    # ---------------------------------------------------------
    # Healthy response
    # ---------------------------------------------------------

    @patch("monitoring.views.get_health_status")
    def test_returns_200_when_healthy(
        self,
        mock_health,
    ):
        mock_health.return_value = {
            "status": "healthy",
            "database": {
                "status": "healthy",
            },
        }

        response = self.client.get(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["status"],
            "healthy",
        )

        self.assertEqual(
            response["Cache-Control"],
            "no-store",
        )

        mock_health.assert_called_once()

    # ---------------------------------------------------------
    # Unhealthy response
    # ---------------------------------------------------------

    @patch("monitoring.views.get_health_status")
    def test_returns_503_when_unhealthy(
        self,
        mock_health,
    ):
        mock_health.return_value = {
            "status": "unhealthy",
            "database": {
                "status": "unhealthy",
            },
        }

        response = self.client.get(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_503_SERVICE_UNAVAILABLE,
        )

        self.assertEqual(
            response.data["status"],
            "unhealthy",
        )

        mock_health.assert_called_once()

    # ---------------------------------------------------------
    # Endpoint is public
    # ---------------------------------------------------------

    @patch("monitoring.views.get_health_status")
    def test_endpoint_does_not_require_authentication(
        self,
        mock_health,
    ):
        mock_health.return_value = {
            "status": "healthy",
        }

        response = self.client.get(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

    # ---------------------------------------------------------
    # Cache-Control header
    # ---------------------------------------------------------

    @patch("monitoring.views.get_health_status")
    def test_sets_cache_control_header(
        self,
        mock_health,
    ):
        mock_health.return_value = {
            "status": "healthy",
        }

        response = self.client.get(self.url)

        self.assertEqual(
            response["Cache-Control"],
            "no-store",
        )

    # ---------------------------------------------------------
    # Payload passthrough
    # ---------------------------------------------------------

    @patch("monitoring.views.get_health_status")
    def test_returns_service_payload_without_modification(
        self,
        mock_health,
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

        response = self.client.get(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data,
            payload,
        )

    # ---------------------------------------------------------
    # Health service called exactly once
    # ---------------------------------------------------------

    @patch("monitoring.views.get_health_status")
    def test_calls_health_service_once(
        self,
        mock_health,
    ):
        mock_health.return_value = {
            "status": "healthy",
        }

        self.client.get(self.url)

        mock_health.assert_called_once()


# ============================================================
# LogViewSet Authentication Tests
# ============================================================

class LogAuthenticationTests(BaseMonitoringViewTestCase):
    """
    Authentication and permission tests for LogViewSet.
    """

    # ---------------------------------------------------------
    # List
    # ---------------------------------------------------------

    def test_list_requires_authentication(self):
        response = self.client.get(
            self.list_url,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    # ---------------------------------------------------------
    # Retrieve
    # ---------------------------------------------------------

    def test_retrieve_requires_authentication(self):
        log = self.create_log()

        response = self.client.get(
            reverse(
                "logs-detail",
                kwargs={
                    "pk": log.pk,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    # ---------------------------------------------------------
    # Create
    # ---------------------------------------------------------

    def test_create_requires_authentication(self):
        payload = {
            "service": self.service.id,
            "status": LogStatus.SUCCESS,
            "status_code": 200,
            "response_time_ms": 120,
            "message": "Backend healthy",
        }

        response = self.client.post(
            self.list_url,
            payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    # ---------------------------------------------------------
    # Authenticated list succeeds
    # ---------------------------------------------------------

    def test_authenticated_user_can_access_list(self):
        self.authenticate()

        response = self.client.get(
            self.list_url,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

    # ---------------------------------------------------------
    # Authenticated retrieve succeeds
    # ---------------------------------------------------------

    def test_authenticated_user_can_retrieve_log(self):
        self.authenticate()

        log = self.create_log()

        response = self.client.get(
            reverse(
                "logs-detail",
                kwargs={
                    "pk": log.pk,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

    # ---------------------------------------------------------
    # Authenticated create succeeds
    # ---------------------------------------------------------

    @patch("monitoring.views.transaction.on_commit")
    def test_authenticated_user_can_create_log(
        self,
        mock_on_commit,
    ):
        self.authenticate()

        payload = {
            "service": self.service.id,
            "status": LogStatus.SUCCESS,
            "status_code": 200,
            "response_time_ms": 95,
            "message": "Everything OK",
        }

        response = self.client.post(
            self.list_url,
            payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertEqual(
            Log.objects.count(),
            1,
        )

        mock_on_commit.assert_called_once()



# ============================================================
# LogViewSet List API Tests
# ============================================================

class LogListAPIViewTests(BaseMonitoringViewTestCase):
    """
    Tests for GET /api/v1/monitoring/logs/
    """

    def setUp(self):
        super().setUp()
        self.authenticate()

    # ---------------------------------------------------------
    # Empty list
    # ---------------------------------------------------------

    def test_returns_empty_list(self):
        response = self.client.get(
            self.list_url,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["results"],
            [],
        )

    # ---------------------------------------------------------
    # Multiple logs
    # ---------------------------------------------------------

    def test_returns_all_logs(self):
        self.create_log(message="Log 1")
        self.create_log(message="Log 2")
        self.create_log(message="Log 3")

        response = self.client.get(
            self.list_url,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            len(response.data["results"]),
            3,
        )

    # ---------------------------------------------------------
    # Read serializer fields
    # ---------------------------------------------------------

    def test_list_uses_read_serializer(self):
        log = self.create_log(
            message="Backend OK",
        )

        response = self.client.get(
            self.list_url,
        )

        item = response.data["results"][0]

        self.assertEqual(
            item["id"],
            log.id,
        )

        self.assertEqual(
            item["message"],
            "Backend OK",
        )

        self.assertEqual(
            item["service"],
            self.service.id,
        )

        self.assertEqual(
            item["service_name"],
            self.service.name,
        )

        self.assertIn(
            "created_at",
            item,
        )

    # ---------------------------------------------------------
    # Default ordering
    # ---------------------------------------------------------

    def test_latest_log_is_first(self):
        older = self.create_log(
            message="Old",
        )

        newer = self.create_log(
            message="New",
        )

        response = self.client.get(
            self.list_url,
        )

        results = response.data["results"]

        self.assertEqual(
            results[0]["id"],
            newer.id,
        )

        self.assertEqual(
            results[1]["id"],
            older.id,
        )

    # ---------------------------------------------------------
    # Pagination keys
    # ---------------------------------------------------------

    def test_paginated_response_contains_expected_keys(self):
        self.create_log()

        response = self.client.get(
            self.list_url,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertIn(
            "results",
            response.data,
        )

        self.assertIn(
            "next",
            response.data,
        )

        self.assertIn(
            "previous",
            response.data,
        )

    # ---------------------------------------------------------
    # Ordering by response time
    # ---------------------------------------------------------

    def test_can_order_by_response_time(self):
        self.create_log(
            response_time_ms=400,
            message="Slow",
        )

        self.create_log(
            response_time_ms=100,
            message="Fast",
        )

        response = self.client.get(
            self.list_url,
            {
                "ordering": "response_time_ms",
            },
        )

        results = response.data["results"]

        self.assertEqual(
            results[0]["response_time_ms"],
            100,
        )

        self.assertEqual(
            results[1]["response_time_ms"],
            400,
        )

    # ---------------------------------------------------------
    # Reverse ordering
    # ---------------------------------------------------------

    def test_can_reverse_order_by_response_time(self):
        self.create_log(
            response_time_ms=100,
            message="Fast",
        )

        self.create_log(
            response_time_ms=500,
            message="Slow",
        )

        response = self.client.get(
            self.list_url,
            {
                "ordering": "-response_time_ms",
            },
        )

        results = response.data["results"]

        self.assertEqual(
            results[0]["response_time_ms"],
            500,
        )

        self.assertEqual(
            results[1]["response_time_ms"],
            100,
        )



# ============================================================
# LogViewSet Retrieve API Tests
# ============================================================

class LogRetrieveAPIViewTests(BaseMonitoringViewTestCase):
    """
    Tests for GET /api/v1/monitoring/logs/{id}/
    """

    def setUp(self):
        super().setUp()
        self.authenticate()

    # ---------------------------------------------------------
    # Existing log
    # ---------------------------------------------------------

    def test_retrieve_existing_log(self):
        log = self.create_log(
            message="Retrieve me",
            response_time_ms=250,
        )

        response = self.client.get(
            reverse(
                "logs-detail",
                kwargs={
                    "pk": log.pk,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["id"],
            log.id,
        )

        self.assertEqual(
            response.data["message"],
            "Retrieve me",
        )

        self.assertEqual(
            response.data["service"],
            self.service.id,
        )

        self.assertEqual(
            response.data["service_name"],
            self.service.name,
        )

        self.assertEqual(
            response.data["response_time_ms"],
            250,
        )

    # ---------------------------------------------------------
    # Missing log
    # ---------------------------------------------------------

    def test_retrieve_non_existing_log_returns_404(self):
        response = self.client.get(
            reverse(
                "logs-detail",
                kwargs={
                    "pk": 999999,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    # ---------------------------------------------------------
    # Read serializer fields
    # ---------------------------------------------------------

    def test_retrieve_contains_all_read_only_fields(self):
        log = self.create_log()

        response = self.client.get(
            reverse(
                "logs-detail",
                kwargs={
                    "pk": log.pk,
                },
            )
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

        self.assertTrue(
            expected_fields.issubset(
                response.data.keys(),
            )
        )

    # ---------------------------------------------------------
    # Correct serializer
    # ---------------------------------------------------------

    def test_retrieve_uses_read_serializer(self):
        log = self.create_log()

        response = self.client.get(
            reverse(
                "logs-detail",
                kwargs={
                    "pk": log.pk,
                },
            )
        )

        serializer = LogReadSerializer(log)

        self.assertEqual(
            set(response.data.keys()),
            set(serializer.data.keys()),
        )

    # ---------------------------------------------------------
    # Retrieve preserves values
    # ---------------------------------------------------------

    def test_retrieve_returns_correct_status_fields(self):
        log = self.create_log(
            status_value=LogStatus.ERROR,
            status_code=500,
            response_time_ms=1500,
            message="Internal Server Error",
        )

        response = self.client.get(
            reverse(
                "logs-detail",
                kwargs={
                    "pk": log.pk,
                },
            )
        )

        self.assertEqual(
            response.data["status"],
            LogStatus.ERROR,
        )

        self.assertEqual(
            response.data["status_code"],
            500,
        )

        self.assertEqual(
            response.data["response_time_ms"],
            1500,
        )

        self.assertEqual(
            response.data["message"],
            "Internal Server Error",
        )

    # ---------------------------------------------------------
    # HTTP method
    # ---------------------------------------------------------

    def test_retrieve_only_accepts_get(self):
        log = self.create_log()

        url = reverse(
            "logs-detail",
            kwargs={
                "pk": log.pk,
            },
        )

        response = self.client.post(
            url,
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )


# ============================================================
# LogViewSet Create API Tests
# ============================================================

class LogCreateAPIViewTests(BaseMonitoringViewTestCase):
    """
    Tests for POST /api/v1/monitoring/logs/
    """

    def setUp(self):
        super().setUp()
        self.authenticate()

    def _valid_payload(self):
        return {
            "service": self.service.id,
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
    ):
        response = self.client.post(
            self.list_url,
            self._valid_payload(),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertEqual(
            Log.objects.count(),
            1,
        )

        created = Log.objects.first()

        self.assertEqual(
            created.message,
            "Everything OK",
        )

        mock_on_commit.assert_called_once()

    # ---------------------------------------------------------
    # Serializer validation
    # ---------------------------------------------------------

    def test_invalid_payload_returns_400(self):
        payload = {
            "service": self.service.id,
            "status": "",
            "message": "",
        }

        response = self.client.post(
            self.list_url,
            payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertEqual(
            Log.objects.count(),
            0,
        )

    # ---------------------------------------------------------
    # Missing required fields
    # ---------------------------------------------------------

    def test_missing_required_fields(self):
        response = self.client.post(
            self.list_url,
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    # ---------------------------------------------------------
    # Invalid service id
    # ---------------------------------------------------------

    def test_invalid_service_returns_400(self):
        payload = self._valid_payload()
        payload["service"] = 999999

        response = self.client.post(
            self.list_url,
            payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    # ---------------------------------------------------------
    # perform_create schedules Celery task
    # ---------------------------------------------------------

    @patch("monitoring.views.process_log_for_alerts_task.delay")
    def test_celery_task_is_registered_after_commit(
        self,
        mock_delay,
    ):
        callbacks = []

        def fake_on_commit(callback):
            callbacks.append(callback)

        with patch(
            "monitoring.views.transaction.on_commit",
            side_effect=fake_on_commit,
        ):
            response = self.client.post(
                self.list_url,
                self._valid_payload(),
                format="json",
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertEqual(
            len(callbacks),
            1,
        )

        created_log = Log.objects.first()

        callbacks[0]()

        mock_delay.assert_called_once_with(
            created_log.id,
        )

    # ---------------------------------------------------------
    # Object stored correctly
    # ---------------------------------------------------------

    @patch("monitoring.views.transaction.on_commit")
    def test_created_log_contains_correct_values(
        self,
        mock_on_commit,
    ):
        payload = {
            "service": self.service.id,
            "status": LogStatus.ERROR,
            "status_code": 500,
            "response_time_ms": 987,
            "message": "Server crashed",
        }

        response = self.client.post(
            self.list_url,
            payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        log = Log.objects.get()

        self.assertEqual(
            log.status,
            LogStatus.ERROR,
        )

        self.assertEqual(
            log.status_code,
            500,
        )

        self.assertEqual(
            log.response_time_ms,
            987,
        )

        self.assertEqual(
            log.message,
            "Server crashed",
        )

    # ---------------------------------------------------------
    # POST only
    # ---------------------------------------------------------

    def test_put_not_allowed(self):
        log = self.create_log()

        response = self.client.put(
            reverse(
                "logs-detail",
                kwargs={
                    "pk": log.pk,
                },
            ),
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def test_patch_not_allowed(self):
        log = self.create_log()

        response = self.client.patch(
            reverse(
                "logs-detail",
                kwargs={
                    "pk": log.pk,
                },
            ),
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def test_delete_not_allowed(self):
        log = self.create_log()

        response = self.client.delete(
            reverse(
                "logs-detail",
                kwargs={
                    "pk": log.pk,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )


# ============================================================
# LogViewSet Internal Methods
# ============================================================

class LogViewSetInternalMethodTests(BaseMonitoringViewTestCase):
    """
    Unit tests for LogViewSet helper methods.
    """

    def setUp(self):
        super().setUp()
        self.authenticate()

    # ---------------------------------------------------------
    # get_serializer_class()
    # ---------------------------------------------------------

    def test_get_serializer_returns_write_serializer_for_create(self):
        view = LogViewSet()
        view.action = "create"

        serializer = view.get_serializer_class()

        self.assertIs(
            serializer,
            LogWriteSerializer,
        )

    def test_get_serializer_returns_read_serializer_for_list(self):
        view = LogViewSet()
        view.action = "list"

        serializer = view.get_serializer_class()

        self.assertIs(
            serializer,
            LogReadSerializer,
        )

    def test_get_serializer_returns_read_serializer_for_retrieve(self):
        view = LogViewSet()
        view.action = "retrieve"

        serializer = view.get_serializer_class()

        self.assertIs(
            serializer,
            LogReadSerializer,
        )

    def test_get_serializer_returns_read_serializer_for_unknown_action(self):
        view = LogViewSet()
        view.action = "something_else"

        serializer = view.get_serializer_class()

        self.assertIs(
            serializer,
            LogReadSerializer,
        )


    @patch("monitoring.views.transaction.on_commit")
    def test_perform_create_registers_transaction_callback(
        self,
        mock_on_commit,
    ):
        serializer = MagicMock()

        log = self.create_log()

        serializer.save.return_value = log

        view = LogViewSet()

        view.perform_create(serializer)

        serializer.save.assert_called_once()

        mock_on_commit.assert_called_once()

    # ---------------------------------------------------------
    # get_queryset()
    # ---------------------------------------------------------

    def test_get_queryset_returns_all_logs(self):
        log1 = self.create_log(message="Log 1")
        log2 = self.create_log(message="Log 2")

        view = LogViewSet()
        view.request = MagicMock()

        queryset = view.get_queryset()

        self.assertIn(log1, queryset)
        self.assertIn(log2, queryset)

    def test_get_queryset_is_ordered_by_created_at_desc(self):
        older = self.create_log(message="Older")
        newer = self.create_log(message="Newer")

        view = LogViewSet()
        view.request = MagicMock()

        queryset = list(view.get_queryset())

        self.assertEqual(
            queryset[0].id,
            newer.id,
        )

        self.assertEqual(
            queryset[1].id,
            older.id,
        )

    def test_get_queryset_uses_select_related(self):
        view = LogViewSet()
        view.request = MagicMock()

        queryset = view.get_queryset()

        # Ensure the queryset can be evaluated without errors
        self.assertIsNotNone(queryset)

        # Check that the expected joins are configured
        self.assertIn(
            "service",
            queryset.query.select_related,
        )

        self.assertIn(
            "created_by",
            queryset.query.select_related["service"],
        )

    # ---------------------------------------------------------
    # View configuration
    # ---------------------------------------------------------

    def test_http_methods_are_restricted(self):
        view = LogViewSet()

        self.assertEqual(
            view.http_method_names,
            ["get", "post"],
        )

    def test_permission_classes(self):
        view = LogViewSet()

        self.assertEqual(
            view.permission_classes,
            [IsAuthenticated],
        )

    def test_filterset_configuration(self):
        view = LogViewSet()

        self.assertIs(
            view.filterset_class,
            LogFilter,
        )

    def test_pagination_configuration(self):
        view = LogViewSet()

        self.assertIs(
            view.pagination_class,
            LogCursorPagination,
        )

    def test_default_ordering_configuration(self):
        view = LogViewSet()

        self.assertEqual(
            view.ordering,
            ["-created_at"],
        )

    def test_ordering_fields_configuration(self):
        view = LogViewSet()

        self.assertEqual(
            view.ordering_fields,
            [
                "created_at",
                "response_time_ms",
            ],
        )



# ============================================================
# LogViewSet Integration Tests
# ============================================================

class LogViewSetIntegrationTests(BaseMonitoringViewTestCase):
    """
    Integration tests covering filtering, ordering and pagination.
    """

    def setUp(self):
        super().setUp()
        self.authenticate()

    # ---------------------------------------------------------
    # Filter by status
    # ---------------------------------------------------------

    def test_filter_by_status(self):
        self.create_log(
            status_value=LogStatus.SUCCESS,
            message="Success",
        )

        self.create_log(
            status_value=LogStatus.ERROR,
            message="Error",
        )

        response = self.client.get(
            self.list_url,
            {
                "status": LogStatus.ERROR,
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            len(response.data["results"]),
            1,
        )

        self.assertEqual(
            response.data["results"][0]["status"],
            LogStatus.ERROR,
        )

    # ---------------------------------------------------------
    # Filter by status code
    # ---------------------------------------------------------

    def test_filter_by_status_code(self):
        self.create_log(status_code=200)
        self.create_log(status_code=500)

        response = self.client.get(
            self.list_url,
            {
                "status_code": 500,
            },
        )

        self.assertEqual(
            len(response.data["results"]),
            1,
        )

        self.assertEqual(
            response.data["results"][0]["status_code"],
            500,
        )

    # ---------------------------------------------------------
    # Search message
    # ---------------------------------------------------------

    def test_filter_by_message(self):
        self.create_log(message="Database connection failed")
        self.create_log(message="Everything OK")

        response = self.client.get(
            self.list_url,
            {
                "message": "database",
            },
        )

        self.assertEqual(
            len(response.data["results"]),
            1,
        )

        self.assertIn(
            "Database",
            response.data["results"][0]["message"],
        )

    # ---------------------------------------------------------
    # Response time filtering
    # ---------------------------------------------------------

    def test_filter_by_response_time(self):
        self.create_log(response_time_ms=100)
        self.create_log(response_time_ms=900)

        response = self.client.get(
            self.list_url,
            {
                "min_response_time": 500,
            },
        )

        self.assertEqual(
            len(response.data["results"]),
            1,
        )

        self.assertEqual(
            response.data["results"][0]["response_time_ms"],
            900,
        )

    def test_filter_created_after(self):
        older = self.create_log(
            message="Older",
        )

        newer = self.create_log(
            message="Newer",
        )

        response = self.client.get(
            self.list_url,
            {
                "created_after": older.created_at.isoformat(),
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertGreaterEqual(
            len(response.data["results"]),
            1,
        )


    def test_filter_created_before(self):
        older = self.create_log(
            message="Older",
        )

        newer = self.create_log(
            message="Newer",
        )

        response = self.client.get(
            self.list_url,
            {
                "created_before": newer.created_at.isoformat(),
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertGreaterEqual(
            len(response.data["results"]),
            1,
        )

    # ---------------------------------------------------------
    # Service filter
    # ---------------------------------------------------------

    def test_filter_by_service(self):
        another_service = Service.objects.create(
            name="Payments",
            created_by=self.user,
        )

        self.create_log(message="A")

        Log.objects.create(
            service=another_service,
            status=LogStatus.SUCCESS,
            status_code=200,
            response_time_ms=50,
            message="B",
        )

        response = self.client.get(
            self.list_url,
            {
                "service": self.service.id,
            },
        )

        self.assertEqual(
            len(response.data["results"]),
            1,
        )

        self.assertEqual(
            response.data["results"][0]["service"],
            self.service.id,
        )


# ============================================================
# LogViewSet Configuration Tests
# ============================================================

class LogViewConfigurationTests(TestCase):
    """
    Final configuration verification.
    """

    def test_queryset_exists(self):
        self.assertIsNotNone(
            LogViewSet.queryset,
        )

    def test_http_method_names(self):
        self.assertEqual(
            LogViewSet.http_method_names,
            ["get", "post"],
        )

    def test_permission_classes(self):
        self.assertEqual(
            LogViewSet.permission_classes,
            [IsAuthenticated],
        )

    def test_filter_backends(self):
        self.assertIn(
            DjangoFilterBackend,
            LogViewSet.filter_backends,
        )

        self.assertIn(
            OrderingFilter,
            LogViewSet.filter_backends,
        )

    def test_filterset(self):
        self.assertIs(
            LogViewSet.filterset_class,
            LogFilter,
        )

    def test_pagination(self):
        self.assertIs(
            LogViewSet.pagination_class,
            LogCursorPagination,
        )

    def test_default_ordering(self):
        self.assertEqual(
            LogViewSet.ordering,
            ["-created_at"],
        )

    def test_ordering_fields(self):
        self.assertEqual(
            LogViewSet.ordering_fields,
            [
                "created_at",
                "response_time_ms",
            ],
        )

    def test_only_expected_mixins_are_used(self):
        self.assertTrue(
            issubclass(
                LogViewSet,
                mixins.CreateModelMixin,
            )
        )

        self.assertTrue(
            issubclass(
                LogViewSet,
                mixins.ListModelMixin,
            )
        )

        self.assertTrue(
            issubclass(
                LogViewSet,
                mixins.RetrieveModelMixin,
            )
        )

        self.assertFalse(
            hasattr(
                LogViewSet,
                "update",
            )
        )

        self.assertFalse(
            hasattr(
                LogViewSet,
                "destroy",
            )
        )