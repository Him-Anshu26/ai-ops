import pytest
from datetime import timedelta
from django.utils import timezone

from accounts.models import (
    User,
    EmailVerificationToken,
    PasswordResetToken,
    UserSession,
)
from tests.factories import (
    UserFactory,
    EmailVerificationTokenFactory,
    PasswordResetTokenFactory,
    UserSessionFactory,
)


@pytest.mark.django_db
class TestUserModel:
    @pytest.fixture(autouse=True)
    def setup_user(self):
        # We explicitly use create_user here instead of UserFactory because 
        # test_email_is_normalized_on_save tests the custom UserManager's create_user method directly.
        self.user = User.objects.create_user(
            email="TEST@Example.COM",
            password="StrongPassword123!",
            first_name="Himanshu",
        )

    def test_email_is_normalized_on_save(self):
        assert self.user.email == "test@example.com"

    def test_default_is_verified_false(self):
        assert not self.user.is_verified

    def test_default_auth_provider_local(self):
        assert self.user.auth_provider == "local"

    def test_provider_id_default_none(self):
        assert self.user.provider_id is None

    def test_string_representation_returns_email(self):
        assert str(self.user) == self.user.email

    def test_username_field_is_email(self):
        assert User.USERNAME_FIELD == "email"

    def test_required_fields_empty(self):
        assert User.REQUIRED_FIELDS == []


@pytest.mark.django_db
class TestEmailVerificationTokenModel:
    @pytest.fixture(autouse=True)
    def setup_token(self):
        self.user = UserFactory(email="user@example.com")
        self.token = EmailVerificationTokenFactory(
            user=self.user,
            token_hash="verification_hash",
        )

    def test_string_representation(self):
        assert str(self.token) == f"EmailToken(user_id={self.user.id})"

    def test_token_not_expired_initially(self):
        assert not self.token.is_expired()

    def test_token_expired_after_24_hours(self):
        self.token.created_at = timezone.now() - timedelta(hours=25)
        assert self.token.is_expired()

    def test_related_name_email_tokens(self):
        assert self.user.email_tokens.count() == 1

    def test_cascade_delete_user_removes_token(self):
        token_id = self.token.id
        self.user.delete()
        assert not EmailVerificationToken.objects.filter(id=token_id).exists()


@pytest.mark.django_db
class TestPasswordResetTokenModel:
    @pytest.fixture(autouse=True)
    def setup_token(self):
        self.user = UserFactory(email="reset@example.com")
        self.token = PasswordResetTokenFactory(
            user=self.user,
            token_hash="reset_hash",
        )

    def test_string_representation(self):
        assert str(self.token) == f"PasswordResetToken(user_id={self.user.id})"

    def test_token_not_expired_initially(self):
        assert not self.token.is_expired()

    def test_token_expired_after_30_minutes(self):
        self.token.created_at = timezone.now() - timedelta(minutes=31)
        assert self.token.is_expired()

    def test_related_name_password_reset_tokens(self):
        assert self.user.password_reset_tokens.count() == 1

    def test_cascade_delete_user_removes_reset_token(self):
        token_id = self.token.id
        self.user.delete()
        assert not PasswordResetToken.objects.filter(id=token_id).exists()


@pytest.mark.django_db
class TestUserSessionModel:
    @pytest.fixture(autouse=True)
    def setup_session(self):
        self.user = UserFactory(email="session@example.com")
        self.session = UserSessionFactory(
            user=self.user,
            session_id="session_123",
            refresh_token_hash="refresh_hash",
        )

    def test_default_is_active_true(self):
        assert self.session.is_active

    def test_string_representation(self):
        assert str(self.session) == f"Session(user_id={self.user.id}, active=True)"

    def test_related_name_sessions(self):
        assert self.user.sessions.count() == 1

    def test_cascade_delete_user_removes_sessions(self):
        session_id = self.session.id
        self.user.delete()
        assert not UserSession.objects.filter(id=session_id).exists()

    def test_session_active_index_exists(self):
        indexes = UserSession._meta.indexes
        fields = [tuple(index.fields) for index in indexes]
        
        assert ("session_id", "is_active") in fields
        assert ("user", "is_active") in fields