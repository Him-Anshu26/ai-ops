from .base import *

import environ

env = environ.Env()

environ.Env.read_env(BASE_DIR / ".env.prod")

DEBUG = False

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")


REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = [
    "rest_framework.renderers.JSONRenderer",
]

REST_FRAMEWORK["DEFAULT_PERMISSION_CLASSES"] = [
    "rest_framework.permissions.IsAuthenticated",
]


EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"





SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
