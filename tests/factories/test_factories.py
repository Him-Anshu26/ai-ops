import pytest

from tests.factories import (
    UserFactory,
    ServiceFactory,
    LogFactory,
    AlertFactory,
)


pytestmark = pytest.mark.django_db


class TestFactories:
    """
    Smoke tests for all Factory Boy factories.

    Ensures every factory builds a valid database object
    without violating model constraints.
    """

    def test_user_factory(self):
        user = UserFactory()

        assert user.pk is not None
        assert user.email
        assert user.first_name

    def test_service_factory(self):
        service = ServiceFactory()

        assert service.pk is not None
        assert service.name
        assert service.slug
        assert service.created_by is not None

    def test_log_factory(self):
        log = LogFactory()

        assert log.pk is not None
        assert log.service is not None
        assert log.message
        assert log.status_code == 200

    def test_alert_factory(self):
        alert = AlertFactory()

        assert alert.pk is not None
        assert alert.service is not None
        assert alert.title
        assert alert.description