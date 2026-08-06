import pytest

from accounts.tokens import (
    generate_access_token,
    generate_refresh_token,
    decode_token,
)
from tests.factories import UserFactory


@pytest.mark.django_db
class TestToken:
    @pytest.fixture(autouse=True)
    def setup_tokens(self):
        self.user = UserFactory(
            email="user@example.com",
            password="Password@123",
        )
        self.session_id = "session-123"

    def test_generate_access_token(self):
        token = generate_access_token(self.user, self.session_id)
        
        assert isinstance(token, str)
        payload = decode_token(token)
        assert payload is not None
        assert payload["user_id"] == self.user.id
        assert payload["session_id"] == self.session_id

    def test_generate_refresh_token(self):
        token = generate_refresh_token(self.user, self.session_id)
        
        assert isinstance(token, str)
        payload = decode_token(token)
        assert payload is not None
        assert payload["user_id"] == self.user.id
        assert payload["session_id"] == self.session_id

    def test_decode_access_token(self):
        token = generate_access_token(self.user, self.session_id)
        payload = decode_token(token)
        assert payload["user_id"] == self.user.id

    def test_decode_refresh_token(self):
        token = generate_refresh_token(self.user, self.session_id)
        payload = decode_token(token)
        assert payload["user_id"] == self.user.id

    def test_decode_invalid_token_returns_none(self):
        payload = decode_token("invalid.token.value")
        assert payload is None

    def test_access_token_contains_standard_claims(self):
        token = generate_access_token(self.user, self.session_id)
        payload = decode_token(token)
        
        assert "exp" in payload
        assert "token_type" in payload
        assert payload["token_type"] == "access"

    def test_refresh_token_contains_standard_claims(self):
        token = generate_refresh_token(self.user, self.session_id)
        payload = decode_token(token)
        
        assert "exp" in payload
        assert "token_type" in payload
        assert payload["token_type"] == "refresh"

    def test_access_and_refresh_tokens_are_different(self):
        access = generate_access_token(self.user, self.session_id)
        refresh = generate_refresh_token(self.user, self.session_id)
        
        assert access != refresh

    def test_session_id_is_embedded_in_both_tokens(self):
        access = generate_access_token(self.user, self.session_id)
        refresh = generate_refresh_token(self.user, self.session_id)
        
        assert decode_token(access)["session_id"] == self.session_id
        assert decode_token(refresh)["session_id"] == self.session_id

    def test_tokens_belong_to_correct_user(self):
        second_user = UserFactory(
            email="second@example.com",
            password="Password@123",
        )
        
        token = generate_access_token(second_user, "session-999")
        payload = decode_token(token)
        
        assert payload["user_id"] == second_user.id
        assert payload["user_id"] != self.user.id