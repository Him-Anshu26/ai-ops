import factory
from factory.django import DjangoModelFactory
from accounts.models import EmailVerificationToken, PasswordResetToken
from .user_factory import UserFactory


class EmailVerificationTokenFactory(DjangoModelFactory):
    class Meta:
        model = EmailVerificationToken

    user = factory.SubFactory(UserFactory)
    token_hash = factory.Sequence(lambda n: f"email_token_hash_{n}")


class PasswordResetTokenFactory(DjangoModelFactory):
    class Meta:
        model = PasswordResetToken

    user = factory.SubFactory(UserFactory)
    token_hash = factory.Sequence(lambda n: f"password_reset_hash_{n}")
