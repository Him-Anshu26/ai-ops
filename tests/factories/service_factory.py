import factory
from factory.django import DjangoModelFactory

from monitoring.models import Service, Status
from tests.factories.user_factory import UserFactory


class ServiceFactory(DjangoModelFactory):
    class Meta:
        model = Service

    name = factory.Sequence(lambda n: f"Service {n}")
    description = factory.Faker("sentence")

    status = Status.ACTIVE

    created_by = factory.SubFactory(UserFactory)