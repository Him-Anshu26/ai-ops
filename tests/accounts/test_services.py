from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from allauth.socialaccount.models import SocialAccount

from accounts.models import (
    User,
    EmailVerificationToken,
    PasswordResetToken,
    UserSession,
)

from accounts.services import (
    GoogleLoginService,
    create_user,
    send_verification_email,
    verify_email,
    resend_verification_email,
    login_user,
    refresh_access_token,
    logout_user,
    request_password_reset,
    reset_password,
    cleanup_expired_verification_tokens,
    cleanup_expired_password_reset_tokens,
    cleanup_inactive_sessions,
)

from accounts.utils import hash_token


class CreateUserServiceTests(TestCase):

    def test_create_user_successfully(self):
        user = create_user(
            email="TEST@Example.COM",
            password="StrongPassword@123",
            first_name=" Himanshu ",
        )

        self.assertEqual(user.email, "test@example.com")
        self.assertEqual(user.first_name, "Himanshu")
        self.assertFalse(user.is_verified)
        self.assertTrue(user.check_password("StrongPassword@123"))

    def test_duplicate_email_raises_error(self):
        User.objects.create_user(
            email="test@example.com",
            password="Password@123",
        )

        with self.assertRaisesMessage(
            ValueError,
            "User already exists",
        ):
            create_user(
                email="TEST@example.com",
                password="Password@123",
            )


class SendVerificationEmailServiceTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email="user@example.com",
            password="Password@123",
            is_verified=False,
        )

    @patch("accounts.services.send_email")
    @patch("accounts.services.generate_token")
    @patch("accounts.services.build_verification_link")
    def test_send_verification_email_creates_token(
        self,
        mock_build_link,
        mock_generate_token,
        mock_send_email,
    ):
        raw_token = "raw-token"

        mock_generate_token.return_value = raw_token
        mock_build_link.return_value = "http://verify"

        send_verification_email(self.user)

        self.assertEqual(
            EmailVerificationToken.objects.count(),
            1,
        )

        token = EmailVerificationToken.objects.get()

        self.assertEqual(
            token.token_hash,
            hash_token(raw_token),
        )

        mock_send_email.assert_called_once()

    @patch("accounts.services.send_email")
    def test_verified_user_receives_no_email(
        self,
        mock_send_email,
    ):
        self.user.is_verified = True
        self.user.save()

        send_verification_email(self.user)

        self.assertEqual(
            EmailVerificationToken.objects.count(),
            0,
        )

        mock_send_email.assert_not_called()

    @patch("accounts.services.send_email")
    @patch("accounts.services.generate_token")
    @patch("accounts.services.build_verification_link")
    def test_previous_tokens_are_removed(
        self,
        mock_build_link,
        mock_generate_token,
        mock_send_email,
    ):
        EmailVerificationToken.objects.create(
            user=self.user,
            token_hash="old",
        )

        mock_generate_token.return_value = "new-token"
        mock_build_link.return_value = "verify-link"

        send_verification_email(self.user)

        self.assertEqual(
            EmailVerificationToken.objects.count(),
            1,
        )

        token = EmailVerificationToken.objects.get()

        self.assertEqual(
            token.token_hash,
            hash_token("new-token"),
        )


class VerifyEmailServiceTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email="user@example.com",
            password="Password@123",
            is_verified=False,
        )

        self.raw_token = "verification-token"

        self.token = EmailVerificationToken.objects.create(
            user=self.user,
            token_hash=hash_token(self.raw_token),
        )

    def test_verify_email_successfully(self):
        verified_user = verify_email(self.raw_token)

        verified_user.refresh_from_db()

        self.assertTrue(verified_user.is_verified)

        self.assertFalse(
            EmailVerificationToken.objects.filter(
                id=self.token.id
            ).exists()
        )

    def test_invalid_token_raises_error(self):
        with self.assertRaisesMessage(
            ValueError,
            "Invalid token",
        ):
            verify_email("wrong-token")

    def test_expired_token_raises_error(self):
        EmailVerificationToken.objects.filter(
            id=self.token.id
        ).update(
            created_at=timezone.now() - timedelta(hours=25)
        )

        with self.assertRaisesMessage(
            ValueError,
            "Token expired",
        ):
            verify_email(self.raw_token)

    def test_already_verified_user_is_supported(self):
        self.user.is_verified = True
        self.user.save()

        verify_email(self.raw_token)

        self.user.refresh_from_db()

        self.assertTrue(self.user.is_verified)

        self.assertFalse(
            EmailVerificationToken.objects.exists()
        )


class ResendVerificationEmailServiceTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email="user@example.com",
            password="Password@123",
            is_verified=False,
        )

    @patch("accounts.services.send_verification_email")
    def test_resend_verification_email(
        self,
        mock_send_verification_email,
    ):
        resend_verification_email("USER@example.com")

        mock_send_verification_email.assert_called_once_with(
            self.user
        )

    @patch("accounts.services.send_verification_email")
    def test_verified_user_does_not_receive_email(
        self,
        mock_send_verification_email,
    ):
        self.user.is_verified = True
        self.user.save()

        resend_verification_email(self.user.email)

        mock_send_verification_email.assert_not_called()

    @patch("accounts.services.send_verification_email")
    def test_unknown_email_returns_silently(
        self,
        mock_send_verification_email,
    ):
        resend_verification_email("unknown@example.com")

        mock_send_verification_email.assert_not_called()




class LoginUserServiceTests(TestCase):

    def setUp(self):
        self.password = "Password@123"

        self.user = User.objects.create_user(
            email="user@example.com",
            password=self.password,
            is_verified=True,
            is_active=True,
        )

    @patch("accounts.services.generate_token")
    @patch("accounts.services.generate_refresh_token")
    @patch("accounts.services.generate_access_token")
    def test_login_successfully(
        self,
        mock_access,
        mock_refresh,
        mock_session,
    ):
        mock_session.return_value = "session-id"
        mock_refresh.return_value = "refresh-token"
        mock_access.return_value = "access-token"

        tokens = login_user(
            email=self.user.email,
            password=self.password,
        )

        self.assertEqual(
            tokens["access"],
            "access-token",
        )

        self.assertEqual(
            tokens["refresh"],
            "refresh-token",
        )

        session = UserSession.objects.get(
            user=self.user
        )

        self.assertEqual(
            session.session_id,
            "session-id",
        )

        self.assertEqual(
            session.refresh_token_hash,
            hash_token("refresh-token"),
        )

        self.assertTrue(session.is_active)

    def test_login_unknown_email(self):
        with self.assertRaisesMessage(
            ValueError,
            "Invalid credentials",
        ):
            login_user(
                email="unknown@example.com",
                password=self.password,
            )

    def test_login_wrong_password(self):
        with self.assertRaisesMessage(
            ValueError,
            "Invalid credentials",
        ):
            login_user(
                email=self.user.email,
                password="WrongPassword",
            )

    def test_login_unverified_user(self):
        self.user.is_verified = False
        self.user.save()

        with self.assertRaisesMessage(
            ValueError,
            "Email is not verified",
        ):
            login_user(
                email=self.user.email,
                password=self.password,
            )

    def test_login_disabled_account(self):
        self.user.is_active = False
        self.user.save()

        with self.assertRaisesMessage(
            ValueError,
            "Account is disabled",
        ):
            login_user(
                email=self.user.email,
                password=self.password,
            )


class RefreshAccessTokenServiceTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email="user@example.com",
            password="Password@123",
            is_verified=True,
        )

        self.session = UserSession.objects.create(
            user=self.user,
            session_id="session-123",
            refresh_token_hash=hash_token("refresh-token"),
            is_active=True,
        )

    @patch("accounts.services.decode_token")
    @patch("accounts.services.generate_access_token")
    def test_refresh_access_token_success(
        self,
        mock_generate_access,
        mock_decode,
    ):
        mock_decode.return_value = {
            "user_id": self.user.id,
            "session_id": self.session.session_id,
        }

        mock_generate_access.return_value = "new-access"

        access = refresh_access_token(
            "refresh-token"
        )

        self.assertEqual(
            access,
            "new-access",
        )

        mock_generate_access.assert_called_once_with(
            user=self.user,
            session_id=self.session.session_id,
        )

    @patch("accounts.services.decode_token")
    def test_invalid_refresh_token(self, mock_decode):
        mock_decode.return_value = None

        with self.assertRaisesMessage(
            ValueError,
            "Invalid token",
        ):
            refresh_access_token(
                "refresh-token"
            )

    @patch("accounts.services.decode_token")
    def test_invalid_payload(self, mock_decode):
        mock_decode.return_value = {
            "user_id": self.user.id,
        }

        with self.assertRaisesMessage(
            ValueError,
            "Invalid token payload",
        ):
            refresh_access_token(
                "refresh-token"
            )

    @patch("accounts.services.decode_token")
    def test_missing_session(self, mock_decode):
        self.session.delete()

        mock_decode.return_value = {
            "user_id": self.user.id,
            "session_id": "session-123",
        }

        with self.assertRaisesMessage(
            ValueError,
            "Session expired",
        ):
            refresh_access_token(
                "refresh-token"
            )

    @patch("accounts.services.decode_token")
    def test_disabled_user(self, mock_decode):
        self.user.is_active = False
        self.user.save()

        mock_decode.return_value = {
            "user_id": self.user.id,
            "session_id": self.session.session_id,
        }

        with self.assertRaisesMessage(
            ValueError,
            "Account disabled",
        ):
            refresh_access_token(
                "refresh-token"
            )

    @patch("accounts.services.decode_token")
    def test_refresh_token_hash_mismatch(
        self,
        mock_decode,
    ):
        mock_decode.return_value = {
            "user_id": self.user.id,
            "session_id": self.session.session_id,
        }

        with self.assertRaisesMessage(
            ValueError,
            "Invalid token",
        ):
            refresh_access_token(
                "tampered-token"
            )


class LogoutUserServiceTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email="user@example.com",
            password="Password@123",
        )

        self.session = UserSession.objects.create(
            user=self.user,
            session_id="session-123",
            refresh_token_hash="hash",
            is_active=True,
        )

    def test_logout_deactivates_session(self):
        logout_user(
            self.session.session_id
        )

        self.session.refresh_from_db()

        self.assertFalse(
            self.session.is_active
        )

    def test_logout_unknown_session(self):
        logout_user("does-not-exist")

        self.assertEqual(
            UserSession.objects.count(),
            1,
        )

        self.session.refresh_from_db()

        self.assertTrue(
            self.session.is_active
        )


class RequestPasswordResetServiceTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email="user@example.com",
            password="Password@123",
            first_name="Himanshu",
        )

    @patch("accounts.services.send_email")
    @patch("accounts.services.generate_token")
    @patch("accounts.services.build_reset_link")
    def test_request_password_reset_successfully(
        self,
        mock_build_link,
        mock_generate_token,
        mock_send_email,
    ):
        mock_generate_token.return_value = "raw-reset-token"
        mock_build_link.return_value = "http://reset"

        request_password_reset(self.user.email)

        self.assertEqual(
            PasswordResetToken.objects.count(),
            1,
        )

        token = PasswordResetToken.objects.get()

        self.assertEqual(
            token.token_hash,
            hash_token("raw-reset-token"),
        )

        mock_send_email.assert_called_once()

    @patch("accounts.services.send_email")
    @patch("accounts.services.generate_token")
    @patch("accounts.services.build_reset_link")
    def test_previous_reset_tokens_are_deleted(
        self,
        mock_build_link,
        mock_generate_token,
        mock_send_email,
    ):
        PasswordResetToken.objects.create(
            user=self.user,
            token_hash="old-token",
        )

        mock_generate_token.return_value = "new-token"
        mock_build_link.return_value = "reset-link"

        request_password_reset(self.user.email)

        self.assertEqual(
            PasswordResetToken.objects.count(),
            1,
        )

        token = PasswordResetToken.objects.get()

        self.assertEqual(
            token.token_hash,
            hash_token("new-token"),
        )

    @patch("accounts.services.send_email")
    def test_unknown_email_returns_silently(
        self,
        mock_send_email,
    ):
        request_password_reset(
            "unknown@example.com"
        )

        self.assertEqual(
            PasswordResetToken.objects.count(),
            0,
        )

        mock_send_email.assert_not_called()


class ResetPasswordServiceTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email="user@example.com",
            password="OldPassword@123",
            is_verified=True,
        )

        self.raw_token = "reset-token"

        self.reset_token = PasswordResetToken.objects.create(
            user=self.user,
            token_hash=hash_token(self.raw_token),
        )

    def test_reset_password_successfully(self):

        UserSession.objects.create(
            user=self.user,
            session_id="session-1",
            refresh_token_hash="hash",
            is_active=True,
        )

        UserSession.objects.create(
            user=self.user,
            session_id="session-2",
            refresh_token_hash="hash",
            is_active=True,
        )

        reset_password(
            token=self.raw_token,
            new_password="NewPassword@123",
        )

        self.user.refresh_from_db()

        self.assertTrue(
            self.user.check_password(
                "NewPassword@123"
            )
        )

        self.assertFalse(
            PasswordResetToken.objects.exists()
        )

        self.assertEqual(
            UserSession.objects.filter(
                is_active=True
            ).count(),
            0,
        )

    def test_invalid_token_raises_error(self):

        with self.assertRaisesMessage(
            ValueError,
            "Invalid token",
        ):
            reset_password(
                token="wrong-token",
                new_password="Password@123",
            )

    def test_expired_token_raises_error(self):

        PasswordResetToken.objects.filter(
            id=self.reset_token.id
        ).update(
            created_at=timezone.now()
            - timedelta(minutes=31)
        )

        with self.assertRaisesMessage(
            ValueError,
            "Token expired",
        ):
            reset_password(
                token=self.raw_token,
                new_password="Password@123",
            )


    def test_password_is_changed(self):

        old_hash = self.user.password

        reset_password(
            token=self.raw_token,
            new_password="BrandNewPassword@123",
        )

        self.user.refresh_from_db()

        self.assertNotEqual(
            old_hash,
            self.user.password,
        )

        self.assertTrue(
            self.user.check_password(
                "BrandNewPassword@123"
            )
        )

    def test_all_sessions_are_invalidated(self):

        active1 = UserSession.objects.create(
            user=self.user,
            session_id="s1",
            refresh_token_hash="hash",
            is_active=True,
        )

        active2 = UserSession.objects.create(
            user=self.user,
            session_id="s2",
            refresh_token_hash="hash",
            is_active=True,
        )

        reset_password(
            token=self.raw_token,
            new_password="Password@12345",
        )

        active1.refresh_from_db()
        active2.refresh_from_db()

        self.assertFalse(active1.is_active)
        self.assertFalse(active2.is_active)

    def test_used_token_is_deleted(self):

        reset_password(
            token=self.raw_token,
            new_password="Password@12345",
        )

        self.assertEqual(
            PasswordResetToken.objects.count(),
            0,
        )

class CleanupExpiredVerificationTokensServiceTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email="user@example.com",
            password="Password@123",
        )

    def test_cleanup_deletes_only_expired_tokens(self):
        expired = EmailVerificationToken.objects.create(
            user=self.user,
            token_hash="expired-token",
        )

        valid = EmailVerificationToken.objects.create(
            user=self.user,
            token_hash="valid-token",
        )

        EmailVerificationToken.objects.filter(
            id=expired.id
        ).update(
            created_at=timezone.now() - timedelta(hours=25)
        )

        deleted = cleanup_expired_verification_tokens()

        self.assertEqual(deleted, 1)

        self.assertFalse(
            EmailVerificationToken.objects.filter(
                id=expired.id
            ).exists()
        )

        self.assertTrue(
            EmailVerificationToken.objects.filter(
                id=valid.id
            ).exists()
        )

    def test_cleanup_when_no_expired_tokens(self):
        EmailVerificationToken.objects.create(
            user=self.user,
            token_hash="valid-token",
        )

        deleted = cleanup_expired_verification_tokens()

        self.assertEqual(deleted, 0)

        self.assertEqual(
            EmailVerificationToken.objects.count(),
            1,
        )


class CleanupExpiredPasswordResetTokensServiceTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email="user@example.com",
            password="Password@123",
        )

    def test_cleanup_deletes_only_expired_reset_tokens(self):
        expired = PasswordResetToken.objects.create(
            user=self.user,
            token_hash="expired-reset",
        )

        valid = PasswordResetToken.objects.create(
            user=self.user,
            token_hash="valid-reset",
        )

        PasswordResetToken.objects.filter(
            id=expired.id
        ).update(
            created_at=timezone.now() - timedelta(minutes=31)
        )

        deleted = cleanup_expired_password_reset_tokens()

        self.assertEqual(deleted, 1)

        self.assertFalse(
            PasswordResetToken.objects.filter(
                id=expired.id
            ).exists()
        )

        self.assertTrue(
            PasswordResetToken.objects.filter(
                id=valid.id
            ).exists()
        )

    def test_cleanup_when_nothing_is_expired(self):
        PasswordResetToken.objects.create(
            user=self.user,
            token_hash="valid-reset",
        )

        deleted = cleanup_expired_password_reset_tokens()

        self.assertEqual(deleted, 0)

        self.assertEqual(
            PasswordResetToken.objects.count(),
            1,
        )


class CleanupInactiveSessionsServiceTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email="user@example.com",
            password="Password@123",
        )

    def test_cleanup_removes_old_inactive_sessions(self):
        old_session = UserSession.objects.create(
            user=self.user,
            session_id="old-session",
            refresh_token_hash="hash",
            is_active=False,
        )

        recent_session = UserSession.objects.create(
            user=self.user,
            session_id="recent-session",
            refresh_token_hash="hash",
            is_active=False,
        )

        active_session = UserSession.objects.create(
            user=self.user,
            session_id="active-session",
            refresh_token_hash="hash",
            is_active=True,
        )

        UserSession.objects.filter(
            id=old_session.id
        ).update(
            created_at=timezone.now() - timedelta(days=91)
        )

        deleted = cleanup_inactive_sessions()

        self.assertEqual(deleted, 1)

        self.assertFalse(
            UserSession.objects.filter(
                id=old_session.id
            ).exists()
        )

        self.assertTrue(
            UserSession.objects.filter(
                id=recent_session.id
            ).exists()
        )

        self.assertTrue(
            UserSession.objects.filter(
                id=active_session.id
            ).exists()
        )

    def test_cleanup_when_no_sessions_are_old(self):
        UserSession.objects.create(
            user=self.user,
            session_id="inactive",
            refresh_token_hash="hash",
            is_active=False,
        )

        deleted = cleanup_inactive_sessions()

        self.assertEqual(deleted, 0)

        self.assertEqual(
            UserSession.objects.count(),
            1,
        )


class GoogleVerifyTokenServiceTests(TestCase):

    def setUp(self):
        self.service = GoogleLoginService()

    @patch("accounts.services.id_token.verify_oauth2_token")
    def test_verify_google_token_success(self, mock_verify):
        mock_verify.return_value = {
            "email": "user@example.com",
            "sub": "google-123",
            "email_verified": True,
            "iss": "accounts.google.com",
        }

        data = self.service.verify_google_token("token")

        self.assertEqual(
            data["email"],
            "user@example.com",
        )

    @patch("accounts.services.id_token.verify_oauth2_token")
    def test_invalid_google_token(self, mock_verify):
        mock_verify.side_effect = ValueError()

        with self.assertRaisesMessage(
            ValueError,
            "Invalid Google token",
        ):
            self.service.verify_google_token("bad-token")

    @patch("accounts.services.id_token.verify_oauth2_token")
    def test_missing_email(self, mock_verify):
        mock_verify.return_value = {
            "sub": "google-123",
            "email_verified": True,
            "iss": "accounts.google.com",
        }

        with self.assertRaisesMessage(
            ValueError,
            "Email not provided by Google",
        ):
            self.service.verify_google_token("token")

    @patch("accounts.services.id_token.verify_oauth2_token")
    def test_missing_google_subject(self, mock_verify):
        mock_verify.return_value = {
            "email": "user@example.com",
            "email_verified": True,
            "iss": "accounts.google.com",
        }

        with self.assertRaisesMessage(
            ValueError,
            "Invalid Google account",
        ):
            self.service.verify_google_token("token")

    @patch("accounts.services.id_token.verify_oauth2_token")
    def test_email_not_verified(self, mock_verify):
        mock_verify.return_value = {
            "email": "user@example.com",
            "sub": "google-123",
            "email_verified": False,
            "iss": "accounts.google.com",
        }

        with self.assertRaisesMessage(
            ValueError,
            "Google email is not verified",
        ):
            self.service.verify_google_token("token")

    @patch("accounts.services.id_token.verify_oauth2_token")
    def test_invalid_google_issuer(self, mock_verify):
        mock_verify.return_value = {
            "email": "user@example.com",
            "sub": "google-123",
            "email_verified": True,
            "iss": "malicious.com",
        }

        with self.assertRaisesMessage(
            ValueError,
            "Invalid Google issuer",
        ):
            self.service.verify_google_token("token")


class GoogleGetOrCreateUserTests(TestCase):

    def setUp(self):
        self.service = GoogleLoginService()

        self.google_data = {
            "email": "user@example.com",
            "sub": "google-123",
            "given_name": "Himanshu",
        }

    def test_create_new_google_user(self):
        user = self.service.get_or_create_user(
            self.google_data
        )

        self.assertEqual(
            user.email,
            "user@example.com",
        )

        self.assertEqual(
            user.first_name,
            "Himanshu",
        )

        self.assertEqual(
            user.auth_provider,
            "google",
        )

        self.assertEqual(
            user.provider_id,
            "google-123",
        )

        self.assertTrue(user.is_verified)

        self.assertTrue(
            SocialAccount.objects.filter(
                user=user,
                provider="google",
            ).exists()
        )

    def test_existing_local_user_is_updated(self):
        user = User.objects.create_user(
            email="user@example.com",
            password="Password@123",
            is_verified=False,
        )

        returned = self.service.get_or_create_user(
            self.google_data
        )

        returned.refresh_from_db()

        self.assertEqual(
            returned.id,
            user.id,
        )

        self.assertEqual(
            returned.auth_provider,
            "google",
        )

        self.assertEqual(
            returned.provider_id,
            "google-123",
        )

        self.assertTrue(
            returned.is_verified
        )

        self.assertTrue(
            SocialAccount.objects.filter(
                user=returned,
                provider="google",
            ).exists()
        )

    def test_existing_google_user_returns_same_user(self):
        user = User.objects.create_user(
            email="user@example.com",
            password="Password@123",
            auth_provider="google",
            provider_id="google-123",
            is_verified=True,
        )

        SocialAccount.objects.create(
            user=user,
            provider="google",
            uid="google-123",
        )

        returned = self.service.get_or_create_user(
            self.google_data
        )

        self.assertEqual(
            returned.id,
            user.id,
        )

        self.assertEqual(
            SocialAccount.objects.count(),
            1,
        )

    def test_disabled_user_cannot_login(self):
        User.objects.create_user(
            email="user@example.com",
            password="Password@123",
            is_active=False,
        )

        with self.assertRaisesMessage(
            ValueError,
            "Account is disabled",
        ):
            self.service.get_or_create_user(
                self.google_data
            )

    def test_email_is_normalized(self):
        self.google_data["email"] = "USER@Example.COM"

        user = self.service.get_or_create_user(
            self.google_data
        )

        self.assertEqual(
            user.email,
            "user@example.com",
        )

class GoogleCreateUserSessionTests(TestCase):

    def setUp(self):
        self.service = GoogleLoginService()

        self.user = User.objects.create_user(
            email="user@example.com",
            password="Password@123",
            is_verified=True,
        )

    @patch("accounts.services.generate_token")
    @patch("accounts.services.generate_refresh_token")
    @patch("accounts.services.generate_access_token")
    def test_create_user_session_success(
        self,
        mock_access,
        mock_refresh,
        mock_generate,
    ):
        mock_generate.return_value = "session-123"
        mock_refresh.return_value = "refresh-token"
        mock_access.return_value = "access-token"

        tokens = self.service.create_user_session(
            self.user
        )

        self.assertEqual(
            tokens["access"],
            "access-token",
        )

        self.assertEqual(
            tokens["refresh"],
            "refresh-token",
        )

        session = UserSession.objects.get()

        self.assertEqual(
            session.session_id,
            "session-123",
        )

        self.assertEqual(
            session.refresh_token_hash,
            hash_token("refresh-token"),
        )

        self.assertTrue(session.is_active)

    @patch("accounts.services.generate_token")
    @patch("accounts.services.generate_refresh_token")
    @patch("accounts.services.generate_access_token")
    def test_refresh_token_is_hashed(
        self,
        mock_access,
        mock_refresh,
        mock_generate,
    ):
        mock_generate.return_value = "session-id"
        mock_refresh.return_value = "refresh-token"
        mock_access.return_value = "access-token"

        self.service.create_user_session(
            self.user
        )

        session = UserSession.objects.get()

        self.assertNotEqual(
            session.refresh_token_hash,
            "refresh-token",
        )

        self.assertEqual(
            session.refresh_token_hash,
            hash_token("refresh-token"),
        )


class GoogleLoginServiceTests(TestCase):

    def setUp(self):
        self.service = GoogleLoginService()

        self.user = User.objects.create_user(
            email="user@example.com",
            password="Password@123",
            is_verified=True,
        )

        self.id_info = {
            "email": self.user.email,
            "sub": "google-123",
            "given_name": "Himanshu",
        }

    @patch.object(
        GoogleLoginService,
        "verify_google_token",
    )
    @patch.object(
        GoogleLoginService,
        "get_or_create_user",
    )
    @patch.object(
        GoogleLoginService,
        "create_user_session",
    )
    def test_google_login_success(
        self,
        mock_session,
        mock_get_user,
        mock_verify,
    ):
        mock_verify.return_value = self.id_info
        mock_get_user.return_value = self.user
        mock_session.return_value = {
            "access": "access-token",
            "refresh": "refresh-token",
        }

        result = self.service("google-token")

        self.assertEqual(
            result["access"],
            "access-token",
        )

        self.assertEqual(
            result["refresh"],
            "refresh-token",
        )

        mock_verify.assert_called_once_with(
            "google-token"
        )

        mock_get_user.assert_called_once_with(
            self.id_info
        )

        mock_session.assert_called_once_with(
            self.user
        )

    @patch.object(
        GoogleLoginService,
        "verify_google_token",
    )
    def test_verify_google_token_failure(
        self,
        mock_verify,
    ):
        mock_verify.side_effect = ValueError(
            "Invalid Google token"
        )

        with self.assertRaisesMessage(
            ValueError,
            "Invalid Google token",
        ):
            self.service("token")

    @patch.object(
        GoogleLoginService,
        "verify_google_token",
    )
    @patch.object(
        GoogleLoginService,
        "get_or_create_user",
    )
    def test_get_user_failure(
        self,
        mock_get_user,
        mock_verify,
    ):
        mock_verify.return_value = self.id_info

        mock_get_user.side_effect = ValueError(
            "Account is disabled"
        )

        with self.assertRaisesMessage(
            ValueError,
            "Account is disabled",
        ):
            self.service("token")

    @patch.object(
        GoogleLoginService,
        "verify_google_token",
    )
    @patch.object(
        GoogleLoginService,
        "get_or_create_user",
    )
    @patch.object(
        GoogleLoginService,
        "create_user_session",
    )
    def test_create_session_failure(
        self,
        mock_session,
        mock_get_user,
        mock_verify,
    ):
        mock_verify.return_value = self.id_info
        mock_get_user.return_value = self.user

        mock_session.side_effect = RuntimeError(
            "Unexpected failure"
        )

        with self.assertRaises(
            RuntimeError
        ):
            self.service("token")

    @patch.object(
        GoogleLoginService,
        "verify_google_token",
    )
    @patch.object(
        GoogleLoginService,
        "get_or_create_user",
    )
    @patch.object(
        GoogleLoginService,
        "create_user_session",
    )
    def test_methods_are_called_in_order(
        self,
        mock_session,
        mock_get_user,
        mock_verify,
    ):
        mock_verify.return_value = self.id_info
        mock_get_user.return_value = self.user
        mock_session.return_value = {
            "access": "access",
            "refresh": "refresh",
        }

        self.service("token")

        self.assertTrue(
            mock_verify.called
        )

        self.assertTrue(
            mock_get_user.called
        )

        self.assertTrue(
            mock_session.called
        )