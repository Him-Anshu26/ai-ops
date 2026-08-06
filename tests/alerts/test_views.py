import uuid

import pytest
from django.urls import reverse
from rest_framework import status
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import IsAuthenticated

from alerts.models import Alert, AlertStatus, AlertSeverity, AlertType
from alerts.views import AlertViewSet
from alerts.filters import AlertFilter
from alerts.pagination import AlertCursorPagination
from alerts.serializers.alert_serializer import (
    AlertWriteSerializer,
    AlertReadSerializer,
    AlertResolveSerializer,
)

from tests.factories import AlertFactory


# ============================================================
# Authentication Tests
# ============================================================

@pytest.mark.django_db
class TestAlertAuthentication:

    def test_list_requires_authentication(self, api_client):
        response = api_client.get(reverse("alerts-list"))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_retrieve_requires_authentication(self, api_client, service):
        alert = AlertFactory(service=service)
        response = api_client.get(reverse("alerts-detail", kwargs={"pk": alert.id}))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ============================================================
# Create API Tests
# ============================================================

@pytest.mark.django_db
class TestAlertCreateAPIView:

    def test_create_alert_successfully(self, authenticated_api_client, service):
        payload = {
            "service": service.id,
            "alert_type": AlertType.ERROR,
            "alert_key": "error:500",
            "severity": AlertSeverity.HIGH,
            "status": AlertStatus.OPEN,
            "message": "Server failed",
        }

        response = authenticated_api_client.post(
            reverse("alerts-list"),
            payload,
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["message"] == "Server failed"
        assert Alert.objects.count() == 1

    def test_create_alert_missing_required_fields(self, authenticated_api_client):
        response = authenticated_api_client.post(
            reverse("alerts-list"),
            {},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_alert_invalid_alert_type(self, authenticated_api_client, service):
        payload = {
            "service": service.id,
            "alert_type": "wrong",
            "alert_key": "error:500",
            "severity": AlertSeverity.HIGH,
            "status": AlertStatus.OPEN,
        }

        response = authenticated_api_client.post(
            reverse("alerts-list"),
            payload,
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_alert_invalid_alert_key_format(self, authenticated_api_client, service):
        payload = {
            "service": service.id,
            "alert_type": AlertType.ERROR,
            "alert_key": "wrong-format",
            "severity": AlertSeverity.HIGH,
            "status": AlertStatus.OPEN,
        }

        response = authenticated_api_client.post(
            reverse("alerts-list"),
            payload,
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_uses_write_serializer(self):
        view = AlertViewSet()
        view.action = "create"
        serializer = view.get_serializer_class()
        assert serializer is AlertWriteSerializer


# ============================================================
# List API Tests
# ============================================================

@pytest.mark.django_db
class TestAlertListAPIView:

    def test_list_returns_alerts(self, authenticated_api_client, service):
        AlertFactory(service=service, message="Alert 1", alert_key="error:1")
        AlertFactory(service=service, message="Alert 2", alert_key="error:2")

        response = authenticated_api_client.get(reverse("alerts-list"))

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 2

    def test_list_returns_only_active_alerts_by_default(self, authenticated_api_client, service):
        AlertFactory(service=service, status=AlertStatus.OPEN)
        AlertFactory(service=service, status=AlertStatus.RESOLVED)

        response = authenticated_api_client.get(reverse("alerts-list"))

        assert len(response.data["results"]) == 1

    def test_list_can_filter_resolved_alerts(self, authenticated_api_client, service):
        AlertFactory(service=service, status=AlertStatus.RESOLVED)

        response = authenticated_api_client.get(
            reverse("alerts-list"),
            {"status": AlertStatus.RESOLVED}
        )

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1

    def test_list_contains_pagination_keys(self, authenticated_api_client, service):
        AlertFactory(service=service)

        response = authenticated_api_client.get(reverse("alerts-list"))

        assert "results" in response.data
        assert "next" in response.data
        assert "previous" in response.data

    def test_list_uses_read_serializer(self, authenticated_api_client, service):
        alert = AlertFactory(service=service)

        response = authenticated_api_client.get(reverse("alerts-list"))
        serializer = AlertReadSerializer(alert)

        assert set(response.data["results"][0].keys()) == set(serializer.data.keys())


# ============================================================
# Retrieve API Tests
# ============================================================

@pytest.mark.django_db
class TestAlertRetrieveAPIView:

    def test_retrieve_existing_alert(self, authenticated_api_client, service):
        alert = AlertFactory(service=service)

        response = authenticated_api_client.get(
            reverse("alerts-detail", kwargs={"pk": alert.id})
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == alert.id

    def test_retrieve_non_existing_alert_returns_404(self, authenticated_api_client):
        response = authenticated_api_client.get(
            reverse("alerts-detail", kwargs={"pk": 999999})
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_retrieve_uses_read_serializer(self, authenticated_api_client, service):
        alert = AlertFactory(service=service)

        response = authenticated_api_client.get(
            reverse("alerts-detail", kwargs={"pk": alert.id})
        )
        serializer = AlertReadSerializer(alert)

        assert set(response.data.keys()) == set(serializer.data.keys())


# ============================================================
# Resolve Workflow Tests
# ============================================================

@pytest.mark.django_db
class TestAlertResolveAPIView:

    def test_resolve_alert_successfully(self, authenticated_api_client, service):
        alert = AlertFactory(service=service, status=AlertStatus.OPEN)

        response = authenticated_api_client.post(
            reverse("alerts-resolve", kwargs={"pk": alert.id}),
            {
                "status": AlertStatus.RESOLVED,
                "resolution_note": "Fixed issue",
            },
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        alert.refresh_from_db()
        assert alert.status == AlertStatus.RESOLVED
        assert alert.resolved_at is not None

    def test_resolve_requires_resolution_note(self, authenticated_api_client, service):
        alert = AlertFactory(service=service, status=AlertStatus.OPEN)

        response = authenticated_api_client.post(
            reverse("alerts-resolve", kwargs={"pk": alert.id}),
            {
                "status": AlertStatus.RESOLVED,
                "resolution_note": "",
            },
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_resolve_uses_resolve_serializer(self):
        view = AlertViewSet()
        view.action = "resolve"
        serializer = view.get_serializer_class()
        assert serializer is AlertResolveSerializer


# ============================================================
# HTTP Method Restrictions
# ============================================================

@pytest.mark.django_db
class TestAlertHTTPRestriction:

    def test_put_not_allowed(self, authenticated_api_client, service):
        alert = AlertFactory(service=service)

        response = authenticated_api_client.put(
            reverse("alerts-detail", kwargs={"pk": alert.id}),
            {},
            format="json",
        )
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_patch_not_allowed(self, authenticated_api_client, service):
        alert = AlertFactory(service=service)

        response = authenticated_api_client.patch(
            reverse("alerts-detail", kwargs={"pk": alert.id}),
            {},
            format="json",
        )
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_delete_not_allowed(self, authenticated_api_client, service):
        alert = AlertFactory(service=service)

        response = authenticated_api_client.delete(
            reverse("alerts-detail", kwargs={"pk": alert.id})
        )
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


# ============================================================
# ViewSet Internal Tests
# ============================================================

@pytest.mark.django_db
class TestAlertViewSetInternal:

    def test_get_serializer_returns_read_serializer_by_default(self):
        view = AlertViewSet()
        view.action = "list"
        serializer = view.get_serializer_class()
        assert serializer is AlertReadSerializer

    def test_queryset_exists(self):
        assert AlertViewSet.queryset is not None

    def test_queryset_default_ordering(self, service):
        AlertFactory(service=service, message="old")
        second = AlertFactory(service=service, message="new")

        view = AlertViewSet()
        view.request = type("Request", (), {"query_params": {}})()
        queryset = list(view.get_queryset())

        # Since ordering is -last_triggered_at, the newer one should be first.
        assert queryset[0].id == second.id

    def test_http_methods_are_restricted(self):
        assert AlertViewSet.http_method_names == ["get", "post"]

    def test_permission_classes(self):
        assert AlertViewSet.permission_classes == [IsAuthenticated]

    def test_filter_configuration(self):
        assert AlertViewSet.filterset_class is AlertFilter

    def test_pagination_configuration(self):
        assert AlertViewSet.pagination_class is AlertCursorPagination


# ============================================================
# Configuration Tests
# ============================================================

class TestAlertConfiguration:

    def test_filter_backends(self):
        assert DjangoFilterBackend in AlertViewSet.filter_backends
        assert OrderingFilter in AlertViewSet.filter_backends

    def test_ordering_fields(self):
        assert AlertViewSet.ordering_fields == [
            "created_at",
            "severity",
            "trigger_count",
            "last_triggered_at",
        ]

    def test_viewset_does_not_have_update(self):
        assert not hasattr(AlertViewSet, "update")

    def test_viewset_does_not_have_destroy(self):
        assert not hasattr(AlertViewSet, "destroy")