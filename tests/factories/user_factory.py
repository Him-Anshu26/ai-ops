import factory
from django.contrib.auth import get_user_model


User = get_user_model()


class UserFactory(factory.django.DjangoModelFactory):
    """
    Factory for the custom User model.

    Produces realistic users for:
    - authentication tests
    - service ownership
    - permissions
    - integration tests
    """

    class Meta:
        model = User
        django_get_or_create = ("email",)

    email = factory.Sequence(lambda n: f"user{n}@example.com")

    first_name = factory.Faker("first_name")

    is_active = True
    is_verified = True
    is_staff = False
    is_superuser = False

    auth_provider = "local"

    provider_id = None

    password = factory.PostGenerationMethodCall(
        "set_password",
        "TestPassword@123",
    )