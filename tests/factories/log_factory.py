import factory
from factory.django import DjangoModelFactory

from monitoring.models import Log
from tests.factories.service_factory import ServiceFactory


class LogFactory(DjangoModelFactory):
    """
    Factory for monitoring.Log.

    Generates realistic monitoring logs for API,
    service-layer and alert pipeline testing.
    """

    class Meta:
        model = Log

    service = factory.SubFactory(ServiceFactory)

    status = Log.LogStatus.SUCCESS

    message = factory.Faker("sentence")

    status_code = 200

    response_time_ms = factory.Faker(
        "random_int",
        min=20,
        max=900,
    )

    metadata = factory.LazyFunction(dict)