import pytest

from alerts.models import AlertSeverity, AlertStatus, AlertType

from tests.factories import (
    AlertFactory,
    LogFactory,
    ServiceFactory,
    UserFactory,
)


@pytest.mark.django_db
class TestFactories:

    def test_user_factory(self):
        user = UserFactory()

        assert user.pk is not None
        assert user.email
        assert user.first_name
        assert user.check_password("Password@123")
        assert user.is_verified is True

    def test_service_factory(self):
        service = ServiceFactory()

        assert service.pk is not None
        assert service.created_by is not None
        assert service.name
        assert service.slug

    def test_log_factory(self):
        log = LogFactory()

        assert log.pk is not None
        assert log.service is not None
        assert log.message
        assert log.status_code == 200
        assert log.response_time_ms == 150

    def test_alert_factory(self):
        alert = AlertFactory()

        assert alert.pk is not None
        assert alert.service is not None
        assert alert.log is not None

        assert alert.message
        assert alert.alert_key

        assert alert.alert_type in (
            AlertType.ERROR,
            AlertType.DOWNTIME,
            AlertType.HIGH_LATENCY,
        )

        assert alert.severity in (
            AlertSeverity.LOW,
            AlertSeverity.MEDIUM,
            AlertSeverity.HIGH,
            AlertSeverity.CRITICAL,
        )

        assert alert.status == AlertStatus.OPEN