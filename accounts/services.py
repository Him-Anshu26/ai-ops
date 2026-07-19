import logging

from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from accounts.models import (
    User,
    EmailVerificationToken,
    PasswordResetToken,
    UserSession,
)

from accounts.utils import (
    generate_token,
    hash_token,
    send_email,
    build_verification_link,
    build_reset_link,
)

from accounts.tokens import (
    generate_access_token,
    generate_refresh_token,
    decode_token,
)


from google.oauth2 import id_token
from google.auth.transport import requests
from allauth.socialaccount.models import SocialAccount
from django.conf import settings



logger = logging.getLogger(__name__)

# Token expiry configuration
EMAIL_VERIFICATION_EXPIRY_HOURS = 24
PASSWORD_RESET_EXPIRY_MINUTES = 30


# Create new user account
class CreateUserService:

    # Run all DB operations inside single transaction
    @transaction.atomic
    def __call__(
        self,
        email: str,
        password: str,
        first_name: str = "",
    ) -> User:

        # Normalize email
        # Prevent:
        # TEST@gmail.com
        # test@gmail.com
        # from becoming separate accounts
        email = email.lower().strip()

        # Prevent duplicate registration
        if User.objects.filter(email=email).exists():
            raise ValueError("User already exists")

        # Create user using Django's create_user()
        # Password automatically gets hashed
        user = User.objects.create_user(
            email=email,
            password=password,
            first_name=first_name.strip(),

            # User must verify email first
            is_verified=False,
        )

        logger.info(
            "User registered successfully",
            extra={"user_id": user.id},
        )

        # Return created user object
        return user


# Service instance
create_user = CreateUserService()


# Send email verification link
class SendVerificationEmailService:

    @transaction.atomic
    def __call__(self, user: User) -> None:

        # Idempotent protection
        # Already verified users should not receive new verification emails
        if user.is_verified:
            return

        # Delete previous verification tokens
        # Only latest token should remain valid
        EmailVerificationToken.objects.filter(user=user).delete()

        # Generate raw secure token
        # Example:
        # "asdkjhasd89as7d..."
        raw_token = generate_token()

        # Hash token before storing in DB
        # Never store raw tokens in database
        token_hash = hash_token(raw_token)

        # Store hashed token
        EmailVerificationToken.objects.create(
            user=user,
            token_hash=token_hash,
        )

        # Build frontend/backend verification URL
        verification_link = build_verification_link(raw_token)


        # this is the raw link with the unencoded token, useful for debugging
        # this token will be used when testing manual email verification in the postman
        # logger.info("RAW VERIFICATION LINK: %s", verification_link)
        # logger.info("Use This Token For Postman Verification: %s", raw_token)

        # Send email to user
        send_email(
            subject="Verify your email",

            # Email body
            message=(
                f"Hi {user.first_name or 'User'},\n\n"
                f"Please verify your email using the link below:\n\n"
                f"{verification_link}\n\n"
                f"This link expires in 24 hours.\n\n"
                f"If you did not create this account, ignore this email."
            ),

            # Email recipient list
            recipient_list=[user.email],
        )

        logger.info(
            "Verification email sent",
            extra={
                "user_id": user.id,
                "email": user.email,
            },
        )


# Service instance
send_verification_email = SendVerificationEmailService()


# Verify email token
class VerifyEmailService:

    @transaction.atomic
    def __call__(self, token: str) -> User:

        # Hash incoming raw token
        # Compare hash with DB hash
        token_hash = hash_token(token)

        try:

            # Find matching verification token
            # select_related("user")
            # avoids extra DB query when accessing verification.user
            verification = (
                EmailVerificationToken.objects
                .select_related("user")
                .get(token_hash=token_hash)
            )

        except EmailVerificationToken.DoesNotExist:

            # Token not found
            raise ValueError("Invalid token")

        # Calculate whether token expired
        #
        # verification.created_at + 24 hours
        is_expired = timezone.now() > (
            verification.created_at +
            timedelta(hours=EMAIL_VERIFICATION_EXPIRY_HOURS)
        )

        # Expired token flow
        if is_expired:

            # Delete expired token
            verification.delete()

            raise ValueError("Token expired")

        # Access related user
        user = verification.user

        # Idempotent behavior
        # If already verified, do not fail
        if not user.is_verified:

            # Mark email verified
            user.is_verified = True

            # Update only changed field
            user.save(update_fields=["is_verified"])

            logger.info(
                "User email verified successfully",
                extra={"user_id": user.id},
            )

        # Delete token after successful usage
        # Verification token should be one-time use
        verification.delete()

        # Return verified user
        return user


# Service instance
verify_email = VerifyEmailService()


# Resend verification email
class ResendVerificationEmailService:

    def __call__(self, email: str) -> None:

        # Normalize email
        email = email.lower().strip()

        try:

            # Find user account
            user = User.objects.get(email=email)

        except User.DoesNotExist:

            # Prevent email enumeration attack
            #
            # Do NOT reveal:
            # "email not found"
            return

        # Already verified users do not need verification email
        if user.is_verified:
            return

        # Send new verification email
        send_verification_email(user)

        logger.info(
            "Verification email resent",
            extra={
                "user_id": user.id,
                "email": user.email,
            },
        )


# Service instance
resend_verification_email = ResendVerificationEmailService()


# Login authenticated user
class LoginUserService:

    @transaction.atomic
    def __call__(self, email: str, password: str) -> dict:

        # Normalize email
        email = email.lower().strip()

        try:

            # Fetch user by email
            user = User.objects.get(email=email)

        except User.DoesNotExist:

            # Prevent credential enumeration
            raise ValueError("Invalid credentials")

        # Prevent login for disabled accounts
        if not user.is_active:
            raise ValueError("Account is disabled")

        # Validate password
        # check_password() compares hashed password securely
        if not user.check_password(password):
            raise ValueError("Invalid credentials")

        # Ensure email is verified
        if not user.is_verified:
            raise ValueError("Email is not verified")

        # Create unique session identifier
        #
        # One login = one session
        session_id = generate_token()

        # Generate refresh JWT token
        refresh_token = generate_refresh_token(
            user=user,
            session_id=session_id,
        )

        # Generate access JWT token
        access_token = generate_access_token(
            user=user,
            session_id=session_id,
        )

        # Store session in DB
        #
        # refresh token is HASHED before storage
        UserSession.objects.create(
            user=user,
            session_id=session_id,
            refresh_token_hash=hash_token(refresh_token),
            is_active=True,
        )

        logger.info(
            "User logged in",
            extra={
                "user_id": user.id,
                "session_id": session_id,
            },
        )

        # Return generated tokens
        return {
            "access": access_token,
            "refresh": refresh_token,
        }


# Service instance
login_user = LoginUserService()


# Generate new access token using refresh token
class RefreshAccessTokenService:

    def __call__(self, refresh_token: str) -> str:

        # Decode JWT token
        #
        # Checks:
        # - signature
        # - expiry
        # - token validity
        payload = decode_token(refresh_token)

        # Invalid or expired token
        if not payload:
            raise ValueError("Invalid token")

        # Extract JWT payload values
        user_id = payload.get("user_id")
        session_id = payload.get("session_id")

        # Validate payload fields
        if not user_id or not session_id:
            raise ValueError("Invalid token payload")

        try:

            # Find active DB session
            session = (
                UserSession.objects
                .select_related("user")
                .get(
                    user_id=user_id,
                    session_id=session_id,
                    is_active=True,
                )
            )

        except UserSession.DoesNotExist:

            # Session inactive or deleted
            raise ValueError("Session expired")

        # Prevent disabled users from refreshing tokens
        if not session.user.is_active:
            raise ValueError("Account disabled")

        # Hash incoming refresh token
        incoming_hash = hash_token(refresh_token)

        # Compare DB hash vs incoming token hash
        #
        # If mismatch:
        # token may be stolen/tampered
        if incoming_hash != session.refresh_token_hash:
            raise ValueError("Invalid token")

        # Generate fresh access token
        access_token = generate_access_token(
            user=session.user,
            session_id=session.session_id,
        )
        

        # Temporary debug prints for how backend processes refresh token
        # print("REFRESH TOKEN PAYLOAD:")
        # print(payload)
        # print("USER ID:")
        # print(user_id)
        # print("SESSION ID:")
        # print(session_id)
        # print("INCOMING HASH:")
        # print(incoming_hash)
        # print("DB HASH:")
        # print(session.refresh_token_hash)

        # Return new access token
        return access_token
    


# Service instance
refresh_access_token = RefreshAccessTokenService()


# Logout current session
class LogoutUserService:

    def __call__(self, session_id: str) -> None:

        # Soft logout approach
        #
        # Do NOT delete session
        # Just mark inactive
        #
        # Useful for:
        # - audit history
        # - security tracking
        # - device history
        updated = UserSession.objects.filter(
            session_id=session_id,
            is_active=True,
        ).update(is_active=False)

        if updated:
            logger.info(
                "User logged out",
                extra={
                    "session_id": session_id,
                },
            )


# Service instance
logout_user = LogoutUserService()


# Request password reset email
class RequestPasswordResetService:

    @transaction.atomic
    def __call__(self, email: str) -> None:

        # Normalize email
        email = email.lower().strip()

        try:

            # Find user account
            user = User.objects.get(email=email)

        except User.DoesNotExist:

            # Prevent email enumeration attack
            return

        # Delete previous reset tokens
        # Only latest token remains valid
        PasswordResetToken.objects.filter(user=user).delete()

        # Generate raw reset token
        raw_token = generate_token()

        # Hash token before DB storage
        token_hash = hash_token(raw_token)

        # Store hashed token
        PasswordResetToken.objects.create(
            user=user,
            token_hash=token_hash,
        )

        # Build password reset URL
        reset_link = build_reset_link(raw_token)

        # this is the raw link with the unencoded token, useful for debugging
        # this token will be used when testing manual password reset in the postman
        # logger.info("RAW RESET LINK: %s", reset_link)
        # logger.info("Use This Token For Postman Reset: %s", raw_token)

        # Send reset email
        send_email(
            subject="Reset your password",

            # Email body
            message=(
                f"Hi {user.first_name or 'User'},\n\n"
                f"Use the link below to reset your password:\n\n"
                f"{reset_link}\n\n"
                f"This link expires in 30 minutes.\n\n"
                f"If you did not request this, ignore this email."
            ),

            recipient_list=[user.email],
        )

        logger.info(
            "Password reset email sent",
            extra={
                "user_id": user.id,
                "email": user.email,
            },
        )


# Service instance
request_password_reset = RequestPasswordResetService()


# Reset user password
class ResetPasswordService:

    @transaction.atomic
    def __call__(self, token: str, new_password: str) -> None:

        # Hash incoming raw token
        token_hash = hash_token(token)

        try:

            # Find reset token in DB
            reset_token = (
                PasswordResetToken.objects
                .select_related("user")
                .get(token_hash=token_hash)
            )

        except PasswordResetToken.DoesNotExist:

            # Invalid token
            raise ValueError("Invalid token")

        # Check token expiry
        is_expired = timezone.now() > (
            reset_token.created_at +
            timedelta(minutes=PASSWORD_RESET_EXPIRY_MINUTES)
        )

        # Expired token flow
        if is_expired:

            # Delete expired token
            reset_token.delete()

            raise ValueError("Token expired")

        # Get related user
        user = reset_token.user

        # Securely hash and update password
        user.set_password(new_password)

        # Save only changed field
        user.save(update_fields=["password"])

        # Invalidate ALL user sessions
        #
        # User gets logged out everywhere
        UserSession.objects.filter(
            user=user,
            is_active=True,
        ).update(is_active=False)

        # Delete used reset token
        # One-time usage only
        reset_token.delete()

        logger.info(
            "User password reset successfully",
            extra={
                "user_id": user.id,
            },
        )


# Service instance
reset_password = ResetPasswordService()


# Cleanup expired verification tokens
class CleanupExpiredVerificationTokensService:

    def __call__(self) -> int:

        # Calculate expiry cutoff datetime
        expiry_time = timezone.now() - timedelta(
            hours=EMAIL_VERIFICATION_EXPIRY_HOURS
        )

        # Delete old expired tokens
        deleted_count, _ = EmailVerificationToken.objects.filter(
            created_at__lt=expiry_time
        ).delete()

        logger.info(
            "Expired verification tokens cleaned",
            extra={
                "deleted_count": deleted_count,
            },
        )

        # Return number of deleted rows
        return deleted_count


# Service instance
cleanup_expired_verification_tokens = (
    CleanupExpiredVerificationTokensService()
)


# Cleanup expired password reset tokens
class CleanupExpiredPasswordResetTokensService:

    def __call__(self) -> int:

        # Calculate expiry cutoff datetime
        expiry_time = timezone.now() - timedelta(
            minutes=PASSWORD_RESET_EXPIRY_MINUTES
        )

        # Delete expired reset tokens
        deleted_count, _ = PasswordResetToken.objects.filter(
            created_at__lt=expiry_time
        ).delete()

        logger.info(
            "Expired password reset tokens cleaned",
            extra={
                "deleted_count": deleted_count,
            },
        )

        # Return deleted rows count
        return deleted_count


# Service instance
cleanup_expired_password_reset_tokens = (
    CleanupExpiredPasswordResetTokensService()
)


# Cleanup old inactive sessions
class CleanupInactiveSessionsService:
    """
    Delete inactive sessions older than 90 days.
    Keeps audit history while preventing DB bloat.
    """

    def __call__(self) -> int:

        # Sessions older than this date will be removed
        retention_date = timezone.now() - timedelta(days=90)

        # Delete inactive old sessions
        deleted_count, _ = UserSession.objects.filter(
            is_active=False,
            created_at__lt=retention_date,
        ).delete()

        logger.info(
            "Inactive sessions cleaned",
            extra={
                "deleted_count": deleted_count,
            },
        )

        # Return deleted rows count
        return deleted_count


# Service instance
cleanup_inactive_sessions = CleanupInactiveSessionsService()




class GoogleLoginService :
    
    # Recieve Google ID token from client & verify it with Google
    def verify_google_token(self, token: str) -> dict:
        try:
            id_info = id_token.verify_oauth2_token(
                token,
                requests.Request(),
                settings.GOOGLE_CLIENT_ID
            )
        except ValueError:
            # Invalid token
            raise ValueError("Invalid Google token")
        
        # extract important identity fields
        email = id_info.get("email")
        google_sub = id_info.get("sub")
        email_verified = id_info.get("email_verified")

        # mandatory validation
        if not email:
            raise ValueError("Email not provided by Google")

        if not google_sub:
            raise ValueError("Invalid Google account")

        # Google account email must be verified
        if not email_verified:
            raise ValueError("Google email is not verified")
        
        if id_info.get("iss") not in [
            "accounts.google.com",
            "https://accounts.google.com",
        ]:
            raise ValueError("Invalid Google issuer")

        return id_info
        
    
    # Find User Or Create New Local User
    def get_or_create_user(self, id_info: dict) -> User:

        email = (
            id_info.get("email", "")
            .lower()
            .strip()
        )

        first_name = id_info.get("given_name", "").strip()

        google_sub = (
            id_info.get("sub", "")
            .strip()
        )

        # check existing local user
        user = User.objects.filter(
            email=email
        ).first()

        # existing user login flow
        if user:

            # blocked/inactive users cannot login
            if not user.is_active:
                raise ValueError("Account is disabled")

            # update provider info if missing
            if not user.auth_provider:
                user.auth_provider = "google"

            if not user.provider_id:
                user.provider_id = google_sub

            # Google accounts are verified identities
            if not user.is_verified:
                user.is_verified = True

            user.save(
                update_fields=[
                    "auth_provider",
                    "provider_id",
                    "is_verified",
                ]
            )

            # ensure social account exists
            SocialAccount.objects.get_or_create(
                user=user,
                provider="google",
                uid=google_sub,
            )

            return user

        # create brand new OAuth user
        user = User.objects.create(
            email=email,
            first_name=first_name,
            is_verified=True,
            auth_provider="google",
            provider_id=google_sub,
        )

        # store provider mapping
        SocialAccount.objects.create(
            user=user,
            provider="google",
            uid=google_sub,
        )

        return user
    

    # Create User Session & generate JWT tokens for authenticated user
    def create_user_session(self,user: User,) -> dict:

        # generate unique session id
        session_id = generate_token()

        # generate refresh token
        refresh_token = generate_refresh_token(
            user=user,
            session_id=session_id,
        )

        # generate access token
        access_token = generate_access_token(
            user=user,
            session_id=session_id,
        )

        # store hashed refresh token in DB
        UserSession.objects.create(
            user=user,
            session_id=session_id,
            refresh_token_hash=hash_token(
                refresh_token
            ),
            is_active=True,
        )

        return {
            "access": access_token,
            "refresh": refresh_token,
        }

    # complete Google OAuth login flow
    @transaction.atomic
    def __call__(self,token: str,) -> dict:

        # step 1:
        # validate Google token
        id_info = self.verify_google_token(
            token
        )

        # step 2:
        # find or create local user
        user = self.get_or_create_user(
            id_info
        )

        # step 3:
        # create internal session
        # and issue JWTs
        tokens = self.create_user_session(
            user
        )

        logger.info(
            "Google login successful",
            extra={
                "user_id": user.id,
                "email": user.email,
            },
        )

        return tokens


google_login = GoogleLoginService()
    
        