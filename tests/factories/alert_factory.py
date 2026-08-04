import factory
from factory.django import DjangoModelFactory

from alerts.models import Alert
from tests.factories.service_factory import ServiceFactory


class AlertFactory(DjangoModelFactory):
    """
    Factory for alerts.Alert.

    Creates valid alert objects suitable for
    notification, service-layer and integration tests.
    """

    class Meta:
        model = Alert

    service = factory.SubFactory(ServiceFactory)

    severity = Alert.AlertSeverity.WARNING

    title = factory.Faker("sentence", nb_words=4)

    description = factory.Faker("paragraph")

    status = Alert.AlertStatus.OPEN

    triggered_by = factory.Faker("word")

    threshold_value = 500

    observed_value = 620

    cooldown_until = None

    resolved_at = None