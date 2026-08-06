"""
Integration tests for Global Permission boundaries.
"""

import pytest
from django.urls import reverse
from rest_framework import status


@pytest.mark.django_db
class TestPermissionWorkflow:
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.logs_url = reverse("logs-list")
        self.alerts_url = reverse("alerts-list")
        self.health_url = reverse("health-check")

    def test_authenticated_access_to_protected_resource(self, authenticated_api_client):
        """
        Verify that requests with a valid Bearer token can successfully access
        protected endpoints.
        """
        response = authenticated_api_client.get(self.logs_url)
        assert response.status_code == status.HTTP_200_OK

        response = authenticated_api_client.get(self.alerts_url)
        assert response.status_code == status.HTTP_200_OK

    def test_unauthenticated_access_rejected(self, api_client):
        """
        Verify that requests entirely missing the Authorization header are strictly rejected
        before ever hitting the View layer.
        """
        # GET request rejection
        get_response = api_client.get(self.logs_url)
        assert get_response.status_code == status.HTTP_401_UNAUTHORIZED
        assert get_response.data["detail"] == "Authentication credentials were not provided."

        # POST request rejection (Telemetry spoofing prevention)
        post_response = api_client.post(self.logs_url, {"status": "error"}, format="json")
        assert post_response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_invalid_token_format_rejected(self, api_client):
        """
        Verify that maliciously formatted, expired, or garbage tokens are caught
        by SimpleJWT and safely rejected.
        """
        api_client.credentials(HTTP_AUTHORIZATION="Bearer garbage.token.format")
        
        response = api_client.get(self.alerts_url)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.data["code"] == "token_not_valid"

    def test_unprotected_endpoints_remain_accessible(self, api_client):
        """
        Verify that infrastructure endpoints explicitly decorated with AllowAny
        bypass the JWT requirement entirely.
        """
        response = api_client.get(self.health_url)
        
        # Must NOT return 401
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_503_SERVICE_UNAVAILABLE]
