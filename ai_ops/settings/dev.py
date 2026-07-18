from .base import *

import environ

env = environ.Env()

environ.Env.read_env(BASE_DIR / ".env.dev")

DEBUG = True


ALLOWED_HOSTS = [
    "localhost",
    "127.0.0.1",
]


REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES'] = [
    'rest_framework.renderers.JSONRenderer',
    'rest_framework.renderers.BrowsableAPIRenderer',
]

REST_FRAMEWORK["DEFAULT_PERMISSION_CLASSES"] = [
    "rest_framework.permissions.AllowAny",
]

