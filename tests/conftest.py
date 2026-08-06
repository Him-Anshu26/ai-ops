import pytest

from django.test import Client
from rest_framework.test import APIClient

from tests.factories import (
    UserFactory,
    ServiceFactory,
    LogFactory,
    AlertFactory,
)


@pytest.fixture
def user(db):
    return UserFactory()


@pytest.fixture
def another_user(db):
    return UserFactory()


@pytest.fixture
def service(db):
    return ServiceFactory()


@pytest.fixture
def log(db):
    return LogFactory()


@pytest.fixture
def alert(db):
    return AlertFactory()


@pytest.fixture
def client():
    return Client()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def authenticated_user(user):
    return user


@pytest.fixture
def authenticated_api_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client