import pytest

from django.urls import reverse

from monitoring.models import LogStatus
from tests.factories import LogFactory, ServiceFactory


@pytest.fixture
def log_list_url():
    return reverse("logs-list")


def make_log(service, **kwargs):
    """Helper to create a log with sensible defaults for view tests."""
    created_at = kwargs.pop("created_at", None)

    defaults = {
        "service": service,
        "status": LogStatus.SUCCESS,
        "status_code": 200,
        "response_time_ms": 100,
        "message": "Test log",
    }
    defaults.update(kwargs)
    log = LogFactory(**defaults)

    if created_at:
        from monitoring.models import Log

        Log.objects.filter(pk=log.pk).update(created_at=created_at)
        log.refresh_from_db()

    return log

