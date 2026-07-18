from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit

# Register → prevent signup spam
register_limit = method_decorator(
    ratelimit(
        key="ip",
        rate="5/m",
        method="POST",
        block=True,
    )
)

# Login → prevent brute-force attacks
login_limit = method_decorator(
    ratelimit(
        key="ip",
        rate="10/m",
        method="POST",
        block=True,
    )
)

# Email verification → prevent abuse of email verification endpoint
email_limit = method_decorator(
    ratelimit(
        key="ip",
        rate="5/m",
        method="POST",
        block=True,
    )
)

# Password reset → prevent abuse of password reset endpoint
password_reset_limit = method_decorator(
    ratelimit(
        key="ip",
        rate="5/m",
        method="POST",
        block=True,
    )
)


# Refresh token → prevent abuse of refresh token endpoint
refresh_token_limit = method_decorator(
    ratelimit(
        key="ip",
        rate="10/m",
        method="POST",
        block=True,
    )
)


# Google login → prevent abuse of Google login endpoint
google_login_limit = method_decorator(
    ratelimit(
        key="ip",
        rate="10/m",
        method="POST",
        block=True,
    )
)