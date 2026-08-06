"""
Integration tests for the Health Monitoring Orchestrator.
"""

import pytest
from unittest.mock import patch
from django.urls import reverse
from rest_framework import status


@pytest.mark.django_db
class TestHealthMonitoringWorkflow:
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.health_url = reverse("health-check")

    @patch("monitoring.services.health_service._check_celery_beat")
    @patch("monitoring.services.health_service._check_celery")
    @patch("monitoring.services.health_service._check_redis")
    @patch("monitoring.services.health_service._check_database")
    def test_health_endpoint_success(self, mock_db, mock_redis, mock_celery, mock_beat, api_client):
        """
        Verify the golden path where all infrastructure subsystems are healthy.
        """
        # 1. Mock Subsystems to report healthy
        mock_db.return_value = {"status": "healthy"}
        mock_redis.return_value = {"status": "healthy"}
        mock_celery.return_value = {"status": "healthy", "workers": 2}
        mock_beat.return_value = {"status": "unknown"}

        # 2. Invoke Health Endpoint
        response = api_client.get(self.health_url)

        # 3. Verify Response
        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "healthy"
        assert response.data["database"]["status"] == "healthy"
        assert response.data["redis"]["status"] == "healthy"
        assert response.data["celery"]["status"] == "healthy"
        # Cache control headers are essential for load balancers
        assert response.headers.get("Cache-Control") == "no-store"

    @patch("monitoring.services.health_service._check_celery_beat")
    @patch("monitoring.services.health_service._check_celery")
    @patch("monitoring.services.health_service._check_redis")
    @patch("monitoring.services.health_service._check_database")
    def test_health_endpoint_database_failure(self, mock_db, mock_redis, mock_celery, mock_beat, api_client):
        """
        Verify that a database outage safely degrades the API to a 503.
        """
        # Database is completely offline
        mock_db.return_value = {"status": "unhealthy", "error": "Connection refused"}
        
        # Other systems remain healthy
        mock_redis.return_value = {"status": "healthy"}
        mock_celery.return_value = {"status": "healthy"}
        mock_beat.return_value = {"status": "unknown"}

        response = api_client.get(self.health_url)

        # Status must explicitly be 503 so load balancers pull the instance
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert response.data["status"] == "unhealthy"
        assert response.data["database"]["status"] == "unhealthy"

    @patch("monitoring.services.health_service._check_celery_beat")
    @patch("monitoring.services.health_service._check_celery")
    @patch("monitoring.services.health_service._check_redis")
    @patch("monitoring.services.health_service._check_database")
    def test_health_endpoint_redis_failure(self, mock_db, mock_redis, mock_celery, mock_beat, api_client):
        """
        Verify that a redis outage safely degrades the API to a 503.
        """
        mock_db.return_value = {"status": "healthy"}
        mock_celery.return_value = {"status": "healthy"}
        mock_beat.return_value = {"status": "unknown"}
        
        # Redis drops off
        mock_redis.return_value = {"status": "unhealthy"}

        response = api_client.get(self.health_url)

        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert response.data["status"] == "unhealthy"
        assert response.data["redis"]["status"] == "unhealthy"

    @patch("monitoring.services.health_service._check_celery_beat")
    @patch("monitoring.services.health_service._check_celery")
    @patch("monitoring.services.health_service._check_redis")
    @patch("monitoring.services.health_service._check_database")
    def test_health_endpoint_celery_worker_failure(self, mock_db, mock_redis, mock_celery, mock_beat, api_client):
        """
        Verify that a celery worker outage safely degrades the API to a 503.
        """
        mock_db.return_value = {"status": "healthy"}
        mock_redis.return_value = {"status": "healthy"}
        mock_beat.return_value = {"status": "unknown"}
        
        # Celery drops off
        mock_celery.return_value = {"status": "unhealthy"}

        response = api_client.get(self.health_url)

        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert response.data["status"] == "unhealthy"
        assert response.data["celery"]["status"] == "unhealthy"

    @patch("monitoring.services.health_service._check_database")
    def test_health_orchestrator_catches_unhandled_exceptions(self, mock_db, api_client):
        """
        Verify that if the orchestrator internals experience a critical Python Exception,
        it catches it safely, logs it, and returns a controlled JSON 503 payload rather
        than bubbling up a raw Django 500 fatal error page.
        """
        # Force a catastrophic unhandled python exception
        mock_db.side_effect = Exception("Catastrophic kernel panic")

        # The orchestrator's global try/except MUST catch this safely
        response = api_client.get(self.health_url)

        # Still cleanly degrades to a 503 JSON payload
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert response.data["status"] == "unhealthy"
        # Database key shouldn't be present since it crashed before building it
        assert "database" not in response.data
