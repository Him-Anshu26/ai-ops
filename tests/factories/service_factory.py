import factory

from monitoring.models import Service, Status

from tests.factories.user_factory import UserFactory


class ServiceFactory(factory.django.DjangoModelFactory):
    """
    Factory for monitored services.

    Automatically creates a valid owner (created_by)
    and generates unique names so model constraints
    are never violated.
    """

    class Meta:
        model = Service

    created_by = factory.SubFactory(UserFactory)

    name = factory.Sequence(lambda n: f"Service {n}")

    description = factory.Faker(
        "sentence",
        nb_words=10,
    )

    status = Status.ACTIVE

    is_deleted = False

    last_checked_at = None

    # Leave blank intentionally.
    # Model.save() generates a unique slug automatically.
    slug = ""