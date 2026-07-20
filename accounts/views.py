from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
# from rest_framework.permissions import AllowAny

from django.conf import settings
from django.shortcuts import render


from accounts.serializers import (
    GoogleLoginSerializer,
    RegisterSerializer,
    LoginSerializer,
    EmailSerializer,
    PasswordResetConfirmSerializer,
    RefreshTokenSerializer,
)

from accounts.services import (
    create_user,
    send_verification_email,
    login_user,
    verify_email,
    resend_verification_email,
    refresh_access_token,
    logout_user,
    request_password_reset,
    reset_password,
    google_login,
)

from accounts.throttling import (
    register_limit,
    login_limit,
    email_limit,
    password_reset_limit,
    refresh_token_limit,
    google_login_limit,
)



from accounts.schemas.auth_schema import (
    register_schema,
    login_schema,
    google_login_schema,
    verify_email_schema,
    resend_verification_schema,
    refresh_token_schema,
    logout_schema,
    password_reset_request_schema,
    password_reset_confirm_schema,
)



# REGISTER API
class RegisterAPIView(APIView):
    
    @register_schema
    # Apply rate limiting on registration requests
    @register_limit
    def post(self, request):

        # request.data contains incoming JSON body
        # Example:
        # {
        #     "email": "test@gmail.com",
        #     "password": "Password@123",
        #     "first_name": "John"
        # }

        # Serializer receives raw request data
        serializer = RegisterSerializer(data=request.data)

        # Validate incoming data
        # Runs:
        # - validate_email()
        # - validate_password()
        # - validate_first_name()
        #
        # If validation fails:
        # DRF automatically returns 400 response
        serializer.is_valid(raise_exception=True)

        # serializer.validated_data contains cleaned/validated data
        #
        # Example:
        # {
        #     "email": "test@gmail.com",
        #     "password": "Password@123",
        #     "first_name": "John"
        # }

        # Create user using service layer
        # Business logic should stay inside services.py
        user = create_user(**serializer.validated_data)

        # Generate verification token
        # Store hashed token in DB
        # Send verification email to user
        send_verification_email(user)

        # Return API response
        return Response(
            {
                "message": "User registered successfully. Please verify your email."
            },
            status=status.HTTP_201_CREATED,
        )



# LOGIN API
class LoginAPIView(APIView):

    @login_schema
    # Apply rate limiting to prevent brute-force login attacks
    @login_limit
    def post(self, request):

        # Receive login request data
        serializer = LoginSerializer(data=request.data)

        # Validate email/password format
        serializer.is_valid(raise_exception=True)

        try:
            # Authenticate user
            # Check:
            # - email exists
            # - password correct
            # - email verified
            #
            # Then:
            # - create session
            # - generate JWT tokens
            # - store hashed refresh token in DB
            tokens = login_user(
                email=serializer.validated_data["email"],
                password=serializer.validated_data["password"],
            )

        except ValueError as e:

            # Invalid credentials or unverified email
            return Response(
                {
                    "error": str(e)
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Successful login response
        return Response(
            {
                "message": "Login successful.",

                # Example:
                # {
                #   "access": "...",
                #   "refresh": "..."
                # }
                "tokens": tokens,
            },
            status=status.HTTP_200_OK,
        )



# VERIFY EMAIL API
class VerifyEmailAPIView(APIView):

    permission_classes = [IsAuthenticated] 

    @verify_email_schema
    def get(self, request):

        # Extract token from URL query params
        #
        # Example:
        # /verify-email/?token=abc123
        #
        # token = "abc123"
        token = request.query_params.get("token")

        # Validate token existence
        if not token:
            return Response(
                {
                    "error": "Token is required."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Service layer handles:
            # - token hashing
            # - DB lookup
            # - expiry check
            # - mark user verified
            # - delete used token
            verify_email(token)

        except ValueError as e:

            # Invalid or expired token
            return Response(
                {
                    "error": str(e)
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Successful verification response
        return Response(
            {
                "message": "Email verified successfully."
            },
            status=status.HTTP_200_OK,
        )



# RESEND VERIFICATION EMAIL API
class ResendVerificationEmailAPIView(APIView):

    @resend_verification_schema
    # Apply rate limiting
    @email_limit
    def post(self, request):

        # Receive email from request body
        serializer = EmailSerializer(data=request.data)

        # Validate email format
        serializer.is_valid(raise_exception=True)

        # Service handles:
        # - user lookup
        # - prevent email enumeration
        # - skip already verified users
        # - generate new token
        # - send email
        resend_verification_email(
            email=serializer.validated_data["email"]
        )

        # Generic response prevents attackers
        # from checking whether email exists
        return Response(
            {
                "message": "If the account exists and is unverified, a verification email has been sent."
            },
            status=status.HTTP_200_OK,
        )



# REFRESH ACCESS TOKEN
class RefreshTokenAPIView(APIView):
    
    @refresh_token_schema
    # Apply rate limiting to prevent abuse of refresh endpoint
    @refresh_token_limit
    def post(self, request):

        # Receive refresh token from request body
        serializer = RefreshTokenSerializer(data=request.data)

        # Validate refresh token existence
        serializer.is_valid(raise_exception=True)

        try:
            # Service layer handles:
            # - JWT decoding
            # - expiry validation
            # - session lookup
            # - session active check
            # - refresh token hash comparison
            # - generate new access token
            access_token = refresh_access_token(
                serializer.validated_data["refresh"]
            )

        except ValueError as e:

            # Invalid/expired session or token
            return Response(
                {
                    "error": str(e)
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Return new access token
        return Response(
            {
                "access": access_token
            },
            status=status.HTTP_200_OK,
        )



# LOGOUT API
class LogoutAPIView(APIView):

    # Only authenticated users can access this API
    permission_classes = [IsAuthenticated]

    @logout_schema
    def post(self, request):

        # request.auth contains decoded JWT payload
        #
        # Example:
        # {
        #     "user_id": 1,
        #     "session_id": "abc123"
        # }
        session_id = request.auth.get("session_id")

        # Ensure session exists inside token payload
        if not session_id:
            return Response(
                {
                    "error": "Invalid session."
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Mark session inactive in DB
        logout_user(session_id)

        # User is now logged out
        return Response(
            {
                "message": "Logged out successfully."
            },
            status=status.HTTP_200_OK,
        )



# PASSWORD RESET REQUEST
class PasswordResetRequestAPIView(APIView):

    @password_reset_request_schema
    # Apply rate limiting
    @password_reset_limit
    def post(self, request):

        # Receive email from request body
        serializer = EmailSerializer(data=request.data)

        # Validate email format
        serializer.is_valid(raise_exception=True)

        # Service layer handles:
        # - user lookup
        # - prevent email enumeration
        # - generate reset token
        # - store hashed token
        # - send reset email
        request_password_reset(
            serializer.validated_data["email"]
        )

        # Generic response for security
        return Response(
            {
                "message": "If the account exists, a password reset email has been sent."
            },
            status=status.HTTP_200_OK,
        )



# PASSWORD RESET CONFIRM
class PasswordResetConfirmAPIView(APIView):

    @password_reset_confirm_schema
    def post(self, request):

        # Receive:
        # - reset token
        # - new password
        serializer = PasswordResetConfirmSerializer(
            data=request.data
        )

        # Validate:
        # - token exists
        # - password strength
        serializer.is_valid(raise_exception=True)

        try:
            # Service layer handles:
            # - token hashing
            # - token lookup
            # - expiry check
            # - password update
            # - invalidate all sessions
            # - delete used token
            reset_password(
                token=serializer.validated_data["token"],
                new_password=serializer.validated_data["new_password"],
            )

        except ValueError as e:

            # Invalid or expired token
            return Response(
                {
                    "error": str(e)
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Successful password reset response
        return Response(
            {
                "message": "Password reset successful."
            },
            status=status.HTTP_200_OK,
        )



# GOOGLE LOGIN API
class GoogleLoginAPIView(APIView):
    
    @google_login_schema
    # Apply rate limiting to prevent abuse of Google login endpoint
    @google_login_limit
    def post(self, request):

        # Receive Google ID token from frontend
        serializer = GoogleLoginSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        try:
            # - verify Google ID token
            # - extract Google identity
            # - find existing local user
            # - create local user if not found
            # - create internal session
            # - generate internal JWT tokens
            # - store hashed refresh token in DB
            tokens = google_login(
                token=serializer.validated_data["id_token"],
            )

        except ValueError as e:

            # Invalid or expired token
            return Response(
                {
                    "error": str(e)
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Successful login response
        return Response(
            {
                "message": "Login successful.",

                # Example:
                # {
                #   "access": "...",
                #   "refresh": "..."
                # }
                "tokens": tokens,
            },
            status=status.HTTP_200_OK,
        )



class GoogleLoginTestAPIView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        return render(
            request,
            "google_login_test/google_test.html",
            {
                "GOOGLE_CLIENT_ID": settings.GOOGLE_CLIENT_ID,
            },
        )
        