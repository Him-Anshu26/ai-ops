# accounts/tests/test_models.py

from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from accounts.models import (
    User,
    EmailVerificationToken,
    PasswordResetToken,
    UserSession,
)


class UserModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="TEST@Example.COM",
            password="StrongPassword123!",
            first_name="Himanshu",
        )

    def test_email_is_normalized_on_save(self):
        self.assertEqual(self.user.email, "test@example.com")

    def test_default_is_verified_false(self):
        self.assertFalse(self.user.is_verified)

    def test_default_auth_provider_local(self):
        self.assertEqual(self.user.auth_provider, "local")

    def test_provider_id_default_none(self):
        self.assertIsNone(self.user.provider_id)

    def test_string_representation_returns_email(self):
        self.assertEqual(str(self.user), self.user.email)

    def test_username_field_is_email(self):
        self.assertEqual(User.USERNAME_FIELD, "email")

    def test_required_fields_empty(self):
        self.assertEqual(User.REQUIRED_FIELDS, [])


class EmailVerificationTokenModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="user@example.com",
            password="Password123!",
        )

        cls.token = EmailVerificationToken.objects.create(
            user=cls.user,
            token_hash="verification_hash",
        )

    def test_string_representation(self):
        self.assertEqual(
            str(self.token),
            f"EmailToken(user_id={self.user.id})",
        )

    def test_token_not_expired_initially(self):
        self.assertFalse(self.token.is_expired())

    def test_token_expired_after_24_hours(self):
        self.token.created_at = (
            timezone.now() - timedelta(hours=25)
        )
        self.assertTrue(self.token.is_expired())

    def test_related_name_email_tokens(self):
        self.assertEqual(
            self.user.email_tokens.count(),
            1,
        )

    def test_cascade_delete_user_removes_token(self):
        token_id = self.token.id
        self.user.delete()

        self.assertFalse(
            EmailVerificationToken.objects.filter(
                id=token_id
            ).exists()
        )


class PasswordResetTokenModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="reset@example.com",
            password="Password123!",
        )

        cls.token = PasswordResetToken.objects.create(
            user=cls.user,
            token_hash="reset_hash",
        )

    def test_string_representation(self):
        self.assertEqual(
            str(self.token),
            f"PasswordResetToken(user_id={self.user.id})",
        )

    def test_token_not_expired_initially(self):
        self.assertFalse(self.token.is_expired())

    def test_token_expired_after_30_minutes(self):
        self.token.created_at = (
            timezone.now() - timedelta(minutes=31)
        )
        self.assertTrue(self.token.is_expired())

    def test_related_name_password_reset_tokens(self):
        self.assertEqual(
            self.user.password_reset_tokens.count(),
            1,
        )

    def test_cascade_delete_user_removes_reset_token(self):
        token_id = self.token.id
        self.user.delete()

        self.assertFalse(
            PasswordResetToken.objects.filter(
                id=token_id
            ).exists()
        )


class UserSessionModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="session@example.com",
            password="Password123!",
        )

        cls.session = UserSession.objects.create(
            user=cls.user,
            session_id="session_123",
            refresh_token_hash="refresh_hash",
        )

    def test_default_is_active_true(self):
        self.assertTrue(self.session.is_active)

    def test_string_representation(self):
        self.assertEqual(
            str(self.session),
            f"Session(user_id={self.user.id}, active=True)",
        )

    def test_related_name_sessions(self):
        self.assertEqual(
            self.user.sessions.count(),
            1,
        )

    def test_cascade_delete_user_removes_sessions(self):
        session_id = self.session.id

        self.user.delete()

        self.assertFalse(
            UserSession.objects.filter(
                id=session_id
            ).exists()
        )

    def test_session_active_index_exists(self):
        indexes = UserSession._meta.indexes

        fields = [tuple(index.fields) for index in indexes]

        self.assertIn(
            ("session_id", "is_active"),
            fields,
        )

        self.assertIn(
            ("user", "is_active"),
            fields,
        )