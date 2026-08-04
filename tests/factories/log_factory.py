import factory
from factory.django import DjangoModelFactory

from monitoring.models import Log, LogStatus
from tests.factories.service_factory import ServiceFactory


class LogFactory(DjangoModelFactory):
    class Meta:
        model = Log

    service = factory.SubFactory(ServiceFactory)

    message = factory.Faker("sentence")

    status = LogStatus.SUCCESS

    severity = "low"

    status_code = 200

    response_time_ms = 150

    metadata = factory.LazyFunction(dict)