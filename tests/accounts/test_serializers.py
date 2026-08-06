import pytest
from rest_framework.exceptions import ErrorDetail

from accounts.serializers import (
    RegisterSerializer,
    LoginSerializer,
    EmailSerializer,
    PasswordResetConfirmSerializer,
    RefreshTokenSerializer,
    GoogleLoginSerializer,
)
from tests.factories import UserFactory


@pytest.mark.django_db
class TestRegisterSerializer:
    def test_valid_serializer(self):
        serializer = RegisterSerializer(
            data={
                "email": "USER@Example.COM",
                "password": "StrongPassword@123",
                "first_name": " Himanshu ",
            }
        )

        assert serializer.is_valid()
        assert serializer.validated_data["email"] == "user@example.com"
        assert serializer.validated_data["first_name"] == "Himanshu"

    def test_duplicate_email_validation(self):
        UserFactory(email="user@example.com")

        serializer = RegisterSerializer(
            data={
                "email": "USER@example.com",
                "password": "StrongPassword@123",
                "first_name": "Himanshu",
            }
        )

        assert not serializer.is_valid()
        assert serializer.errors["email"][0] == ErrorDetail(
            "A user with this email already exists.",
            code="invalid",
        )

    def test_first_name_is_trimmed(self):
        serializer = RegisterSerializer(
            data={
                "email": "user@example.com",
                "password": "StrongPassword@123",
                "first_name": "  Himanshu   ",
            }
        )

        assert serializer.is_valid()
        assert serializer.validated_data["first_name"] == "Himanshu"

    def test_blank_first_name_fails(self):
        serializer = RegisterSerializer(
            data={
                "email": "user@example.com",
                "password": "StrongPassword@123",
                "first_name": "     ",
            }
        )

        assert not serializer.is_valid()
        assert serializer.errors["first_name"][0] == ErrorDetail(
            "First name is required.",
            code="invalid",
        )

    def test_password_validation_called(self):
        serializer = RegisterSerializer()
        password = "StrongPassword@123"
        assert serializer.validate_password(password) == password


class TestLoginSerializer:
    def test_valid_login_serializer(self):
        serializer = LoginSerializer(
            data={
                "email": " USER@Example.COM ",
                "password": "Password@123",
            }
        )

        assert serializer.is_valid()
        assert serializer.validated_data["email"] == "user@example.com"

    def test_email_is_normalized(self):
        serializer = LoginSerializer()
        assert serializer.validate_email(" USER@Example.COM ") == "user@example.com"


class TestEmailSerializer:
    def test_valid_email_serializer(self):
        serializer = EmailSerializer(
            data={
                "email": " USER@Example.COM ",
            }
        )

        assert serializer.is_valid()
        assert serializer.validated_data["email"] == "user@example.com"

    def test_email_is_normalized(self):
        serializer = EmailSerializer()
        assert serializer.validate_email(" USER@Example.COM ") == "user@example.com"


class TestPasswordResetConfirmSerializer:
    def test_valid_serializer(self):
        serializer = PasswordResetConfirmSerializer(
            data={
                "token": " token123 ",
                "new_password": "StrongPassword@123",
            }
        )

        assert serializer.is_valid()
        assert serializer.validated_data["token"] == "token123"

    def test_blank_token_fails(self):
        serializer = PasswordResetConfirmSerializer(
            data={
                "token": "",
                "new_password": "StrongPassword@123",
            }
        )

        assert not serializer.is_valid()
        assert serializer.errors["token"][0] == ErrorDetail(
            "This field may not be blank.",
            code="blank",
        )

    def test_password_validation_called(self):
        serializer = PasswordResetConfirmSerializer()
        password = "StrongPassword@123"
        assert serializer.validate_new_password(password) == password


class TestRefreshTokenSerializer:
    def test_valid_refresh_token(self):
        serializer = RefreshTokenSerializer(
            data={
                "refresh": " refresh-token ",
            }
        )

        assert serializer.is_valid()
        assert serializer.validated_data["refresh"] == "refresh-token"

    def test_blank_refresh_token_fails(self):
        serializer = RefreshTokenSerializer(
            data={
                "refresh": "",
            }
        )

        assert not serializer.is_valid()
        assert serializer.errors["refresh"][0] == ErrorDetail(
            "This field may not be blank.",
            code="blank",
        )


class TestGoogleLoginSerializer:
    def test_valid_google_login_serializer(self):
        serializer = GoogleLoginSerializer(
            data={
                "id_token": " google-token ",
            }
        )

        assert serializer.is_valid()
        assert serializer.validated_data["id_token"] == "google-token"

    def test_blank_google_token_fails(self):
        serializer = GoogleLoginSerializer(
            data={
                "id_token": "",
            }
        )

        assert not serializer.is_valid()
        assert serializer.errors["id_token"][0] == ErrorDetail(
            "This field may not be blank.",
            code="blank",
        )