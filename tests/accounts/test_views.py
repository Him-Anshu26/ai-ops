from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import (
    APIClient,
    APIRequestFactory,
    force_authenticate,
    override_settings,
    settings,
)

from accounts.models import User

from accounts.views import (
    LogoutAPIView,
    PasswordResetRequestAPIView,
)

from rest_framework_simplejwt.tokens import RefreshToken


@override_settings(
    REST_FRAMEWORK={
        **settings.REST_FRAMEWORK,
        "DEFAULT_THROTTLE_CLASSES": [],
        "DEFAULT_THROTTLE_RATES": {},
    },
    RATELIMIT_ENABLE=False
)
class RegisterAPIViewTests(TestCase):

    def setUp(self):
        self.client = APIClient()

        self.url = reverse("register")

        self.payload = {
            "email": "user@example.com",
            "password": "StrongPassword@123",
            "first_name": "Himanshu",
        }

    @patch("accounts.views.send_verification_email")
    def test_register_successfully(
        self,
        mock_send_email,
    ):
        response = self.client.post(
            self.url,
            self.payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertEqual(
            response.data["message"],
            (
                "User registered successfully. "
                "Please verify your email."
            ),
        )

        self.assertEqual(
            User.objects.count(),
            1,
        )

        user = User.objects.get()

        self.assertEqual(
            user.email,
            "user@example.com",
        )

        mock_send_email.assert_called_once_with(user)

    @patch("accounts.views.logger.exception")
    @patch("accounts.views.send_verification_email")
    def test_register_when_email_service_fails(
        self,
        mock_send_email,
        mock_logger,
    ):
        mock_send_email.side_effect = Exception(
            "Mail server down"
        )

        response = self.client.post(
            self.url,
            self.payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertEqual(
            response.data["message"],
            (
                "Account created successfully. "
                "Verification email could not be sent. "
                "Please try again later."
            ),
        )

        self.assertEqual(
            User.objects.count(),
            1,
        )

    def test_register_duplicate_email(self):

        User.objects.create_user(
            email="user@example.com",
            password="Password@123",
        )

        response = self.client.post(
            self.url,
            self.payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn(
            "email",
            response.data,
        )

    def test_register_invalid_password(self):

        payload = self.payload.copy()

        payload["password"] = "123"

        response = self.client.post(
            self.url,
            payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn(
            "password",
            response.data,
        )

    def test_register_blank_first_name(self):

        payload = self.payload.copy()

        payload["first_name"] = "     "

        response = self.client.post(
            self.url,
            payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn(
            "first_name",
            response.data,
        )

    def test_register_missing_required_fields(self):

        response = self.client.post(
            self.url,
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn(
            "email",
            response.data,
        )

        self.assertIn(
            "password",
            response.data,
        )

    def test_register_email_is_normalized(self):

        payload = self.payload.copy()

        payload["email"] = " USER@Example.COM "

        with patch(
            "accounts.views.send_verification_email"
        ):
            response = self.client.post(
                self.url,
                payload,
                format="json",
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        user = User.objects.get()

        self.assertEqual(
            user.email,
            "user@example.com",
        )

    def test_register_first_name_is_trimmed(self):

        payload = self.payload.copy()

        payload["first_name"] = "   Himanshu   "

        with patch(
            "accounts.views.send_verification_email"
        ):
            self.client.post(
                self.url,
                payload,
                format="json",
            )

        user = User.objects.get()

        self.assertEqual(
            user.first_name,
            "Himanshu",
        )


class LoginAPIViewTests(TestCase):

    def setUp(self):
        self.client = APIClient()

        self.url = reverse("login")

        self.password = "Password@123"

        self.user = User.objects.create_user(
            email="user@example.com",
            password=self.password,
            is_verified=True,
            is_active=True,
        )

        self.payload = {
            "email": self.user.email,
            "password": self.password,
        }

    @patch("accounts.views.login_user")
    def test_login_successfully(
        self,
        mock_login,
    ):
        mock_login.return_value = {
            "access": "access-token",
            "refresh": "refresh-token",
        }

        response = self.client.post(
            self.url,
            self.payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["message"],
            "Login successful.",
        )

        self.assertEqual(
            response.data["tokens"]["access"],
            "access-token",
        )

        self.assertEqual(
            response.data["tokens"]["refresh"],
            "refresh-token",
        )

        mock_login.assert_called_once_with(
            email=self.user.email,
            password=self.password,
        )

    @patch("accounts.views.login_user")
    def test_invalid_credentials(
        self,
        mock_login,
    ):
        mock_login.side_effect = ValueError(
            "Invalid credentials"
        )

        response = self.client.post(
            self.url,
            self.payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

        self.assertEqual(
            response.data["error"],
            "Invalid credentials",
        )

    @patch("accounts.views.login_user")
    def test_unverified_email(
        self,
        mock_login,
    ):
        mock_login.side_effect = ValueError(
            "Email is not verified"
        )

        response = self.client.post(
            self.url,
            self.payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

        self.assertEqual(
            response.data["error"],
            "Email is not verified",
        )

    @patch("accounts.views.login_user")
    def test_disabled_account(
        self,
        mock_login,
    ):
        mock_login.side_effect = ValueError(
            "Account is disabled"
        )

        response = self.client.post(
            self.url,
            self.payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

        self.assertEqual(
            response.data["error"],
            "Account is disabled",
        )

    def test_login_serializer_validation_error(self):

        response = self.client.post(
            self.url,
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn(
            "email",
            response.data,
        )

        self.assertIn(
            "password",
            response.data,
        )

    def test_login_email_is_normalized(self):

        payload = {
            "email": " USER@Example.COM ",
            "password": self.password,
        }

        with patch(
            "accounts.views.login_user"
        ) as mock_login:

            mock_login.return_value = {
                "access": "access",
                "refresh": "refresh",
            }

            response = self.client.post(
                self.url,
                payload,
                format="json",
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        mock_login.assert_called_once_with(
            email="user@example.com",
            password=self.password,
        )


class VerifyEmailAPIViewTests(TestCase):

    def setUp(self):
        self.client = APIClient()

        self.url = reverse("verify-email")

    @patch("accounts.views.verify_email")
    def test_verify_email_successfully(
        self,
        mock_verify_email,
    ):
        response = self.client.get(
            self.url,
            {"token": "valid-token"},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["message"],
            "Email verified successfully.",
        )

        mock_verify_email.assert_called_once_with(
            "valid-token"
        )

    def test_verify_email_without_token(self):

        response = self.client.get(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertEqual(
            response.data["error"],
            "Token is required.",
        )

    @patch("accounts.views.verify_email")
    def test_invalid_token(
        self,
        mock_verify_email,
    ):
        mock_verify_email.side_effect = ValueError(
            "Invalid token"
        )

        response = self.client.get(
            self.url,
            {"token": "wrong-token"},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertEqual(
            response.data["error"],
            "Invalid token",
        )

    @patch("accounts.views.verify_email")
    def test_expired_token(
        self,
        mock_verify_email,
    ):
        mock_verify_email.side_effect = ValueError(
            "Token expired"
        )

        response = self.client.get(
            self.url,
            {"token": "expired-token"},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertEqual(
            response.data["error"],
            "Token expired",
        )

    @patch("accounts.views.verify_email")
    def test_service_exception_is_propagated(
        self,
        mock_verify_email,
    ):
        mock_verify_email.side_effect = ValueError(
            "Some verification error"
        )

        response = self.client.get(
            self.url,
            {"token": "abc"},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertEqual(
            response.data["error"],
            "Some verification error",
        )


class ResendVerificationEmailAPIViewTests(TestCase):

    def setUp(self):
        self.client = APIClient()

        self.url = reverse(
            "resend-verification"
        )

        self.payload = {
            "email": "user@example.com",
        }

    @patch("accounts.views.resend_verification_email")
    def test_resend_verification_email_successfully(
        self,
        mock_resend,
    ):
        response = self.client.post(
            self.url,
            self.payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["message"],
            (
                "If the account exists and is "
                "unverified, a verification "
                "email has been sent."
            ),
        )

        mock_resend.assert_called_once_with(
            email="user@example.com",
        )

    def test_missing_email(self):

        response = self.client.post(
            self.url,
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn(
            "email",
            response.data,
        )

    def test_invalid_email_format(self):

        payload = {
            "email": "invalid-email",
        }

        response = self.client.post(
            self.url,
            payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn(
            "email",
            response.data,
        )

    @patch("accounts.views.resend_verification_email")
    def test_email_is_normalized_before_service_call(
        self,
        mock_resend,
    ):
        payload = {
            "email": " USER@Example.COM ",
        }

        response = self.client.post(
            self.url,
            payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        mock_resend.assert_called_once_with(
            email="user@example.com",
        )

    @patch("accounts.views.resend_verification_email")
    def test_service_is_called_once(
        self,
        mock_resend,
    ):
        self.client.post(
            self.url,
            self.payload,
            format="json",
        )

        self.assertEqual(
            mock_resend.call_count,
            1,
        )


class RefreshTokenAPIViewTests(TestCase):

    def setUp(self):
        self.client = APIClient()

        self.url = reverse("refresh")

        self.payload = {
            "refresh": "refresh-token",
        }

    @patch("accounts.views.refresh_access_token")
    def test_refresh_access_token_successfully(
        self,
        mock_refresh,
    ):
        mock_refresh.return_value = "new-access-token"

        response = self.client.post(
            self.url,
            self.payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["access"],
            "new-access-token",
        )

        mock_refresh.assert_called_once_with(
            "refresh-token"
        )

    @patch("accounts.views.refresh_access_token")
    def test_invalid_refresh_token(
        self,
        mock_refresh,
    ):
        mock_refresh.side_effect = ValueError(
            "Invalid token"
        )

        response = self.client.post(
            self.url,
            self.payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

        self.assertEqual(
            response.data["error"],
            "Invalid token",
        )

    @patch("accounts.views.refresh_access_token")
    def test_expired_session(
        self,
        mock_refresh,
    ):
        mock_refresh.side_effect = ValueError(
            "Session expired"
        )

        response = self.client.post(
            self.url,
            self.payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

        self.assertEqual(
            response.data["error"],
            "Session expired",
        )

    def test_missing_refresh_token(self):

        response = self.client.post(
            self.url,
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn(
            "refresh",
            response.data,
        )

    def test_blank_refresh_token(self):

        response = self.client.post(
            self.url,
            {
                "refresh": "   ",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn(
            "refresh",
            response.data,
        )

    @patch("accounts.views.refresh_access_token")
    def test_refresh_token_is_trimmed_before_service_call(
        self,
        mock_refresh,
    ):
        mock_refresh.return_value = "access-token"

        response = self.client.post(
            self.url,
            {
                "refresh": "   refresh-token   ",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        mock_refresh.assert_called_once_with(
            "refresh-token"
        )

    @patch("accounts.views.refresh_access_token")
    def test_service_called_once(
        self,
        mock_refresh,
    ):
        mock_refresh.return_value = "access-token"

        self.client.post(
            self.url,
            self.payload,
            format="json",
        )

        self.assertEqual(
            mock_refresh.call_count,
            1,
        )


class LogoutAPIViewTests(TestCase):

    def setUp(self):
        self.client = APIClient()

        self.url = reverse("logout")

        self.user = User.objects.create_user(
            email="user@example.com",
            password="Password@123",
            is_verified=True,
            is_active=True,
        )

        refresh = RefreshToken.for_user(self.user)

        self.access_token = str(refresh.access_token)

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.access_token}"
        )

    @patch("accounts.views.logout_user")
    def test_logout_successfully(
        self,
        mock_logout,
    ):
        with patch(
            "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate",
            return_value=(
                self.user,
                {
                    "session_id": "session-123",
                },
            ),
        ):
            response = self.client.post(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["message"],
            "Logged out successfully.",
        )

        mock_logout.assert_called_once_with(
            "session-123",
        )

    @patch("accounts.views.logout_user")
    def test_missing_session_id_returns_error(
        self,
        mock_logout,
    ):
        with patch(
            "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate",
            return_value=(
                self.user,
                {},
            ),
        ):
            response = self.client.post(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

        self.assertEqual(
            response.data["error"],
            "Invalid session.",
        )

        mock_logout.assert_not_called()

    @patch("accounts.views.logout_user")
    def test_none_session_id_returns_error(
        self,
        mock_logout,
    ):
        with patch(
            "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate",
            return_value=(
                self.user,
                {
                    "session_id": None,
                },
            ),
        ):
            response = self.client.post(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

        self.assertEqual(
            response.data["error"],
            "Invalid session.",
        )

        mock_logout.assert_not_called()

    @patch("accounts.views.logout_user")
    def test_logout_service_called_once(
        self,
        mock_logout,
    ):
        with patch(
            "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate",
            return_value=(
                self.user,
                {
                    "session_id": "session-abc",
                },
            ),
        ):
            self.client.post(self.url)

        self.assertEqual(
            mock_logout.call_count,
            1,
        )



class PasswordResetRequestAPIViewTests(TestCase):

    def setUp(self):
        self.factory = APIRequestFactory()

        self.view = (
            PasswordResetRequestAPIView.as_view()
        )

    @patch(
        "accounts.views.request_password_reset"
    )
    def test_password_reset_request_success(
        self,
        mock_request_reset,
    ):
        request = self.factory.post(
            "/password-reset/",
            {
                "email": "USER@example.com",
            },
            format="json",
        )

        response = self.view(request)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["message"],
            (
                "If the account exists, "
                "a password reset email has been sent."
            ),
        )

        mock_request_reset.assert_called_once_with(
            "user@example.com",
        )

    @patch(
        "accounts.views.request_password_reset"
    )
    def test_invalid_email_returns_400(
        self,
        mock_request_reset,
    ):
        request = self.factory.post(
            "/password-reset/",
            {
                "email": "invalid-email",
            },
            format="json",
        )

        response = self.view(request)

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn(
            "email",
            response.data,
        )

        mock_request_reset.assert_not_called()

    @patch(
        "accounts.views.request_password_reset"
    )
    def test_missing_email_returns_400(
        self,
        mock_request_reset,
    ):
        request = self.factory.post(
            "/password-reset/",
            {},
            format="json",
        )

        response = self.view(request)

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn(
            "email",
            response.data,
        )

        mock_request_reset.assert_not_called()

    @patch(
        "accounts.views.request_password_reset"
    )
    def test_email_is_normalized_before_service(
        self,
        mock_request_reset,
    ):
        request = self.factory.post(
            "/password-reset/",
            {
                "email": "  USER@Example.COM  ",
            },
            format="json",
        )

        response = self.view(request)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        mock_request_reset.assert_called_once_with(
            "user@example.com",
        )


class PasswordResetConfirmAPIViewTests(TestCase):

    def setUp(self):
        self.client = APIClient()

        self.url = reverse(
            "password-reset-confirm"
        )

    @patch("accounts.views.reset_password")
    def test_password_reset_confirm_success(
        self,
        mock_reset_password,
    ):
        response = self.client.post(
            self.url,
            {
                "token": "valid-token",
                "new_password": "Password@123",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["message"],
            "Password reset successful.",
        )

        mock_reset_password.assert_called_once_with(
            token="valid-token",
            new_password="Password@123",
        )

    @patch("accounts.views.reset_password")
    def test_invalid_token_returns_400(
        self,
        mock_reset_password,
    ):
        mock_reset_password.side_effect = ValueError(
            "Invalid token"
        )

        response = self.client.post(
            self.url,
            {
                "token": "bad-token",
                "new_password": "Password@123",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertEqual(
            response.data["error"],
            "Invalid token",
        )

    def test_missing_token(self):
        response = self.client.post(
            self.url,
            {
                "new_password": "Password@123",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_missing_password(self):
        response = self.client.post(
            self.url,
            {
                "token": "abc",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_blank_token(self):
        response = self.client.post(
            self.url,
            {
                "token": "",
                "new_password": "Password@123",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_weak_password(self):
        response = self.client.post(
            self.url,
            {
                "token": "abc",
                "new_password": "123",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )


class GoogleLoginAPIViewTests(TestCase):

    def setUp(self):
        self.client = APIClient()

        self.url = reverse(
            "google-login"
        )

    @patch("accounts.views.google_login")
    def test_google_login_success(
        self,
        mock_google_login,
    ):
        mock_google_login.return_value = {
            "access": "access-token",
            "refresh": "refresh-token",
        }

        response = self.client.post(
            self.url,
            {
                "id_token": "google-token",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["tokens"]["access"],
            "access-token",
        )

        mock_google_login.assert_called_once_with(
            token="google-token",
        )

    @patch("accounts.views.google_login")
    def test_invalid_google_token(
        self,
        mock_google_login,
    ):
        mock_google_login.side_effect = ValueError(
            "Invalid Google token"
        )

        response = self.client.post(
            self.url,
            {
                "id_token": "bad-token",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

        self.assertEqual(
            response.data["error"],
            "Invalid Google token",
        )

    def test_missing_id_token(self):
        response = self.client.post(
            self.url,
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_blank_id_token(self):
        response = self.client.post(
            self.url,
            {
                "id_token": "",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    @patch("accounts.views.google_login")
    def test_disabled_account(
        self,
        mock_google_login,
    ):
        mock_google_login.side_effect = ValueError(
            "Account is disabled"
        )

        response = self.client.post(
            self.url,
            {
                "id_token": "token",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    @patch("accounts.views.google_login")
    def test_google_login_service_called(
        self,
        mock_google_login,
    ):
        mock_google_login.return_value = {
            "access": "a",
            "refresh": "r",
        }

        self.client.post(
            self.url,
            {
                "id_token": "token",
            },
            format="json",
        )

        mock_google_login.assert_called_once()



class GoogleLoginTestAPIViewTests(TestCase):

    def setUp(self):
        self.client = APIClient()

        self.url = reverse(
            "google-test"
        )

    def test_google_test_page_renders(self):
        response = self.client.get(
            self.url
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertTemplateUsed(
            response,
            "google_login_test/google_test.html",
        )

    @patch(
        "accounts.views.settings.GOOGLE_CLIENT_ID",
        "client-id",
    )
    def test_google_client_id_in_context(self):
        response = self.client.get(
            self.url
        )

        self.assertEqual(
            response.context[
                "GOOGLE_CLIENT_ID"
            ],
            "client-id",
        )