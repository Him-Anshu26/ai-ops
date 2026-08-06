import pytest
from accounts.models import User


@pytest.mark.django_db
class TestUserManager:
    def test_create_user_successfully(self):
        user = User.objects.create_user(
            email="TEST@Example.COM",
            password="Password@123",
            first_name=" Himanshu ",
        )

        assert user.email == "test@example.com"
        assert user.check_password("Password@123")
        assert not user.is_staff
        assert not user.is_superuser
        assert user.is_active

    def test_create_user_without_email_raises_error(self):
        with pytest.raises(ValueError, match="Email is required"):
            User.objects.create_user(
                email="",
                password="Password@123",
            )

    def test_create_user_password_is_hashed(self):
        user = User.objects.create_user(
            email="user@example.com",
            password="Password@123",
        )

        assert user.password != "Password@123"
        assert user.check_password("Password@123")

    def test_create_user_without_password(self):
        user = User.objects.create_user(
            email="user@example.com",
        )

        assert not user.has_usable_password()

    def test_create_superuser_successfully(self):
        admin = User.objects.create_superuser(
            email="admin@example.com",
            password="AdminPassword@123",
        )

        assert admin.is_staff
        assert admin.is_superuser
        assert admin.is_active
        assert admin.check_password("AdminPassword@123")

    def test_create_superuser_requires_is_staff_true(self):
        with pytest.raises(ValueError, match="Superuser must have is_staff=True"):
            User.objects.create_superuser(
                email="admin@example.com",
                password="AdminPassword@123",
                is_staff=False,
            )

    def test_create_superuser_requires_is_superuser_true(self):
        with pytest.raises(ValueError, match="Superuser must have is_superuser=True"):
            User.objects.create_superuser(
                email="admin@example.com",
                password="AdminPassword@123",
                is_superuser=False,
            )

    def test_email_is_normalized(self):
        email = "USER@Example.COM"

        user = User.objects.create_user(
            email=email,
            password="Password@123",
        )

        assert user.email == email.lower()