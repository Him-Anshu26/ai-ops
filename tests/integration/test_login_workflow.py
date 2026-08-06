"""
Integration tests for the complete login workflow.
"""

import pytest
from django.urls import reverse
from rest_framework import status

from accounts.models import UserSession
from tests.factories import UserFactory


@pytest.mark.django_db
class TestLoginWorkflow:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.login_url = reverse("login")
        self.raw_password = "Password@123"

    def test_login_workflow_success(self, api_client):
        """
        Verify the complete successful login flow:
        API -> Service -> Password Check -> Token Gen -> Session Creation.
        """
        user = UserFactory(
            is_verified=True,
            is_active=True,
            password=self.raw_password
        )

        payload = {
            "email": user.email,
            "password": self.raw_password
        }

        response = api_client.post(self.login_url, payload, format="json")

        # 1. Verify HTTP Response
        assert response.status_code == status.HTTP_200_OK
        assert "message" in response.data
        assert "tokens" in response.data
        assert "access" in response.data["tokens"]
        assert "refresh" in response.data["tokens"]

        # 2. Verify Database State
        assert UserSession.objects.filter(user=user).count() == 1
        
        session = UserSession.objects.get(user=user)
        assert session.is_active is True
        assert session.session_id is not None
        assert session.refresh_token_hash is not None

    def test_login_workflow_unverified_user(self, api_client):
        """
        Verify that an unverified user cannot log in and no session is created.
        """
        user = UserFactory(
            is_verified=False,
            is_active=True,
            password=self.raw_password
        )

        payload = {
            "email": user.email,
            "password": self.raw_password
        }

        response = api_client.post(self.login_url, payload, format="json")

        # 1. Verify HTTP Response
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.data["error"] == "Email is not verified"

        # 2. Verify Database State
        assert UserSession.objects.filter(user=user).count() == 0

    def test_login_workflow_inactive_user(self, api_client):
        """
        Verify that a disabled (inactive) user cannot log in.
        """
        user = UserFactory(
            is_verified=True,
            is_active=False,
            password=self.raw_password
        )

        payload = {
            "email": user.email,
            "password": self.raw_password
        }

        response = api_client.post(self.login_url, payload, format="json")

        # 1. Verify HTTP Response
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.data["error"] == "Account is disabled"

        # 2. Verify Database State
        assert UserSession.objects.filter(user=user).count() == 0

    def test_login_workflow_invalid_password(self, api_client):
        """
        Verify login rejection on incorrect password.
        """
        user = UserFactory(
            is_verified=True,
            is_active=True,
            password=self.raw_password
        )

        payload = {
            "email": user.email,
            "password": "WrongPassword!123"
        }

        response = api_client.post(self.login_url, payload, format="json")

        # 1. Verify HTTP Response
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.data["error"] == "Invalid credentials"

        # 2. Verify Database State
        assert UserSession.objects.filter(user=user).count() == 0

    def test_login_workflow_nonexistent_user(self, api_client):
        """
        Verify login rejection for non-existent email (anti-enumeration check).
        """
        payload = {
            "email": "doesnotexist@example.com",
            "password": "Password@123"
        }

        response = api_client.post(self.login_url, payload, format="json")

        # 1. Verify HTTP Response
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.data["error"] == "Invalid credentials"

        # 2. Verify Database State
        assert UserSession.objects.count() == 0
