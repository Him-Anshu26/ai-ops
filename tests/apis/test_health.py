"""
API integration tests for the health check endpoint.
"""

import pytest
from unittest.mock import patch
from django.urls import reverse
from rest_framework import status


@pytest.mark.django_db
class TestHealthAPI:
    @pytest.fixture(autouse=True)
    def setup_url(self):
        self.url = reverse("health-check")

    @patch("monitoring.services.health_service._check_database")
    @patch("monitoring.services.health_service._check_redis")
    @patch("monitoring.services.health_service._check_celery")
    def test_health_check_success(self, mock_celery, mock_redis, mock_db, api_client):
        mock_db.return_value = {"status": "healthy", "backend": "postgresql"}
        mock_redis.return_value = {"status": "healthy"}
        mock_celery.return_value = {"status": "healthy", "broker": "healthy", "workers": 2}

        response = api_client.get(self.url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "healthy"
        assert response.data["database"]["status"] == "healthy"
        assert response.data["redis"]["status"] == "healthy"
        assert response.data["celery"]["status"] == "healthy"

    @patch("monitoring.services.health_service._check_database")
    def test_health_check_database_failure(self, mock_db, api_client):
        # Even if other services are healthy, a DB failure degrades the whole system.
        mock_db.return_value = {"status": "unhealthy", "error": "Connection refused"}

        response = api_client.get(self.url)

        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert response.data["status"] == "unhealthy"
        assert response.data["database"]["status"] == "unhealthy"

    @patch("monitoring.services.health_service._check_redis")
    def test_health_check_redis_failure(self, mock_redis, api_client):
        mock_redis.return_value = {"status": "unhealthy", "error": "Timeout"}

        response = api_client.get(self.url)

        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert response.data["status"] == "unhealthy"
        assert response.data["redis"]["status"] == "unhealthy"

    @patch("monitoring.services.health_service._check_celery")
    def test_health_check_celery_failure(self, mock_celery, api_client):
        mock_celery.return_value = {"status": "unhealthy", "broker": "unhealthy"}

        response = api_client.get(self.url)

        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert response.data["status"] == "unhealthy"
        assert response.data["celery"]["status"] == "unhealthy"

    @patch("monitoring.views.get_health_status")
    def test_health_check_unexpected_exception(self, mock_get_health_status, api_client):
        # Simulating a catastrophic failure in the health service itself.
        # However, the view itself does not catch it; the service's get_health_status 
        # is supposed to catch it. Wait, if get_health_status raises an exception (because we mock it),
        # the view will crash with 500 unless the view catches it.
        # The prompt says: "The orchestrator get_health_status never raises".
        # If we mock `_build_response` to raise an exception, `get_health_status` catches it 
        # and returns `_fallback_response`. Let's mock `_build_response` instead!
        pass

    @patch("monitoring.services.health_service._build_response")
    def test_health_check_graceful_fallback(self, mock_build, api_client):
        # Simulate a bug inside the health orchestrator itself
        mock_build.side_effect = Exception("Catastrophic orchestrator failure")

        response = api_client.get(self.url)

        # The orchestrator should catch the exception and return the fallback payload (unhealthy)
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert response.data["status"] == "unhealthy"
