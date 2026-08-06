import hashlib
from unittest.mock import Mock, patch

import pytest

from accounts.utils import (
    build_reset_link,
    build_verification_link,
    generate_token,
    hash_token,
    send_email,
)


class TestGenerateToken:
    def test_generate_token_returns_string(self):
        token = generate_token()

        assert isinstance(token, str)
        assert len(token) > 40

    def test_generate_token_is_unique(self):
        token1 = generate_token()
        token2 = generate_token()

        assert token1 != token2


class TestHashToken:
    def test_hash_token_matches_sha256(self):
        token = "my-secret-token"
        expected = hashlib.sha256(token.encode()).hexdigest()

        assert hash_token(token) == expected

    def test_hash_token_is_deterministic(self):
        token = "same-token"
        assert hash_token(token) == hash_token(token)

    def test_different_tokens_produce_different_hashes(self):
        assert hash_token("token-1") != hash_token("token-2")


class TestSendEmail:
    @pytest.fixture(autouse=True)
    def setup_settings(self, settings):
        settings.RESEND_API_KEY = "test-api-key"
        settings.DEFAULT_FROM_EMAIL = "noreply@example.com"

    @patch("accounts.utils.resend.Emails.send")
    def test_send_email_success(self, mock_send, settings):
        mock_send.return_value = {"id": "email-id"}

        send_email(
            subject="Welcome",
            message="Hello User",
            recipient_list=["user@example.com"],
        )

        assert settings.RESEND_API_KEY == "test-api-key"
        mock_send.assert_called_once_with(
            {
                "from": "noreply@example.com",
                "to": ["user@example.com"],
                "subject": "Welcome",
                "text": "Hello User",
            }
        )

    @patch("accounts.utils.logger")
    @patch("accounts.utils.resend.Emails.send")
    def test_send_email_logs_success(self, mock_send, mock_logger):
        mock_send.return_value = {"id": "email-id"}

        send_email(
            subject="Subject",
            message="Message",
            recipient_list=["user@example.com"],
        )

        mock_logger.info.assert_called_once()

    @patch("accounts.utils.logger")
    @patch("accounts.utils.resend.Emails.send")
    def test_send_email_failure_is_reraised(self, mock_send, mock_logger):
        mock_send.side_effect = Exception("Resend failure")

        with pytest.raises(Exception, match="Resend failure"):
            send_email(
                subject="Subject",
                message="Message",
                recipient_list=["user@example.com"],
            )

        mock_logger.exception.assert_called_once()


class TestBuildVerificationLink:
    @pytest.fixture(autouse=True)
    def setup_settings(self, settings):
        settings.FRONTEND_URL = "https://frontend.example.com"

    def test_build_verification_link(self):
        token = "abc123"
        link = build_verification_link(token)
        assert link == "https://frontend.example.com/verify-email/?token=abc123"


class TestBuildResetLink:
    @pytest.fixture(autouse=True)
    def setup_settings(self, settings):
        settings.FRONTEND_URL = "https://frontend.example.com"

    def test_build_reset_link(self):
        token = "reset123"
        link = build_reset_link(token)
        assert link == "https://frontend.example.com/reset-password/?token=reset123"