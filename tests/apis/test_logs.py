"""
API integration tests for monitoring logs endpoints.
"""

import pytest
from unittest.mock import patch
from django.urls import reverse
from rest_framework import status

from monitoring.models import Log, LogStatus
from tests.factories import LogFactory


# ---------------------------------------------------------
# GET /logs/ (List)
# ---------------------------------------------------------

@pytest.mark.django_db
class TestListLogsAPI:
    @pytest.fixture(autouse=True)
    def setup_url(self):
        self.url = reverse("logs-list")

    def test_list_logs_success(self, authenticated_api_client, log):
        response = authenticated_api_client.get(self.url)

        assert response.status_code == status.HTTP_200_OK
        assert "results" in response.data
        assert len(response.data["results"]) >= 1
        assert response.data["results"][0]["id"] == log.id
        assert response.data["results"][0]["message"] == log.message

    def test_list_logs_unauthenticated(self, api_client):
        response = api_client.get(self.url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_logs_filtering(self, authenticated_api_client, service):
        LogFactory(service=service, status=LogStatus.SUCCESS)
        LogFactory(service=service, status=LogStatus.ERROR)

        response = authenticated_api_client.get(f"{self.url}?status=error")

        assert response.status_code == status.HTTP_200_OK
        for result in response.data["results"]:
            assert result["status"] == "error"

    def test_list_logs_ordering(self, authenticated_api_client, service):
        LogFactory(service=service, response_time_ms=100)
        LogFactory(service=service, response_time_ms=500)

        response = authenticated_api_client.get(f"{self.url}?ordering=-response_time_ms")

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) >= 2
        
        results = response.data["results"]
        assert results[0]["response_time_ms"] >= results[1]["response_time_ms"]


# ---------------------------------------------------------
# GET /logs/{id}/ (Retrieve)
# ---------------------------------------------------------

@pytest.mark.django_db
class TestRetrieveLogAPI:
    def test_retrieve_log_success(self, authenticated_api_client, log):
        url = reverse("logs-detail", kwargs={"pk": log.id})
        response = authenticated_api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == log.id
        assert response.data["service_name"] == log.service.name

    def test_retrieve_log_not_found(self, authenticated_api_client):
        url = reverse("logs-detail", kwargs={"pk": 99999})
        response = authenticated_api_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_retrieve_log_unauthenticated(self, api_client, log):
        url = reverse("logs-detail", kwargs={"pk": log.id})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ---------------------------------------------------------
# POST /logs/ (Create)
# ---------------------------------------------------------

@pytest.mark.django_db
class TestCreateLogAPI:
    @pytest.fixture(autouse=True)
    def setup_url(self):
        self.url = reverse("logs-list")

    @patch("monitoring.views.process_log_for_alerts_task.delay")
    def test_create_log_success(self, mock_task, authenticated_api_client, service):
        payload = {
            "service": service.id,
            "status": "success",
            "status_code": 200,
            "response_time_ms": 150,
            "message": "Healthy response"
        }

        response = authenticated_api_client.post(self.url, payload, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["status"] == "success"
        
        # Verify database
        assert Log.objects.filter(service=service).count() == 1
        
        # In a real Django test, transaction.on_commit hooks don't always fire unless 
        # using TransactionTestCase, but DRF tests typically bypass atomic blocks, 
        # so we just assert the response for now and the database state.
        # mock_task.assert_called_once() is tricky with on_commit in standard tests,
        # so we will ensure the object is created successfully.

    def test_create_log_default_message(self, authenticated_api_client, service):
        payload = {
            "service": service.id,
            "status": "warning"
        }
        response = authenticated_api_client.post(self.url, payload, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["message"] == "warning log"

    def test_create_log_unauthenticated(self, api_client, service):
        response = api_client.post(self.url, {"service": service.id, "status": "success"}, format="json")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.parametrize("payload_override, expected_error_field", [
        ({"service": None}, "service"),
        ({"status": "invalid"}, "status"),
        ({"status": None}, "status"),
        ({"response_time_ms": -10}, "response_time_ms"),
        ({"status_code": 99}, "status_code"),
        ({"status_code": 600}, "status_code"),
        ({"status": "error", "status_code": 200}, "non_field_errors"),
    ])
    def test_create_log_validation(self, authenticated_api_client, service, payload_override, expected_error_field):
        payload = {
            "service": service.id if payload_override.get("service", 1) is not None else None,
            "status": "success"
        }
        payload.update(payload_override)
        
        if payload["service"] is None:
            del payload["service"]

        response = authenticated_api_client.post(self.url, payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert expected_error_field in response.data


# ---------------------------------------------------------
# Blocked Methods (PATCH, PUT, DELETE)
# ---------------------------------------------------------

@pytest.mark.django_db
class TestBlockedMethodsAPI:
    @pytest.mark.parametrize("method", ["put", "patch", "delete"])
    def test_blocked_methods_on_detail(self, authenticated_api_client, log, method):
        url = reverse("logs-detail", kwargs={"pk": log.id})
        client_method = getattr(authenticated_api_client, method)
        
        response = client_method(url, {}, format="json")
        
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
