from django.test import TestCase

from accounts.models import User


class UserManagerTests(TestCase):

    def test_create_user_successfully(self):
        user = User.objects.create_user(
            email="TEST@Example.COM",
            password="Password@123",
            first_name=" Himanshu ",
        )

        self.assertEqual(
            user.email,
            "test@example.com",
        )

        self.assertTrue(
            user.check_password("Password@123")
        )

        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.is_active)

    def test_create_user_without_email_raises_error(self):
        with self.assertRaisesMessage(
            ValueError,
            "Email is required",
        ):
            User.objects.create_user(
                email="",
                password="Password@123",
            )

    def test_create_user_password_is_hashed(self):
        user = User.objects.create_user(
            email="user@example.com",
            password="Password@123",
        )

        self.assertNotEqual(
            user.password,
            "Password@123",
        )

        self.assertTrue(
            user.check_password("Password@123")
        )

    def test_create_user_without_password(self):
        user = User.objects.create_user(
            email="user@example.com",
        )

        self.assertFalse(
            user.has_usable_password()
        )

    def test_create_superuser_successfully(self):
        admin = User.objects.create_superuser(
            email="admin@example.com",
            password="AdminPassword@123",
        )

        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)
        self.assertTrue(admin.is_active)

        self.assertTrue(
            admin.check_password(
                "AdminPassword@123"
            )
        )

    def test_create_superuser_requires_is_staff_true(self):
        with self.assertRaisesMessage(
            ValueError,
            "Superuser must have is_staff=True",
        ):
            User.objects.create_superuser(
                email="admin@example.com",
                password="AdminPassword@123",
                is_staff=False,
            )

    def test_create_superuser_requires_is_superuser_true(self):
        with self.assertRaisesMessage(
            ValueError,
            "Superuser must have is_superuser=True",
        ):
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

        self.assertEqual(
            user.email,
            email.lower(),
        )