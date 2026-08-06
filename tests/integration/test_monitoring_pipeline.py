"""
Integration tests for the Monitoring API to Celery Pipeline handoff.
"""

import pytest
from unittest.mock import patch
from django.urls import reverse
from rest_framework import status

from monitoring.models import Log


@pytest.mark.django_db
class TestMonitoringPipelineWorkflow:
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.logs_url = reverse("logs-list")

    @patch("monitoring.views.process_log_for_alerts_task.delay")
    @patch("monitoring.views.transaction.on_commit")
    def test_api_to_celery_pipeline_handoff(self, mock_on_commit, mock_delay, authenticated_api_client, service):
        """
        Verify the complete golden path:
        API POST -> DB Write -> Transaction Commit -> Celery Dispatch.
        """
        payload = {
            "service": service.id,
            "status": "error",
            "status_code": 500,
            "response_time_ms": 1200
        }

        # 1. Ingest Log via API
        response = authenticated_api_client.post(self.logs_url, payload, format="json")
        
        # 3. Verify Database State
        assert Log.objects.filter(service=service).count() == 1
        log = Log.objects.get(service=service)
        
        # 4. Verify Transaction Hook Handoff
        assert mock_on_commit.called
        
        # Manually execute the lambda trapped by on_commit
        mock_on_commit.call_args[0][0]()
        
        # 5. Verify Celery Worker Dispatched Correctly
        assert mock_delay.called
        assert mock_delay.call_args[0][0] == log.id

    @patch("monitoring.views.process_log_for_alerts_task.delay")
    @patch("monitoring.views.transaction.on_commit")
    def test_pipeline_rejects_invalid_payload(self, mock_on_commit, mock_delay, authenticated_api_client):
        """
        Verify that a bad API payload does not corrupt the database or trigger background workers.
        """
        # Missing 'service' and 'response_time_ms'
        payload = {
            "status_code": 500,
            "endpoint": "/api/test",
        }

        # 1. Ingest Bad Log via API
        response = authenticated_api_client.post(self.logs_url, payload, format="json")
        
        # 2. Verify API Rejection
        assert response.status_code == status.HTTP_400_BAD_REQUEST

        # 3. Verify Database State (Clean)
        assert Log.objects.count() == 0
        
        # 4. Verify Celery workers completely bypassed
        assert not mock_on_commit.called
        assert not mock_delay.called
