"""
API integration tests for authentication endpoints.

Tests real HTTP API behavior:
- Register
- Login
- Refresh token
- Logout
"""

import pytest
from unittest.mock import patch
from django.urls import reverse
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import User
from tests.factories import UserFactory


# ---------------------------------------------------------
# Register API Tests
# ---------------------------------------------------------

@pytest.mark.django_db
class TestRegisterAPI:
    @pytest.fixture(autouse=True)
    def setup_url(self):
        self.url = reverse("register")
        self.payload = {
            "email": "user@example.com",
            "password": "StrongPassword@123",
            "first_name": "Himanshu",
        }

    @patch("accounts.views.send_verification_email")
    def test_register_success(self, mock_email, api_client):
        response = api_client.post(self.url, self.payload, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["message"] == (
            "User registered successfully. "
            "Please verify your email."
        )
        assert User.objects.filter(email="user@example.com").exists()
        mock_email.assert_called_once()

    @pytest.mark.parametrize("invalid_payload", [
        {},
        {"email": "user@example.com"},
        {"password": "StrongPassword@123"},
    ])
    def test_register_invalid_payload(self, api_client, invalid_payload):
        response = api_client.post(self.url, invalid_payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_duplicate_email(self, api_client):
        UserFactory(email="user@example.com", password="Password@123")
        response = api_client.post(self.url, self.payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "email" in response.data


# ---------------------------------------------------------
# Login API Tests
# ---------------------------------------------------------

@pytest.mark.django_db
class TestLoginAPI:
    @pytest.fixture(autouse=True)
    def setup_url(self):
        self.url = reverse("login")
        self.password = "Password@123"

    def test_login_success(self, api_client):
        user = UserFactory(password=self.password)
        
        response = api_client.post(
            self.url,
            {"email": user.email, "password": self.password},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert "tokens" in response.data
        assert "access" in response.data["tokens"]
        assert "refresh" in response.data["tokens"]

    @pytest.mark.parametrize("payload", [
        {"email": "unknown@example.com", "password": "Password@123"},
        {"email": "user@example.com", "password": "WrongPassword"},
    ])
    def test_login_invalid_credentials(self, api_client, payload):
        UserFactory(email="user@example.com", password="Password@123")
        
        response = api_client.post(self.url, payload, format="json")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "error" in response.data

    def test_login_missing_fields(self, api_client):
        response = api_client.post(self.url, {}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST


# ---------------------------------------------------------
# Refresh Token API Tests
# ---------------------------------------------------------

@pytest.mark.django_db
class TestRefreshTokenAPI:
    @pytest.fixture(autouse=True)
    def setup_url(self):
        self.url = reverse("refresh")

    def test_refresh_invalid_token(self, api_client):
        response = api_client.post(
            self.url,
            {"refresh": "invalid-token"},
            format="json",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_refresh_missing_token(self, api_client):
        response = api_client.post(self.url, {}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST


# ---------------------------------------------------------
# Logout API Tests
# ---------------------------------------------------------

@pytest.mark.django_db
class TestLogoutAPI:
    @pytest.fixture(autouse=True)
    def setup_url(self):
        self.url = reverse("logout")

    def test_logout_without_authentication(self, api_client):
        response = api_client.post(self.url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_logout_authenticated_user(self, api_client, user):
        # We need the raw token to set in the headers as the test explicitly validates it
        refresh = RefreshToken.for_user(user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
        
        response = api_client.post(self.url)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
