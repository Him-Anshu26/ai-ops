from unittest.mock import patch

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIRequestFactory, override_settings, settings
from pytest_django.asserts import assertTemplateUsed

from accounts.models import User
from accounts.views import PasswordResetRequestAPIView
from rest_framework_simplejwt.tokens import RefreshToken
from tests.factories import UserFactory


@pytest.mark.django_db
class TestRegisterAPIView:
    @pytest.fixture(autouse=True)
    def setup_view(self, api_client, settings):
        settings.REST_FRAMEWORK = {
            **getattr(settings, "REST_FRAMEWORK", {}),
            "DEFAULT_THROTTLE_CLASSES": [],
            "DEFAULT_THROTTLE_RATES": {},
        }
        settings.RATELIMIT_ENABLE = False
        
        self.client = api_client
        self.url = reverse("register")
        self.payload = {
            "email": "user@example.com",
            "password": "StrongPassword@123",
            "first_name": "Himanshu",
        }

    @patch("accounts.views.send_verification_email")
    def test_register_successfully(self, mock_send_email):
        response = self.client.post(self.url, self.payload, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["message"] == "User registered successfully. Please verify your email."
        assert User.objects.count() == 1
        
        user = User.objects.get()
        assert user.email == "user@example.com"
        mock_send_email.assert_called_once_with(user)

    @patch("accounts.views.logger.exception")
    @patch("accounts.views.send_verification_email")
    def test_register_when_email_service_fails(self, mock_send_email, mock_logger):
        mock_send_email.side_effect = Exception("Mail server down")

        response = self.client.post(self.url, self.payload, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["message"] == "Account created successfully. Verification email could not be sent. Please try again later."
        assert User.objects.count() == 1

    def test_register_duplicate_email(self):
        UserFactory(email="user@example.com", password="Password@123")

        response = self.client.post(self.url, self.payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "email" in response.data

    def test_register_invalid_password(self):
        payload = self.payload.copy()
        payload["password"] = "123"

        response = self.client.post(self.url, payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "password" in response.data

    def test_register_blank_first_name(self):
        payload = self.payload.copy()
        payload["first_name"] = "     "

        response = self.client.post(self.url, payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "first_name" in response.data

    def test_register_missing_required_fields(self):
        response = self.client.post(self.url, {}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "email" in response.data
        assert "password" in response.data

    def test_register_email_is_normalized(self):
        payload = self.payload.copy()
        payload["email"] = " USER@Example.COM "

        with patch("accounts.views.send_verification_email"):
            response = self.client.post(self.url, payload, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        user = User.objects.get()
        assert user.email == "user@example.com"

    def test_register_first_name_is_trimmed(self):
        payload = self.payload.copy()
        payload["first_name"] = "   Himanshu   "

        with patch("accounts.views.send_verification_email"):
            self.client.post(self.url, payload, format="json")

        user = User.objects.get()
        assert user.first_name == "Himanshu"


@pytest.mark.django_db
class TestLoginAPIView:
    @pytest.fixture(autouse=True)
    def setup_view(self, api_client):
        self.client = api_client
        self.url = reverse("login")
        self.password = "Password@123"

        self.user = UserFactory(
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
    def test_login_successfully(self, mock_login):
        mock_login.return_value = {
            "access": "access-token",
            "refresh": "refresh-token",
        }

        response = self.client.post(self.url, self.payload, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["message"] == "Login successful."
        assert response.data["tokens"]["access"] == "access-token"
        assert response.data["tokens"]["refresh"] == "refresh-token"
        mock_login.assert_called_once_with(email=self.user.email, password=self.password)

    @patch("accounts.views.login_user")
    def test_invalid_credentials(self, mock_login):
        mock_login.side_effect = ValueError("Invalid credentials")

        response = self.client.post(self.url, self.payload, format="json")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.data["error"] == "Invalid credentials"

    @patch("accounts.views.login_user")
    def test_unverified_email(self, mock_login):
        mock_login.side_effect = ValueError("Email is not verified")

        response = self.client.post(self.url, self.payload, format="json")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.data["error"] == "Email is not verified"

    @patch("accounts.views.login_user")
    def test_disabled_account(self, mock_login):
        mock_login.side_effect = ValueError("Account is disabled")

        response = self.client.post(self.url, self.payload, format="json")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.data["error"] == "Account is disabled"

    def test_login_serializer_validation_error(self):
        response = self.client.post(self.url, {}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "email" in response.data
        assert "password" in response.data

    def test_login_email_is_normalized(self):
        payload = {
            "email": " USER@Example.COM ",
            "password": self.password,
        }

        with patch("accounts.views.login_user") as mock_login:
            mock_login.return_value = {
                "access": "access",
                "refresh": "refresh",
            }
            response = self.client.post(self.url, payload, format="json")

        assert response.status_code == status.HTTP_200_OK
        mock_login.assert_called_once_with(email="user@example.com", password=self.password)


@pytest.mark.django_db
class TestVerifyEmailAPIView:
    @pytest.fixture(autouse=True)
    def setup_view(self, api_client):
        self.client = api_client
        self.url = reverse("verify-email")

    @patch("accounts.views.verify_email")
    def test_verify_email_successfully(self, mock_verify_email):
        response = self.client.get(self.url, {"token": "valid-token"})

        assert response.status_code == status.HTTP_200_OK
        assert response.data["message"] == "Email verified successfully."
        mock_verify_email.assert_called_once_with("valid-token")

    def test_verify_email_without_token(self):
        response = self.client.get(self.url)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error"] == "Token is required."

    @patch("accounts.views.verify_email")
    def test_invalid_token(self, mock_verify_email):
        mock_verify_email.side_effect = ValueError("Invalid token")

        response = self.client.get(self.url, {"token": "wrong-token"})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error"] == "Invalid token"

    @patch("accounts.views.verify_email")
    def test_expired_token(self, mock_verify_email):
        mock_verify_email.side_effect = ValueError("Token expired")

        response = self.client.get(self.url, {"token": "expired-token"})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error"] == "Token expired"

    @patch("accounts.views.verify_email")
    def test_service_exception_is_propagated(self, mock_verify_email):
        mock_verify_email.side_effect = ValueError("Some verification error")

        response = self.client.get(self.url, {"token": "abc"})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error"] == "Some verification error"


@pytest.mark.django_db
class TestResendVerificationEmailAPIView:
    @pytest.fixture(autouse=True)
    def setup_view(self, api_client):
        self.client = api_client
        self.url = reverse("resend-verification")
        self.payload = {"email": "user@example.com"}

    @patch("accounts.views.resend_verification_email")
    def test_resend_verification_email_successfully(self, mock_resend):
        response = self.client.post(self.url, self.payload, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["message"] == "If the account exists and is unverified, a verification email has been sent."
        mock_resend.assert_called_once_with(email="user@example.com")

    def test_missing_email(self):
        response = self.client.post(self.url, {}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "email" in response.data

    def test_invalid_email_format(self):
        payload = {"email": "invalid-email"}

        response = self.client.post(self.url, payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "email" in response.data

    @patch("accounts.views.resend_verification_email")
    def test_email_is_normalized_before_service_call(self, mock_resend):
        payload = {"email": " USER@Example.COM "}

        response = self.client.post(self.url, payload, format="json")

        assert response.status_code == status.HTTP_200_OK
        mock_resend.assert_called_once_with(email="user@example.com")

    @patch("accounts.views.resend_verification_email")
    def test_service_is_called_once(self, mock_resend):
        self.client.post(self.url, self.payload, format="json")
        assert mock_resend.call_count == 1


@pytest.mark.django_db
class TestRefreshTokenAPIView:
    @pytest.fixture(autouse=True)
    def setup_view(self, api_client):
        self.client = api_client
        self.url = reverse("refresh")
        self.payload = {"refresh": "refresh-token"}

    @patch("accounts.views.refresh_access_token")
    def test_refresh_access_token_successfully(self, mock_refresh):
        mock_refresh.return_value = "new-access-token"

        response = self.client.post(self.url, self.payload, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["access"] == "new-access-token"
        mock_refresh.assert_called_once_with("refresh-token")

    @patch("accounts.views.refresh_access_token")
    def test_invalid_refresh_token(self, mock_refresh):
        mock_refresh.side_effect = ValueError("Invalid token")

        response = self.client.post(self.url, self.payload, format="json")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.data["error"] == "Invalid token"

    @patch("accounts.views.refresh_access_token")
    def test_expired_session(self, mock_refresh):
        mock_refresh.side_effect = ValueError("Session expired")

        response = self.client.post(self.url, self.payload, format="json")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.data["error"] == "Session expired"

    def test_missing_refresh_token(self):
        response = self.client.post(self.url, {}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "refresh" in response.data

    def test_blank_refresh_token(self):
        response = self.client.post(self.url, {"refresh": "   "}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "refresh" in response.data

    @patch("accounts.views.refresh_access_token")
    def test_refresh_token_is_trimmed_before_service_call(self, mock_refresh):
        mock_refresh.return_value = "access-token"

        response = self.client.post(self.url, {"refresh": "   refresh-token   "}, format="json")

        assert response.status_code == status.HTTP_200_OK
        mock_refresh.assert_called_once_with("refresh-token")

    @patch("accounts.views.refresh_access_token")
    def test_service_called_once(self, mock_refresh):
        mock_refresh.return_value = "access-token"
        self.client.post(self.url, self.payload, format="json")
        assert mock_refresh.call_count == 1


@pytest.mark.django_db
class TestLogoutAPIView:
    @pytest.fixture(autouse=True)
    def setup_view(self, api_client):
        self.client = api_client
        self.url = reverse("logout")

        self.user = UserFactory(
            email="user@example.com",
            password="Password@123",
            is_verified=True,
            is_active=True,
        )

        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access_token}")

    @patch("accounts.views.logout_user")
    def test_logout_successfully(self, mock_logout):
        with patch(
            "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate",
            return_value=(self.user, {"session_id": "session-123"}),
        ):
            response = self.client.post(self.url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["message"] == "Logged out successfully."
        mock_logout.assert_called_once_with("session-123")

    @patch("accounts.views.logout_user")
    def test_missing_session_id_returns_error(self, mock_logout):
        with patch(
            "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate",
            return_value=(self.user, {}),
        ):
            response = self.client.post(self.url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.data["error"] == "Invalid session."
        mock_logout.assert_not_called()

    @patch("accounts.views.logout_user")
    def test_none_session_id_returns_error(self, mock_logout):
        with patch(
            "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate",
            return_value=(self.user, {"session_id": None}),
        ):
            response = self.client.post(self.url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.data["error"] == "Invalid session."
        mock_logout.assert_not_called()

    @patch("accounts.views.logout_user")
    def test_logout_service_called_once(self, mock_logout):
        with patch(
            "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate",
            return_value=(self.user, {"session_id": "session-abc"}),
        ):
            self.client.post(self.url)

        assert mock_logout.call_count == 1


@pytest.mark.django_db
class TestPasswordResetRequestAPIView:
    @pytest.fixture(autouse=True)
    def setup_view(self):
        self.factory = APIRequestFactory()
        self.view = PasswordResetRequestAPIView.as_view()

    @patch("accounts.views.request_password_reset")
    def test_password_reset_request_success(self, mock_request_reset):
        request = self.factory.post("/password-reset/", {"email": "USER@example.com"}, format="json")
        response = self.view(request)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["message"] == "If the account exists, a password reset email has been sent."
        mock_request_reset.assert_called_once_with("user@example.com")

    @patch("accounts.views.request_password_reset")
    def test_invalid_email_returns_400(self, mock_request_reset):
        request = self.factory.post("/password-reset/", {"email": "invalid-email"}, format="json")
        response = self.view(request)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "email" in response.data
        mock_request_reset.assert_not_called()

    @patch("accounts.views.request_password_reset")
    def test_missing_email_returns_400(self, mock_request_reset):
        request = self.factory.post("/password-reset/", {}, format="json")
        response = self.view(request)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "email" in response.data
        mock_request_reset.assert_not_called()

    @patch("accounts.views.request_password_reset")
    def test_email_is_normalized_before_service(self, mock_request_reset):
        request = self.factory.post("/password-reset/", {"email": "  USER@Example.COM  "}, format="json")
        response = self.view(request)

        assert response.status_code == status.HTTP_200_OK
        mock_request_reset.assert_called_once_with("user@example.com")


@pytest.mark.django_db
class TestPasswordResetConfirmAPIView:
    @pytest.fixture(autouse=True)
    def setup_view(self, api_client):
        self.client = api_client
        self.url = reverse("password-reset-confirm")

    @patch("accounts.views.reset_password")
    def test_password_reset_confirm_success(self, mock_reset_password):
        response = self.client.post(self.url, {"token": "valid-token", "new_password": "Password@123"}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["message"] == "Password reset successful."
        mock_reset_password.assert_called_once_with(token="valid-token", new_password="Password@123")

    @patch("accounts.views.reset_password")
    def test_invalid_token_returns_400(self, mock_reset_password):
        mock_reset_password.side_effect = ValueError("Invalid token")

        response = self.client.post(self.url, {"token": "bad-token", "new_password": "Password@123"}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error"] == "Invalid token"

    def test_missing_token(self):
        response = self.client.post(self.url, {"new_password": "Password@123"}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_missing_password(self):
        response = self.client.post(self.url, {"token": "abc"}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_blank_token(self):
        response = self.client.post(self.url, {"token": "", "new_password": "Password@123"}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_weak_password(self):
        response = self.client.post(self.url, {"token": "abc", "new_password": "123"}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestGoogleLoginAPIView:
    @pytest.fixture(autouse=True)
    def setup_view(self, api_client):
        self.client = api_client
        self.url = reverse("google-login")

    @patch("accounts.views.google_login")
    def test_google_login_success(self, mock_google_login):
        mock_google_login.return_value = {"access": "access-token", "refresh": "refresh-token"}

        response = self.client.post(self.url, {"id_token": "google-token"}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["tokens"]["access"] == "access-token"
        mock_google_login.assert_called_once_with(token="google-token")

    @patch("accounts.views.google_login")
    def test_invalid_google_token(self, mock_google_login):
        mock_google_login.side_effect = ValueError("Invalid Google token")

        response = self.client.post(self.url, {"id_token": "bad-token"}, format="json")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.data["error"] == "Invalid Google token"

    def test_missing_id_token(self):
        response = self.client.post(self.url, {}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_blank_id_token(self):
        response = self.client.post(self.url, {"id_token": ""}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @patch("accounts.views.google_login")
    def test_disabled_account(self, mock_google_login):
        mock_google_login.side_effect = ValueError("Account is disabled")

        response = self.client.post(self.url, {"id_token": "token"}, format="json")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @patch("accounts.views.google_login")
    def test_google_login_service_called(self, mock_google_login):
        mock_google_login.return_value = {"access": "a", "refresh": "r"}
        self.client.post(self.url, {"id_token": "token"}, format="json")
        mock_google_login.assert_called_once()


@pytest.mark.django_db
class TestGoogleLoginTestAPIView:
    @pytest.fixture(autouse=True)
    def setup_view(self, api_client):
        self.client = api_client
        self.url = reverse("google-test")

    def test_google_test_page_renders(self):
        response = self.client.get(self.url)
        assert response.status_code == status.HTTP_200_OK
        assertTemplateUsed(response, "google_login_test/google_test.html")

    @patch("accounts.views.settings.GOOGLE_CLIENT_ID", "client-id")
    def test_google_client_id_in_context(self):
        response = self.client.get(self.url)
        assert response.context["GOOGLE_CLIENT_ID"] == "client-id"