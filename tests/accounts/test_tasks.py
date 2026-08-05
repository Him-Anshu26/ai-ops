from unittest.mock import patch

from django.test import TestCase

from accounts.tasks import (
    cleanup_expired_email_verification_tokens,
    cleanup_expired_password_reset_tokens,
    cleanup_inactive_sessions,
    cleanup_accounts,
)


class CleanupExpiredEmailVerificationTokensTaskTests(TestCase):

    @patch(
        "accounts.tasks.cleanup_expired_verification_tokens_service"
    )
    def test_cleanup_email_tokens_task(
        self,
        mock_service,
    ):
        mock_service.return_value = 5

        result = cleanup_expired_email_verification_tokens()

        self.assertEqual(result, 5)
        mock_service.assert_called_once_with()


class CleanupExpiredPasswordResetTokensTaskTests(TestCase):

    @patch(
        "accounts.tasks.cleanup_expired_password_reset_tokens_service"
    )
    def test_cleanup_password_reset_tokens_task(
        self,
        mock_service,
    ):
        mock_service.return_value = 3

        result = cleanup_expired_password_reset_tokens()

        self.assertEqual(result, 3)
        mock_service.assert_called_once_with()


class CleanupInactiveSessionsTaskTests(TestCase):

    @patch(
        "accounts.tasks.cleanup_inactive_sessions_service"
    )
    def test_cleanup_inactive_sessions_task(
        self,
        mock_service,
    ):
        mock_service.return_value = 7

        result = cleanup_inactive_sessions()

        self.assertEqual(result, 7)
        mock_service.assert_called_once_with()


class CleanupAccountsTaskTests(TestCase):

    @patch(
        "accounts.tasks.cleanup_inactive_sessions"
    )
    @patch(
        "accounts.tasks.cleanup_expired_password_reset_tokens"
    )
    @patch(
        "accounts.tasks.cleanup_expired_email_verification_tokens"
    )
    def test_cleanup_accounts_runs_all_tasks(
        self,
        mock_email,
        mock_password,
        mock_sessions,
    ):
        mock_email.return_value = 2
        mock_password.return_value = 4
        mock_sessions.return_value = 6

        result = cleanup_accounts()

        mock_email.assert_called_once_with()
        mock_password.assert_called_once_with()
        mock_sessions.assert_called_once_with()

        self.assertEqual(
            result,
            {
                "email_verification_tokens": 2,
                "password_reset_tokens": 4,
                "inactive_sessions": 6,
            },
        )

    @patch(
        "accounts.tasks.cleanup_inactive_sessions"
    )
    @patch(
        "accounts.tasks.cleanup_expired_password_reset_tokens"
    )
    @patch(
        "accounts.tasks.cleanup_expired_email_verification_tokens"
    )
    def test_cleanup_accounts_returns_zero_counts(
        self,
        mock_email,
        mock_password,
        mock_sessions,
    ):
        mock_email.return_value = 0
        mock_password.return_value = 0
        mock_sessions.return_value = 0

        result = cleanup_accounts()

        self.assertEqual(
            result,
            {
                "email_verification_tokens": 0,
                "password_reset_tokens": 0,
                "inactive_sessions": 0,
            },
        )