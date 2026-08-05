from django.contrib.auth.password_validation import validate_password
from django.test import TestCase
from rest_framework.exceptions import ErrorDetail

from accounts.models import User
from accounts.serializers import (
    RegisterSerializer,
    LoginSerializer,
    EmailSerializer,
    PasswordResetConfirmSerializer,
    RefreshTokenSerializer,
    GoogleLoginSerializer,
)


class RegisterSerializerTests(TestCase):

    def test_valid_serializer(self):
        serializer = RegisterSerializer(
            data={
                "email": "USER@Example.COM",
                "password": "StrongPassword@123",
                "first_name": " Himanshu ",
            }
        )

        self.assertTrue(serializer.is_valid())

        self.assertEqual(
            serializer.validated_data["email"],
            "user@example.com",
        )

        self.assertEqual(
            serializer.validated_data["first_name"],
            "Himanshu",
        )

    def test_duplicate_email_validation(self):
        User.objects.create_user(
            email="user@example.com",
            password="Password@123",
        )

        serializer = RegisterSerializer(
            data={
                "email": "USER@example.com",
                "password": "StrongPassword@123",
                "first_name": "Himanshu",
            }
        )

        self.assertFalse(serializer.is_valid())

        self.assertEqual(
            serializer.errors["email"][0],
            ErrorDetail(
                "A user with this email already exists.",
                code="invalid",
            ),
        )

    def test_first_name_is_trimmed(self):
        serializer = RegisterSerializer(
            data={
                "email": "user@example.com",
                "password": "StrongPassword@123",
                "first_name": "  Himanshu   ",
            }
        )

        self.assertTrue(serializer.is_valid())

        self.assertEqual(
            serializer.validated_data["first_name"],
            "Himanshu",
        )

    def test_blank_first_name_fails(self):
        serializer = RegisterSerializer(
            data={
                "email": "user@example.com",
                "password": "StrongPassword@123",
                "first_name": "     ",
            }
        )

        self.assertFalse(serializer.is_valid())

        self.assertEqual(
            serializer.errors["first_name"][0],
            ErrorDetail(
                "First name is required.",
                code="invalid",
            ),
        )

    def test_password_validation_called(self):
        serializer = RegisterSerializer()

        password = "StrongPassword@123"

        self.assertEqual(
            serializer.validate_password(password),
            password,
        )


class LoginSerializerTests(TestCase):

    def test_valid_login_serializer(self):
        serializer = LoginSerializer(
            data={
                "email": " USER@Example.COM ",
                "password": "Password@123",
            }
        )

        self.assertTrue(serializer.is_valid())

        self.assertEqual(
            serializer.validated_data["email"],
            "user@example.com",
        )

    def test_email_is_normalized(self):
        serializer = LoginSerializer()

        self.assertEqual(
            serializer.validate_email(
                " USER@Example.COM "
            ),
            "user@example.com",
        )


class EmailSerializerTests(TestCase):

    def test_valid_email_serializer(self):
        serializer = EmailSerializer(
            data={
                "email": " USER@Example.COM ",
            }
        )

        self.assertTrue(serializer.is_valid())

        self.assertEqual(
            serializer.validated_data["email"],
            "user@example.com",
        )

    def test_email_is_normalized(self):
        serializer = EmailSerializer()

        self.assertEqual(
            serializer.validate_email(
                " USER@Example.COM "
            ),
            "user@example.com",
        )


class PasswordResetConfirmSerializerTests(TestCase):

    def test_valid_serializer(self):
        serializer = PasswordResetConfirmSerializer(
            data={
                "token": " token123 ",
                "new_password": "StrongPassword@123",
            }
        )

        self.assertTrue(serializer.is_valid())

        self.assertEqual(
            serializer.validated_data["token"],
            "token123",
        )

    def test_blank_token_fails(self):
        serializer = PasswordResetConfirmSerializer(
            data={
                "token": "",
                "new_password": "StrongPassword@123",
            }
        )

        self.assertFalse(serializer.is_valid())

        self.assertEqual(
            serializer.errors["token"][0],
            ErrorDetail(
                "This field may not be blank.",
                code="blank",
            ),
        )

    def test_password_validation_called(self):
        serializer = PasswordResetConfirmSerializer()

        password = "StrongPassword@123"

        self.assertEqual(
            serializer.validate_new_password(
                password
            ),
            password,
        )


class RefreshTokenSerializerTests(TestCase):

    def test_valid_refresh_token(self):
        serializer = RefreshTokenSerializer(
            data={
                "refresh": " refresh-token ",
            }
        )

        self.assertTrue(serializer.is_valid())

        self.assertEqual(
            serializer.validated_data["refresh"],
            "refresh-token",
        )

    def test_blank_refresh_token_fails(self):
        serializer = RefreshTokenSerializer(
            data={
                "refresh": "",
            }
        )

        self.assertFalse(serializer.is_valid())

        self.assertEqual(
            serializer.errors["refresh"][0],
            ErrorDetail(
                "This field may not be blank.",
                code="blank",
            ),
        )


class GoogleLoginSerializerTests(TestCase):

    def test_valid_google_login_serializer(self):
        serializer = GoogleLoginSerializer(
            data={
                "id_token": " google-token ",
            }
        )

        self.assertTrue(serializer.is_valid())

        self.assertEqual(
            serializer.validated_data["id_token"],
            "google-token",
        )

    def test_blank_google_token_fails(self):
        serializer = GoogleLoginSerializer(
            data={
                "id_token": "",
            }
        )

        self.assertFalse(serializer.is_valid())

        self.assertEqual(
            serializer.errors["id_token"][0],
            ErrorDetail(
                "This field may not be blank.",
                code="blank",
            ),
        )