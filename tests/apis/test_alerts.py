"""
API integration tests for alerts endpoints.
"""

import pytest
from django.urls import reverse
from rest_framework import status

from alerts.models import Alert, AlertStatus, AlertSeverity, AlertType
from tests.factories import AlertFactory


# ---------------------------------------------------------
# GET /alerts/ (List)
# ---------------------------------------------------------

@pytest.mark.django_db
class TestListAlertsAPI:
    @pytest.fixture(autouse=True)
    def setup_url(self):
        self.url = reverse("alerts-list")

    def test_list_alerts_default_filter(self, authenticated_api_client, service):
        AlertFactory(service=service, status=AlertStatus.OPEN)
        AlertFactory(service=service, status=AlertStatus.ACKNOWLEDGED)
        AlertFactory(service=service, status=AlertStatus.RESOLVED)

        response = authenticated_api_client.get(self.url)

        assert response.status_code == status.HTTP_200_OK
        assert "results" in response.data
        assert len(response.data["results"]) >= 2
        
        statuses = [alert["status"] for alert in response.data["results"]]
        assert AlertStatus.OPEN in statuses
        assert AlertStatus.ACKNOWLEDGED in statuses
        assert AlertStatus.RESOLVED not in statuses

    def test_list_alerts_explicit_status_filter(self, authenticated_api_client, service):
        AlertFactory(service=service, status=AlertStatus.OPEN)
        AlertFactory(service=service, status=AlertStatus.RESOLVED)

        response = authenticated_api_client.get(f"{self.url}?status=resolved")

        assert response.status_code == status.HTTP_200_OK
        for result in response.data["results"]:
            assert result["status"] == AlertStatus.RESOLVED

    def test_list_alerts_ordering(self, authenticated_api_client, service):
        AlertFactory(service=service, trigger_count=1)
        AlertFactory(service=service, trigger_count=10)

        response = authenticated_api_client.get(f"{self.url}?ordering=-trigger_count")

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) >= 2
        
        results = response.data["results"]
        assert results[0]["trigger_count"] >= results[1]["trigger_count"]

    def test_list_alerts_unauthenticated(self, api_client):
        response = api_client.get(self.url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ---------------------------------------------------------
# GET /alerts/{id}/ (Retrieve)
# ---------------------------------------------------------

@pytest.mark.django_db
class TestRetrieveAlertAPI:
    def test_retrieve_alert_success(self, authenticated_api_client, alert):
        url = reverse("alerts-detail", kwargs={"pk": alert.id})
        response = authenticated_api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == alert.id
        assert response.data["service_name"] == alert.service.name

    def test_retrieve_alert_not_found(self, authenticated_api_client):
        url = reverse("alerts-detail", kwargs={"pk": 99999})
        response = authenticated_api_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_retrieve_alert_unauthenticated(self, api_client, alert):
        url = reverse("alerts-detail", kwargs={"pk": alert.id})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ---------------------------------------------------------
# POST /alerts/ (Create)
# ---------------------------------------------------------

@pytest.mark.django_db
class TestCreateAlertAPI:
    @pytest.fixture(autouse=True)
    def setup_url(self):
        self.url = reverse("alerts-list")

    def test_create_alert_success(self, authenticated_api_client, service):
        payload = {
            "service": service.id,
            "alert_type": AlertType.ERROR,
            "alert_key": "error:123",
            "severity": AlertSeverity.HIGH,
            "status": AlertStatus.OPEN,
            "message": "Critical system failure"
        }

        response = authenticated_api_client.post(self.url, payload, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["alert_key"] == "error:123"
        assert response.data["status"] == AlertStatus.OPEN
        assert Alert.objects.filter(alert_key="error:123").exists()

    @pytest.mark.parametrize("payload_override, expected_error_field", [
        ({"service": None}, "service"),
        ({"severity": "invalid_severity"}, "severity"),
        ({"status": "invalid_status"}, "status"),
        ({"alert_type": "invalid_type"}, "alert_type"),
        ({"alert_key": ""}, "alert_key"),
        ({"alert_key": "invalidformat"}, "alert_key"),
    ])
    def test_create_alert_validation(self, authenticated_api_client, service, payload_override, expected_error_field):
        payload = {
            "service": service.id if payload_override.get("service", 1) is not None else None,
            "alert_type": AlertType.ERROR,
            "alert_key": "error:123",
            "severity": AlertSeverity.HIGH,
            "status": AlertStatus.OPEN,
            "message": "Critical system failure"
        }
        payload.update(payload_override)
        
        if payload["service"] is None:
            del payload["service"]

        response = authenticated_api_client.post(self.url, payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert expected_error_field in response.data

    def test_create_alert_duplicate_constraint(self, authenticated_api_client, service):
        AlertFactory(service=service, alert_type=AlertType.ERROR, alert_key="error:123", status=AlertStatus.OPEN)

        payload = {
            "service": service.id,
            "alert_type": AlertType.ERROR,
            "alert_key": "error:123",
            "severity": AlertSeverity.HIGH,
            "status": AlertStatus.OPEN,
            "message": "Another critical system failure"
        }

        response = authenticated_api_client.post(self.url, payload, format="json")

        # DRF ModelSerializer automatically enforces UniqueConstraint and returns a 400 with non_field_errors
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "non_field_errors" in response.data

    def test_create_alert_unauthenticated(self, api_client, service):
        payload = {
            "service": service.id,
            "alert_type": AlertType.ERROR,
            "alert_key": "error:123",
            "severity": AlertSeverity.HIGH,
            "status": AlertStatus.OPEN,
        }
        response = api_client.post(self.url, payload, format="json")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ---------------------------------------------------------
# POST /alerts/{id}/resolve/ (Resolve)
# ---------------------------------------------------------

@pytest.mark.django_db
class TestResolveAlertAPI:
    def test_resolve_alert_success(self, authenticated_api_client, alert):
        url = reverse("alerts-resolve", kwargs={"pk": alert.id})
        payload = {
            "status": AlertStatus.RESOLVED,
            "resolution_note": "Issue was fixed by restarting the service."
        }

        response = authenticated_api_client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == AlertStatus.RESOLVED
        assert response.data["resolution_note"] == payload["resolution_note"]
        
        alert.refresh_from_db()
        assert alert.status == AlertStatus.RESOLVED
        assert alert.resolved_at is not None

    def test_resolve_alert_missing_note_fails(self, authenticated_api_client, alert):
        url = reverse("alerts-resolve", kwargs={"pk": alert.id})
        payload = {
            "status": AlertStatus.RESOLVED
        }

        response = authenticated_api_client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "resolution_note" in response.data

    def test_resolve_alert_unauthenticated(self, api_client, alert):
        url = reverse("alerts-resolve", kwargs={"pk": alert.id})
        response = api_client.post(url, {}, format="json")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ---------------------------------------------------------
# Blocked Methods (PATCH, PUT, DELETE)
# ---------------------------------------------------------

@pytest.mark.django_db
class TestBlockedMethodsAPI:
    @pytest.mark.parametrize("method", ["put", "patch", "delete"])
    def test_blocked_methods_on_detail(self, authenticated_api_client, alert, method):
        url = reverse("alerts-detail", kwargs={"pk": alert.id})
        client_method = getattr(authenticated_api_client, method)
        
        response = client_method(url, {}, format="json")
        
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
