from django.test import SimpleTestCase
from django.urls import resolve, reverse

from accounts.views import (
    RegisterAPIView,
    LoginAPIView,
    VerifyEmailAPIView,
    ResendVerificationEmailAPIView,
    RefreshTokenAPIView,
    LogoutAPIView,
    PasswordResetRequestAPIView,
    PasswordResetConfirmAPIView,
    GoogleLoginAPIView,
    GoogleLoginTestAPIView,
)


class AccountURLTests(SimpleTestCase):

    def test_register_url(self):

        self.assertEqual(
            reverse("register"),
            "/api/v1/accounts/register/",
        )

        self.assertEqual(
            resolve("/api/v1/accounts/register/").func.view_class,
            RegisterAPIView,
        )

    def test_login_url(self):

        self.assertEqual(
            reverse("login"),
            "/api/v1/accounts/login/",
        )

        self.assertEqual(
            resolve("/api/v1/accounts/login/").func.view_class,
            LoginAPIView,
        )

    def test_verify_email_url(self):

        self.assertEqual(
            reverse("verify-email"),
            "/api/v1/accounts/verify-email/",
        )

        self.assertEqual(
            resolve("/api/v1/accounts/verify-email/").func.view_class,
            VerifyEmailAPIView,
        )

    def test_resend_verification_url(self):

        self.assertEqual(
            reverse("resend-verification"),
            "/api/v1/accounts/resend-verification/",
        )

        self.assertEqual(
            resolve(
                "/api/v1/accounts/resend-verification/"
            ).func.view_class,
            ResendVerificationEmailAPIView,
        )

    def test_refresh_url(self):

        self.assertEqual(
            reverse("refresh"),
            "/api/v1/accounts/refresh/",
        )

        self.assertEqual(
            resolve("/api/v1/accounts/refresh/").func.view_class,
            RefreshTokenAPIView,
        )

    def test_logout_url(self):

        self.assertEqual(
            reverse("logout"),
            "/api/v1/accounts/logout/",
        )

        self.assertEqual(
            resolve("/api/v1/accounts/logout/").func.view_class,
            LogoutAPIView,
        )

    def test_password_reset_url(self):

        self.assertEqual(
            reverse("password-reset"),
            "/api/v1/accounts/password-reset/",
        )

        self.assertEqual(
            resolve(
                "/api/v1/accounts/password-reset/"
            ).func.view_class,
            PasswordResetRequestAPIView,
        )

    def test_password_reset_confirm_url(self):

        self.assertEqual(
            reverse(
                "password-reset-confirm"
            ),
            "/api/v1/accounts/password-reset-confirm/",
        )

        self.assertEqual(
            resolve(
                "/api/v1/accounts/password-reset-confirm/"
            ).func.view_class,
            PasswordResetConfirmAPIView,
        )

    def test_google_login_url(self):

        self.assertEqual(
            reverse("google-login"),
            "/api/v1/accounts/google-login/",
        )

        self.assertEqual(
            resolve(
                "/api/v1/accounts/google-login/"
            ).func.view_class,
            GoogleLoginAPIView,
        )

    def test_google_test_url(self):

        self.assertEqual(
            reverse("google-test"),
            "/api/v1/accounts/google-test/",
        )

        self.assertEqual(
            resolve(
                "/api/v1/accounts/google-test/"
            ).func.view_class,
            GoogleLoginTestAPIView,
        )