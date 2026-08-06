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


class TestAccountURLs:
    def test_register_url(self):
        assert reverse("register") == "/api/v1/accounts/register/"
        assert resolve("/api/v1/accounts/register/").func.view_class == RegisterAPIView

    def test_login_url(self):
        assert reverse("login") == "/api/v1/accounts/login/"
        assert resolve("/api/v1/accounts/login/").func.view_class == LoginAPIView

    def test_verify_email_url(self):
        assert reverse("verify-email") == "/api/v1/accounts/verify-email/"
        assert resolve("/api/v1/accounts/verify-email/").func.view_class == VerifyEmailAPIView

    def test_resend_verification_url(self):
        assert reverse("resend-verification") == "/api/v1/accounts/resend-verification/"
        assert resolve("/api/v1/accounts/resend-verification/").func.view_class == ResendVerificationEmailAPIView

    def test_refresh_url(self):
        assert reverse("refresh") == "/api/v1/accounts/refresh/"
        assert resolve("/api/v1/accounts/refresh/").func.view_class == RefreshTokenAPIView

    def test_logout_url(self):
        assert reverse("logout") == "/api/v1/accounts/logout/"
        assert resolve("/api/v1/accounts/logout/").func.view_class == LogoutAPIView

    def test_password_reset_url(self):
        assert reverse("password-reset") == "/api/v1/accounts/password-reset/"
        assert resolve("/api/v1/accounts/password-reset/").func.view_class == PasswordResetRequestAPIView

    def test_password_reset_confirm_url(self):
        assert reverse("password-reset-confirm") == "/api/v1/accounts/password-reset-confirm/"
        assert resolve("/api/v1/accounts/password-reset-confirm/").func.view_class == PasswordResetConfirmAPIView

    def test_google_login_url(self):
        assert reverse("google-login") == "/api/v1/accounts/google-login/"
        assert resolve("/api/v1/accounts/google-login/").func.view_class == GoogleLoginAPIView

    def test_google_test_url(self):
        assert reverse("google-test") == "/api/v1/accounts/google-test/"
        assert resolve("/api/v1/accounts/google-test/").func.view_class == GoogleLoginTestAPIView