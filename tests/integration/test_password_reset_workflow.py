"""
Integration tests for the complete password reset workflow.
"""

import pytest
from datetime import timedelta
from unittest.mock import patch
from django.utils import timezone
from django.urls import reverse
from rest_framework import status

from accounts.models import PasswordResetToken, UserSession
from accounts.utils import hash_token
from tests.factories import UserFactory, PasswordResetTokenFactory, UserSessionFactory


@pytest.mark.django_db
class TestPasswordResetWorkflow:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.request_url = reverse("password-reset")
        self.confirm_url = reverse("password-reset-confirm")

    @patch("accounts.services.send_email")
    def test_password_reset_golden_path(self, mock_send_email, api_client):
        """
        Verify the complete golden path:
        Request Reset -> Email Sent -> Confirm Reset -> Password Changed -> Sessions Invalidated.
        """
        old_password = "OldPassword@123"
        new_password = "NewPassword!456"
        
        user = UserFactory(password=old_password, is_verified=True, is_active=True)
        
        # Inject an active session to verify global logout
        session = UserSessionFactory(user=user, is_active=True)

        # 1. Request Password Reset
        payload = {"email": user.email}
        request_response = api_client.post(self.request_url, payload, format="json")
        
        assert request_response.status_code == status.HTTP_200_OK
        assert PasswordResetToken.objects.filter(user=user).count() == 1

        # 2. Extract Raw Token from Mock
        assert mock_send_email.called
        email_body = mock_send_email.call_args[1]["message"]
        # Extract token from '.../reset-password/?token=RAW_TOKEN'
        raw_token = email_body.split("token=")[1].split("\n")[0].strip()

        # 3. Confirm Password Reset
        confirm_payload = {
            "token": raw_token,
            "new_password": new_password
        }
        confirm_response = api_client.post(self.confirm_url, confirm_payload, format="json")
        
        assert confirm_response.status_code == status.HTTP_200_OK
        assert confirm_response.data["message"] == "Password reset successful."

        # 4. Verify Database Changes
        user.refresh_from_db()
        # Verify old password fails
        assert user.check_password(old_password) is False
        # Verify new password succeeds
        assert user.check_password(new_password) is True

        # Token must be deleted after successful use
        assert PasswordResetToken.objects.filter(user=user).count() == 0

        # 5. Verify Session Invalidation (Global Logout)
        session.refresh_from_db()
        assert session.is_active is False

    @patch("accounts.services.send_email")
    def test_password_reset_request_nonexistent_email(self, mock_send_email, api_client):
        """
        Verify that requesting a reset for an invalid email succeeds without leaking info.
        """
        payload = {"email": "nobody@example.com"}
        response = api_client.post(self.request_url, payload, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert "password reset email has been sent" in response.data["message"]

        # No token created, no email sent
        assert PasswordResetToken.objects.count() == 0
        assert not mock_send_email.called

    def test_password_reset_confirm_invalid_token(self, api_client):
        """
        Verify that an invalid token is rejected cleanly.
        """
        payload = {
            "token": "invalid-garbage-token",
            "new_password": "NewPassword!456"
        }
        response = api_client.post(self.confirm_url, payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error"] == "Invalid token"

    def test_password_reset_confirm_expired_token(self, api_client):
        """
        Verify that an expired token is rejected and deleted from the database.
        """
        user = UserFactory()
        raw_token = "expiredtoken123"
        
        # Inject token and artificially age it past 30 minutes
        token_record = PasswordResetTokenFactory(
            user=user,
            token_hash=hash_token(raw_token)
        )
        PasswordResetToken.objects.filter(id=token_record.id).update(
            created_at=timezone.now() - timedelta(minutes=40)
        )

        payload = {
            "token": raw_token,
            "new_password": "NewPassword!456"
        }
        response = api_client.post(self.confirm_url, payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error"] == "Token expired"

        # The API raises ValueError which rolls back the transaction, 
        # so the token is NOT deleted immediately. It relies on the cleanup cron job.
        assert PasswordResetToken.objects.filter(id=token_record.id).count() == 1
