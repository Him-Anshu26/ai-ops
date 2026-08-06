import factory
from factory.django import DjangoModelFactory
from accounts.models import UserSession
from .user_factory import UserFactory


class UserSessionFactory(DjangoModelFactory):
    class Meta:
        model = UserSession

    user = factory.SubFactory(UserFactory)
    session_id = factory.Sequence(lambda n: f"session_id_{n}")
    refresh_token_hash = factory.Sequence(lambda n: f"refresh_hash_{n}")
    is_active = True
