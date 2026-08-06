"""
Integration tests for the complete email verification workflow.
"""

import pytest
from unittest.mock import patch
from django.urls import reverse
from rest_framework import status

from accounts.models import User, EmailVerificationToken
from accounts.utils import hash_token
from tests.factories import UserFactory, EmailVerificationTokenFactory


@pytest.mark.django_db
class TestEmailVerificationWorkflow:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.register_url = reverse("register")
        self.verify_url = reverse("verify-email")
        self.resend_url = reverse("resend-verification")

    @patch("accounts.services.send_email")
    def test_registration_to_verification_workflow(self, mock_send_email, api_client):
        """
        Verify the complete golden path:
        Register -> Email Token Gen -> Verification -> Token Deletion.
        """
        payload = {
            "email": "newuser@example.com",
            "password": "Password@123",
            "first_name": "NewUser"
        }

        # 1. Register User
        register_response = api_client.post(self.register_url, payload, format="json")
        assert register_response.status_code == status.HTTP_201_CREATED

        # 2. Verify User State in DB
        user = User.objects.get(email="newuser@example.com")
        assert user.is_verified is False
        assert EmailVerificationToken.objects.filter(user=user).count() == 1

        # 3. Extract Raw Token from Mock
        assert mock_send_email.called
        email_body = mock_send_email.call_args[1]["message"]
        # The token is at the end of the URL, e.g. '.../verify-email/?token=RAW_TOKEN'
        # We can extract it by splitting the string.
        raw_token = email_body.split("token=")[1].split("\n")[0].strip()

        # 4. Attempt Verification
        verify_response = api_client.get(f"{self.verify_url}?token={raw_token}")
        assert verify_response.status_code == status.HTTP_200_OK
        assert verify_response.data["message"] == "Email verified successfully."

        # 5. Verify Final State
        user.refresh_from_db()
        assert user.is_verified is True
        # Token must be deleted after successful use
        assert EmailVerificationToken.objects.filter(user=user).count() == 0

    def test_verification_already_verified_user(self, api_client):
        """
        Verify that verifying an already verified user is idempotent.
        """
        user = UserFactory(is_verified=True)
        raw_token = "sometoken123"
        
        # Inject token manually
        EmailVerificationTokenFactory(
            user=user,
            token_hash=hash_token(raw_token)
        )

        response = api_client.get(f"{self.verify_url}?token={raw_token}")
        
        assert response.status_code == status.HTTP_200_OK
        assert EmailVerificationToken.objects.filter(user=user).count() == 0

    def test_verification_invalid_token(self, api_client):
        """
        Verify that garbage tokens are rejected.
        """
        response = api_client.get(f"{self.verify_url}?token=invalid-token")
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error"] == "Invalid token"

    def test_verification_missing_token(self, api_client):
        """
        Verify that missing tokens are rejected cleanly.
        """
        response = api_client.get(self.verify_url)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error"] == "Token is required."

    @patch("accounts.services.send_email")
    def test_resend_verification_workflow(self, mock_send_email, api_client):
        """
        Verify the workflow to resend verification emails to unverified users.
        """
        user = UserFactory(is_verified=False)
        # Give them an old token to ensure it gets cleared out
        EmailVerificationTokenFactory(user=user)

        payload = {"email": user.email}
        response = api_client.post(self.resend_url, payload, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert "verification email has been sent" in response.data["message"]

        # Ensure the old token was deleted and EXACTLY ONE new token was generated
        assert EmailVerificationToken.objects.filter(user=user).count() == 1
        assert mock_send_email.called

    @patch("accounts.services.send_email")
    def test_resend_verification_already_verified(self, mock_send_email, api_client):
        """
        Verify that resending to a verified user does not generate a token,
        but still returns the generic success message to prevent enumeration.
        """
        user = UserFactory(is_verified=True)

        payload = {"email": user.email}
        response = api_client.post(self.resend_url, payload, format="json")

        assert response.status_code == status.HTTP_200_OK
        
        # No new tokens should be generated
        assert EmailVerificationToken.objects.filter(user=user).count() == 0
        # No email should be dispatched
        assert not mock_send_email.called

    def test_resend_verification_nonexistent_email(self, api_client):
        """
        Verify that resending to a non-existent email returns success to prevent enumeration.
        """
        payload = {"email": "nobody@example.com"}
        response = api_client.post(self.resend_url, payload, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert EmailVerificationToken.objects.count() == 0
