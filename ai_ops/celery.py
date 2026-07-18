import os

from celery import Celery


# Set the default Django settings module for Celery.
os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "ai_ops.settings.dev",
)


# Create the Celery application.
app = Celery("ai_ops")


# Load Celery configuration from Django settings.
#
# Only settings prefixed with "CELERY_" will be loaded.
#
# Example:
# CELERY_BROKER_URL
# CELERY_RESULT_BACKEND
# CELERY_TIMEZONE
app.config_from_object(
    "django.conf:settings",
    namespace="CELERY",
)


# Automatically discover tasks.py from all installed apps.
#
# Example:
# accounts/tasks.py
# alerts/tasks.py
# monitoring/tasks.py
app.autodiscover_tasks()