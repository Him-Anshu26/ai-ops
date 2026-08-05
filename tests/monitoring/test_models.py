from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

from monitoring.models import (
    Log,
    LogStatus,
    Service,
    Status,
)

User = get_user_model()


class ServiceModelTests(TestCase):
    """
    Unit tests for Service model.

    Covers:
    - Object creation
    - Default values
    - __str__
    - Slug generation
    - Slug uniqueness
    - Constraints
    - Soft delete behaviour
    - Ordering
    """

    def setUp(self):
        self.user = User.objects.create_user(
            email="owner@example.com",
            password="Password@123",
        )

        self.other_user = User.objects.create_user(
            email="second@example.com",
            password="Password@123",
        )

    # ---------------------------------------------------------
    # Object Creation
    # ---------------------------------------------------------

    def test_create_service_successfully(self):
        service = Service.objects.create(
            name="Authentication API",
            description="Handles authentication",
            created_by=self.user,
        )

        self.assertEqual(service.name, "Authentication API")
        self.assertEqual(service.description, "Handles authentication")
        self.assertEqual(service.status, Status.ACTIVE)
        self.assertFalse(service.is_deleted)
        self.assertEqual(service.created_by, self.user)

    def test_default_values(self):
        service = Service.objects.create(
            name="Payments",
            created_by=self.user,
        )

        self.assertEqual(service.status, Status.ACTIVE)
        self.assertFalse(service.is_deleted)
        self.assertIsNone(service.last_checked_at)

    # ---------------------------------------------------------
    # String Representation
    # ---------------------------------------------------------

    def test_string_representation(self):
        service = Service.objects.create(
            name="Monitoring",
            created_by=self.user,
        )

        self.assertEqual(
            str(service),
            f"Monitoring ({self.user.email})",
        )

    # ---------------------------------------------------------
    # Slug Generation
    # ---------------------------------------------------------

    def test_slug_is_generated_automatically(self):
        service = Service.objects.create(
            name="My Awesome Service",
            created_by=self.user,
        )

        self.assertEqual(
            service.slug,
            "my-awesome-service",
        )

    def test_slug_is_not_modified_when_already_provided(self):
        service = Service.objects.create(
            name="Random Service",
            slug="custom-slug",
            created_by=self.user,
        )

        self.assertEqual(service.slug, "custom-slug")

    def test_empty_name_generates_default_slug(self):
        service = Service.objects.create(
            name="!!!",
            created_by=self.user,
        )

        self.assertEqual(service.slug, "service")

    # Slug Collision
    def test_slug_can_be_reused_after_soft_delete(self):
        first = Service.objects.create(
            name="API Server",
            created_by=self.user,
        )

        first.is_deleted = True
        first.save(update_fields=["is_deleted"])

        second = Service.objects.create(
            name="API Server",
            created_by=self.user,
        )

        self.assertEqual(first.slug, "api-server")
        self.assertEqual(second.slug, "api-server")

    def test_same_slug_allowed_for_different_users(self):
        first = Service.objects.create(
            name="Backend",
            created_by=self.user,
        )

        second = Service.objects.create(
            name="Backend",
            created_by=self.other_user,
        )

        self.assertEqual(first.slug, "backend")
        self.assertEqual(second.slug, "backend")

    # ---------------------------------------------------------
    # Constraints
    # ---------------------------------------------------------

    def test_same_name_same_user_not_allowed(self):
        Service.objects.create(
            name="Orders",
            created_by=self.user,
        )

        with self.assertRaisesMessage(
            ValueError,
            "Could not generate unique slug",
        ):
            Service.objects.create(
                name="Orders",
                created_by=self.user,
            )

    def test_same_name_different_users_allowed(self):
        Service.objects.create(
            name="Orders",
            created_by=self.user,
        )

        service = Service.objects.create(
            name="Orders",
            created_by=self.other_user,
        )

        self.assertEqual(service.name, "Orders")

    def test_same_slug_same_user_not_allowed(self):
        Service.objects.create(
            name="Users",
            slug="users-api",
            created_by=self.user,
        )

        with self.assertRaises(IntegrityError):
            Service.objects.create(
                name="Something Else",
                slug="users-api",
                created_by=self.user,
            )

    def test_same_slug_different_users_allowed(self):
        Service.objects.create(
            name="Users",
            slug="users-api",
            created_by=self.user,
        )

        service = Service.objects.create(
            name="Users 2",
            slug="users-api",
            created_by=self.other_user,
        )

        self.assertEqual(service.slug, "users-api")

    # ---------------------------------------------------------
    # Soft Delete Behaviour
    # ---------------------------------------------------------

    def test_soft_deleted_name_can_be_reused(self):
        service = Service.objects.create(
            name="Gateway",
            created_by=self.user,
        )

        service.is_deleted = True
        service.save(update_fields=["is_deleted"])

        reused = Service.objects.create(
            name="Gateway",
            created_by=self.user,
        )

        self.assertEqual(reused.name, "Gateway")
        self.assertFalse(reused.is_deleted)

    def test_soft_deleted_slug_can_be_reused(self):
        service = Service.objects.create(
            name="Email",
            slug="email-service",
            created_by=self.user,
        )

        service.is_deleted = True
        service.save(update_fields=["is_deleted"])

        reused = Service.objects.create(
            name="Another Email",
            slug="email-service",
            created_by=self.user,
        )

        self.assertEqual(
            reused.slug,
            "email-service",
        )

    # ---------------------------------------------------------
    # Ordering
    # ---------------------------------------------------------

    def test_ordering_newest_first(self):
        old = Service.objects.create(
            name="Old",
            created_by=self.user,
        )

        new = Service.objects.create(
            name="New",
            created_by=self.user,
        )

        services = list(Service.objects.all())

        self.assertEqual(services[0], new)
        self.assertEqual(services[1], old)

    # ---------------------------------------------------------
    # Timestamp Fields
    # ---------------------------------------------------------

    def test_created_at_is_set(self):
        service = Service.objects.create(
            name="Logging",
            created_by=self.user,
        )

        self.assertIsNotNone(service.created_at)

    def test_updated_at_changes_after_save(self):
        service = Service.objects.create(
            name="Metrics",
            created_by=self.user,
        )

        original = service.updated_at

        service.description = "Updated description"
        service.save()

        service.refresh_from_db()

        self.assertGreaterEqual(
            service.updated_at,
            original,
        )

    # ---------------------------------------------------------
    # Status Choices
    # ---------------------------------------------------------

    def test_all_status_choices_work(self):
        for status in Status.values:
            service = Service.objects.create(
                name=f"Service-{status}",
                created_by=self.user,
                status=status,
            )

            self.assertEqual(service.status, status)

    # ---------------------------------------------------------
    # Last Checked
    # ---------------------------------------------------------

    def test_last_checked_at_can_be_updated(self):
        service = Service.objects.create(
            name="Health API",
            created_by=self.user,
        )

        now = timezone.now()

        service.last_checked_at = now
        service.save(update_fields=["last_checked_at"])

        service.refresh_from_db()

        self.assertIsNotNone(service.last_checked_at)
        self.assertEqual(
            service.last_checked_at.replace(microsecond=0),
            now.replace(microsecond=0),
        )


class LogModelTests(TestCase):
    """
    Unit tests for Log model.

    Covers:
    - Object creation
    - Defaults
    - __str__
    - Validators
    - Metadata
    - Ordering
    - Cascade delete
    """

    def setUp(self):
        self.user = User.objects.create_user(
            email="owner@example.com",
            password="Password@123",
        )

        self.service = Service.objects.create(
            name="Monitoring API",
            created_by=self.user,
        )

    # ---------------------------------------------------------
    # Object Creation
    # ---------------------------------------------------------

    def test_create_log_successfully(self):
        log = Log.objects.create(
            service=self.service,
            message="Everything is working",
            status=LogStatus.SUCCESS,
            severity="low",
            status_code=200,
            response_time_ms=120,
        )

        self.assertEqual(log.service, self.service)
        self.assertEqual(log.message, "Everything is working")
        self.assertEqual(log.status, LogStatus.SUCCESS)
        self.assertEqual(log.severity, "low")
        self.assertEqual(log.status_code, 200)
        self.assertEqual(log.response_time_ms, 120)

    def test_default_values(self):
        log = Log.objects.create(
            service=self.service,
            message="Hello",
        )

        self.assertEqual(
            log.status,
            LogStatus.SUCCESS,
        )

        self.assertEqual(
            log.severity,
            "low",
        )

        self.assertIsNone(log.status_code)
        self.assertIsNone(log.response_time_ms)
        self.assertEqual(log.metadata, {})

    # ---------------------------------------------------------
    # String Representation
    # ---------------------------------------------------------

    def test_string_representation(self):
        log = Log.objects.create(
            service=self.service,
            message="Created",
            status=LogStatus.ERROR,
        )

        self.assertEqual(
            str(log),
            f"{self.service.name} - error",
        )

    # ---------------------------------------------------------
    # Metadata
    # ---------------------------------------------------------

    def test_metadata_accepts_dictionary(self):
        log = Log.objects.create(
            service=self.service,
            message="Metadata",
            metadata={
                "ip": "127.0.0.1",
                "browser": "Chrome",
            },
        )

        self.assertEqual(
            log.metadata["ip"],
            "127.0.0.1",
        )

        self.assertEqual(
            log.metadata["browser"],
            "Chrome",
        )

    def test_metadata_defaults_to_empty_dict(self):
        log = Log.objects.create(
            service=self.service,
            message="No metadata",
        )

        self.assertEqual(log.metadata, {})

    def test_metadata_instances_are_independent(self):
        first = Log.objects.create(
            service=self.service,
            message="First",
        )

        second = Log.objects.create(
            service=self.service,
            message="Second",
        )

        first.metadata["hello"] = "world"
        first.save()

        second.refresh_from_db()

        self.assertEqual(second.metadata, {})

    # ---------------------------------------------------------
    # Status Choices
    # ---------------------------------------------------------

    def test_all_status_choices(self):
        for status in LogStatus.values:
            log = Log.objects.create(
                service=self.service,
                message=status,
                status=status,
            )

            self.assertEqual(log.status, status)

    # ---------------------------------------------------------
    # Severity Choices
    # ---------------------------------------------------------

    def test_all_severity_choices(self):
        severities = [
            "low",
            "medium",
            "high",
        ]

        for severity in severities:
            log = Log.objects.create(
                service=self.service,
                message=severity,
                severity=severity,
            )

            self.assertEqual(
                log.severity,
                severity,
            )

    # ---------------------------------------------------------
    # Status Code Validators
    # ---------------------------------------------------------

    def test_valid_status_code_lower_boundary(self):
        log = Log(
            service=self.service,
            message="Boundary",
            status_code=100,
        )

        log.full_clean()

    def test_valid_status_code_upper_boundary(self):
        log = Log(
            service=self.service,
            message="Boundary",
            status_code=599,
        )

        log.full_clean()

    def test_status_code_below_range_fails_validation(self):
        log = Log(
            service=self.service,
            message="Bad",
            status_code=99,
        )

        with self.assertRaises(Exception):
            log.full_clean()

    def test_status_code_above_range_fails_validation(self):
        log = Log(
            service=self.service,
            message="Bad",
            status_code=600,
        )

        with self.assertRaises(Exception):
            log.full_clean()

    # ---------------------------------------------------------
    # Response Time
    # ---------------------------------------------------------

    def test_response_time_can_be_zero(self):
        log = Log.objects.create(
            service=self.service,
            message="Instant",
            response_time_ms=0,
        )

        self.assertEqual(
            log.response_time_ms,
            0,
        )

    def test_response_time_can_store_large_values(self):
        log = Log.objects.create(
            service=self.service,
            message="Slow",
            response_time_ms=999999,
        )

        self.assertEqual(
            log.response_time_ms,
            999999,
        )

    # ---------------------------------------------------------
    # Ordering
    # ---------------------------------------------------------

    def test_logs_are_ordered_newest_first(self):
        old = Log.objects.create(
            service=self.service,
            message="Old",
        )

        new = Log.objects.create(
            service=self.service,
            message="New",
        )

        logs = list(Log.objects.all())

        self.assertEqual(logs[0], new)
        self.assertEqual(logs[1], old)

    # ---------------------------------------------------------
    # Timestamp
    # ---------------------------------------------------------

    def test_created_at_is_set(self):
        log = Log.objects.create(
            service=self.service,
            message="Timestamp",
        )

        self.assertIsNotNone(log.created_at)

    # ---------------------------------------------------------
    # Cascade Delete
    # ---------------------------------------------------------

    def test_logs_are_deleted_when_service_is_deleted(self):
        Log.objects.create(
            service=self.service,
            message="One",
        )

        Log.objects.create(
            service=self.service,
            message="Two",
        )

        self.assertEqual(
            Log.objects.count(),
            2,
        )

        self.service.delete()

        self.assertEqual(
            Log.objects.count(),
            0,
        )

    # ---------------------------------------------------------
    # Nullable Fields
    # ---------------------------------------------------------

    def test_nullable_fields_accept_none(self):
        log = Log.objects.create(
            service=self.service,
            message="Nullable",
            status_code=None,
            response_time_ms=None,
        )

        self.assertIsNone(log.status_code)
        self.assertIsNone(log.response_time_ms)

    # ---------------------------------------------------------
    # Foreign Key
    # ---------------------------------------------------------

    def test_log_belongs_to_correct_service(self):
        another = Service.objects.create(
            name="Payments",
            created_by=self.user,
        )

        first_log = Log.objects.create(
            service=self.service,
            message="API",
        )

        second_log = Log.objects.create(
            service=another,
            message="Payments",
        )

        self.assertEqual(
            self.service.logs.count(),
            1,
        )

        self.assertEqual(
            another.logs.count(),
            1,
        )

        self.assertEqual(
            self.service.logs.first(),
            first_log,
        )

        self.assertEqual(
            another.logs.first(),
            second_log,
        )


