from drf_spectacular.utils import (
    extend_schema,
    OpenApiExample,
    OpenApiParameter,
)
from rest_framework import serializers

from accounts.serializers import (
    RegisterSerializer,
    LoginSerializer,
    EmailSerializer,
    RefreshTokenSerializer,
    PasswordResetConfirmSerializer,
    GoogleLoginSerializer,
)


# RESPONSE SERIALIZERS
class MessageResponseSerializer(serializers.Serializer):
    message = serializers.CharField()


class RefreshResponseSerializer(serializers.Serializer):
    access = serializers.CharField()


class TokenSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()


class LoginResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    tokens = TokenSerializer()


# REGISTER
register_schema = extend_schema(
    tags=["Authentication"],
    summary="Register user",
    description=(
        "Create a new user account and send "
        "an email verification link."
    ),
    request=RegisterSerializer,
    responses={
        201: MessageResponseSerializer,
    },
    examples=[
        OpenApiExample(
            "Register Request",
            value={
                "email": "john@example.com",
                "password": "StrongPassword123!",
                "first_name": "John",
            },
            request_only=True,
        ),
        OpenApiExample(
            "Register Success",
            value={
                "message": (
                    "User registered successfully. "
                    "Please verify your email."
                )
            },
            response_only=True,
            status_codes=["201"],
        ),
    ],
)


# LOGIN
login_schema = extend_schema(
    tags=["Authentication"],
    summary="Login user",
    description=(
        "Authenticate user credentials and "
        "issue access and refresh tokens."
    ),
    request=LoginSerializer,
    responses={
        200: LoginResponseSerializer,
    },
    examples=[
        OpenApiExample(
            "Login Request",
            value={
                "email": "john@example.com",
                "password": "StrongPassword123!",
            },
            request_only=True,
        ),
        OpenApiExample(
            "Login Success",
            value={
                "message": "Login successful.",
                "tokens": {
                    "access": "jwt_access_token",
                    "refresh": "jwt_refresh_token",
                },
            },
            response_only=True,
            status_codes=["200"],
        ),
    ],
)


# GOOGLE LOGIN
google_login_schema = extend_schema(
    tags=["Authentication"],
    summary="Google login",
    description=(
        "Authenticate user using a Google "
        "ID token and issue internal JWT tokens."
    ),
    request=GoogleLoginSerializer,
    responses={
        200: LoginResponseSerializer,
    },
    examples=[
        OpenApiExample(
            "Google Login Request",
            value={
                "id_token": "google_id_token",
            },
            request_only=True,
        ),
        OpenApiExample(
            "Google Login Success",
            value={
                "message": "Login successful.",
                "tokens": {
                    "access": "jwt_access_token",
                    "refresh": "jwt_refresh_token",
                },
            },
            response_only=True,
            status_codes=["200"],
        ),
    ],
)


# VERIFY EMAIL
verify_email_schema = extend_schema(
    tags=["Authentication"],
    summary="Verify email",
    description=(
        "Verify user email using the "
        "verification token."
    ),
    parameters=[
        OpenApiParameter(
            name="token",
            description="Email verification token.",
            required=True,
            type=str,
        )
    ],
    responses={
        200: MessageResponseSerializer,
    },
    examples=[
        OpenApiExample(
            "Verify Email Success",
            value={
                "message": "Email verified successfully."
            },
            response_only=True,
            status_codes=["200"],
        ),
    ],
)


# RESEND VERIFICATION
resend_verification_schema = extend_schema(
    tags=["Authentication"],
    summary="Resend verification email",
    description=(
        "Resend email verification link "
        "for unverified users."
    ),
    request=EmailSerializer,
    responses={
        200: MessageResponseSerializer,
    },
    examples=[
        OpenApiExample(
            "Resend Verification Request",
            value={
                "email": "john@example.com"
            },
            request_only=True,
        ),
        OpenApiExample(
            "Resend Verification Success",
            value={
                "message": "Verification email sent."
            },
            response_only=True,
            status_codes=["200"],
        ),
    ],
)


# REFRESH TOKEN
refresh_token_schema = extend_schema(
    tags=["Authentication"],
    summary="Refresh access token",
    description=(
        "Generate a new access token using "
        "a valid refresh token."
    ),
    request=RefreshTokenSerializer,
    responses={
        200: RefreshResponseSerializer,
    },
    examples=[
        OpenApiExample(
            "Refresh Request",
            value={
                "refresh": "jwt_refresh_token"
            },
            request_only=True,
        ),
        OpenApiExample(
            "Refresh Success",
            value={
                "access": "new_access_token"
            },
            response_only=True,
            status_codes=["200"],
        ),
    ],
)


# LOGOUT
logout_schema = extend_schema(
    tags=["Authentication"],
    summary="Logout user",
    description="Invalidate the current session.",
    responses={
        200: MessageResponseSerializer,
    },
    examples=[
        OpenApiExample(
            "Logout Success",
            value={
                "message": "Logged out successfully."
            },
            response_only=True,
            status_codes=["200"],
        ),
    ],
)


# PASSWORD RESET REQUEST
password_reset_request_schema = extend_schema(
    tags=["Authentication"],
    summary="Request password reset",
    description=(
        "Send password reset email "
        "to the user."
    ),
    request=EmailSerializer,
    responses={
        200: MessageResponseSerializer,
    },
    examples=[
        OpenApiExample(
            "Password Reset Request",
            value={
                "email": "john@example.com"
            },
            request_only=True,
        ),
        OpenApiExample(
            "Password Reset Email Sent",
            value={
                "message": "Password reset email sent."
            },
            response_only=True,
            status_codes=["200"],
        ),
    ],
)




# PASSWORD RESET CONFIRM
password_reset_confirm_schema = extend_schema(
    tags=["Authentication"],
    summary="Confirm password reset",
    description=(
        "Reset password using a valid "
        "password reset token."
    ),
    request=PasswordResetConfirmSerializer,
    responses={
        200: MessageResponseSerializer,
    },
    examples=[
        OpenApiExample(
            "Password Reset Confirm",
            value={
                "token": "reset_token",
                "new_password": "NewPassword123!",
            },
            request_only=True,
        ),
        OpenApiExample(
            "Password Reset Success",
            value={
                "message": "Password reset successful."
            },
            response_only=True,
            status_codes=["200"],
        ),
    ],
)