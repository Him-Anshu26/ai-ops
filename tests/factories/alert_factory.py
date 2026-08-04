import factory
from factory.django import DjangoModelFactory

from alerts.models import (
    Alert,
    AlertSeverity,
    AlertStatus,
    AlertType,
)

from tests.factories.log_factory import LogFactory
from tests.factories.service_factory import ServiceFactory


class AlertFactory(DjangoModelFactory):
    class Meta:
        model = Alert

    service = factory.SubFactory(ServiceFactory)

    log = factory.SubFactory(LogFactory)

    alert_type = AlertType.ERROR

    message = factory.Faker("sentence")

    alert_key = factory.Sequence(lambda n: f"error-service-{n}")

    severity = AlertSeverity.MEDIUM

    status = AlertStatus.OPEN

    trigger_count = 1