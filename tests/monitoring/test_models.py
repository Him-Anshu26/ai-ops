import pytest

from django.db import IntegrityError, transaction
from django.utils import timezone

from monitoring.models import (
    Log,
    LogStatus,
    Service,
    Status,
)

from tests.factories import ServiceFactory


@pytest.mark.django_db
class TestServiceModel:
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

    # ---------------------------------------------------------
    # Object Creation
    # ---------------------------------------------------------

    def test_create_service_successfully(self, user):
        service = Service.objects.create(
            name="Authentication API",
            description="Handles authentication",
            created_by=user,
        )

        assert service.name == "Authentication API"
        assert service.description == "Handles authentication"
        assert service.status == Status.ACTIVE
        assert service.is_deleted is False
        assert service.created_by == user

    def test_default_values(self, user):
        service = Service.objects.create(
            name="Payments",
            created_by=user,
        )

        assert service.status == Status.ACTIVE
        assert service.is_deleted is False
        assert service.last_checked_at is None

    # ---------------------------------------------------------
    # String Representation
    # ---------------------------------------------------------

    def test_string_representation(self, user):
        service = Service.objects.create(
            name="Monitoring",
            created_by=user,
        )

        assert str(service) == f"Monitoring ({user.email})"

    # ---------------------------------------------------------
    # Slug Generation
    # ---------------------------------------------------------

    def test_slug_is_generated_automatically(self, user):
        service = Service.objects.create(
            name="My Awesome Service",
            created_by=user,
        )

        assert service.slug == "my-awesome-service"

    def test_slug_is_not_modified_when_already_provided(self, user):
        service = Service.objects.create(
            name="Random Service",
            slug="custom-slug",
            created_by=user,
        )

        assert service.slug == "custom-slug"

    def test_empty_name_generates_default_slug(self, user):
        service = Service.objects.create(
            name="!!!",
            created_by=user,
        )

        assert service.slug == "service"

    # Slug Collision
    def test_slug_can_be_reused_after_soft_delete(self, user):
        first = Service.objects.create(
            name="API Server",
            created_by=user,
        )

        first.is_deleted = True
        first.save(update_fields=["is_deleted"])

        second = Service.objects.create(
            name="API Server",
            created_by=user,
        )

        assert first.slug == "api-server"
        assert second.slug == "api-server"

    def test_same_slug_allowed_for_different_users(self, user, another_user):
        first = Service.objects.create(
            name="Backend",
            created_by=user,
        )

        second = Service.objects.create(
            name="Backend",
            created_by=another_user,
        )

        assert first.slug == "backend"
        assert second.slug == "backend"

    # ---------------------------------------------------------
    # Constraints
    # ---------------------------------------------------------

    def test_same_name_same_user_not_allowed(self, user):
        Service.objects.create(
            name="Orders",
            created_by=user,
        )

        with pytest.raises(ValueError, match="Could not generate unique slug"):
            Service.objects.create(
                name="Orders",
                created_by=user,
            )

    def test_same_name_different_users_allowed(self, user, another_user):
        Service.objects.create(
            name="Orders",
            created_by=user,
        )

        service = Service.objects.create(
            name="Orders",
            created_by=another_user,
        )

        assert service.name == "Orders"

    def test_same_slug_same_user_not_allowed(self, user):
        Service.objects.create(
            name="Users",
            slug="users-api",
            created_by=user,
        )

        with pytest.raises(IntegrityError):
            with transaction.atomic():
                Service.objects.create(
                    name="Something Else",
                    slug="users-api",
                    created_by=user,
                )

    def test_same_slug_different_users_allowed(self, user, another_user):
        Service.objects.create(
            name="Users",
            slug="users-api",
            created_by=user,
        )

        service = Service.objects.create(
            name="Users 2",
            slug="users-api",
            created_by=another_user,
        )

        assert service.slug == "users-api"

    # ---------------------------------------------------------
    # Soft Delete Behaviour
    # ---------------------------------------------------------

    def test_soft_deleted_name_can_be_reused(self, user):
        service = Service.objects.create(
            name="Gateway",
            created_by=user,
        )

        service.is_deleted = True
        service.save(update_fields=["is_deleted"])

        reused = Service.objects.create(
            name="Gateway",
            created_by=user,
        )

        assert reused.name == "Gateway"
        assert reused.is_deleted is False

    def test_soft_deleted_slug_can_be_reused(self, user):
        service = Service.objects.create(
            name="Email",
            slug="email-service",
            created_by=user,
        )

        service.is_deleted = True
        service.save(update_fields=["is_deleted"])

        reused = Service.objects.create(
            name="Another Email",
            slug="email-service",
            created_by=user,
        )

        assert reused.slug == "email-service"

    # ---------------------------------------------------------
    # Ordering
    # ---------------------------------------------------------

    def test_ordering_newest_first(self, user):
        old = Service.objects.create(
            name="Old",
            created_by=user,
        )

        new = Service.objects.create(
            name="New",
            created_by=user,
        )

        services = list(Service.objects.all())

        assert services[0] == new
        assert services[1] == old

    # ---------------------------------------------------------
    # Timestamp Fields
    # ---------------------------------------------------------

    def test_created_at_is_set(self, user):
        service = Service.objects.create(
            name="Logging",
            created_by=user,
        )

        assert service.created_at is not None

    def test_updated_at_changes_after_save(self, user):
        service = Service.objects.create(
            name="Metrics",
            created_by=user,
        )

        original = service.updated_at

        service.description = "Updated description"
        service.save()

        service.refresh_from_db()

        assert service.updated_at >= original

    # ---------------------------------------------------------
    # Status Choices
    # ---------------------------------------------------------

    def test_all_status_choices_work(self, user):
        for status in Status.values:
            service = Service.objects.create(
                name=f"Service-{status}",
                created_by=user,
                status=status,
            )

            assert service.status == status

    # ---------------------------------------------------------
    # Last Checked
    # ---------------------------------------------------------

    def test_last_checked_at_can_be_updated(self, user):
        service = Service.objects.create(
            name="Health API",
            created_by=user,
        )

        now = timezone.now()

        service.last_checked_at = now
        service.save(update_fields=["last_checked_at"])

        service.refresh_from_db()

        assert service.last_checked_at is not None
        assert (
            service.last_checked_at.replace(microsecond=0)
            == now.replace(microsecond=0)
        )


@pytest.mark.django_db
class TestLogModel:
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

    # ---------------------------------------------------------
    # Object Creation
    # ---------------------------------------------------------

    def test_create_log_successfully(self, service):
        log = Log.objects.create(
            service=service,
            message="Everything is working",
            status=LogStatus.SUCCESS,
            severity="low",
            status_code=200,
            response_time_ms=120,
        )

        assert log.service == service
        assert log.message == "Everything is working"
        assert log.status == LogStatus.SUCCESS
        assert log.severity == "low"
        assert log.status_code == 200
        assert log.response_time_ms == 120

    def test_default_values(self, service):
        log = Log.objects.create(
            service=service,
            message="Hello",
        )

        assert log.status == LogStatus.SUCCESS
        assert log.severity == "low"
        assert log.status_code is None
        assert log.response_time_ms is None
        assert log.metadata == {}

    # ---------------------------------------------------------
    # String Representation
    # ---------------------------------------------------------

    def test_string_representation(self, service):
        log = Log.objects.create(
            service=service,
            message="Created",
            status=LogStatus.ERROR,
        )

        assert str(log) == f"{service.name} - error"

    # ---------------------------------------------------------
    # Metadata
    # ---------------------------------------------------------

    def test_metadata_accepts_dictionary(self, service):
        log = Log.objects.create(
            service=service,
            message="Metadata",
            metadata={
                "ip": "127.0.0.1",
                "browser": "Chrome",
            },
        )

        assert log.metadata["ip"] == "127.0.0.1"
        assert log.metadata["browser"] == "Chrome"

    def test_metadata_defaults_to_empty_dict(self, service):
        log = Log.objects.create(
            service=service,
            message="No metadata",
        )

        assert log.metadata == {}

    def test_metadata_instances_are_independent(self, service):
        first = Log.objects.create(
            service=service,
            message="First",
        )

        second = Log.objects.create(
            service=service,
            message="Second",
        )

        first.metadata["hello"] = "world"
        first.save()

        second.refresh_from_db()

        assert second.metadata == {}

    # ---------------------------------------------------------
    # Status Choices
    # ---------------------------------------------------------

    def test_all_status_choices(self, service):
        for status in LogStatus.values:
            log = Log.objects.create(
                service=service,
                message=status,
                status=status,
            )

            assert log.status == status

    # ---------------------------------------------------------
    # Severity Choices
    # ---------------------------------------------------------

    def test_all_severity_choices(self, service):
        severities = [
            "low",
            "medium",
            "high",
        ]

        for severity in severities:
            log = Log.objects.create(
                service=service,
                message=severity,
                severity=severity,
            )

            assert log.severity == severity

    # ---------------------------------------------------------
    # Status Code Validators
    # ---------------------------------------------------------

    def test_valid_status_code_lower_boundary(self, service):
        log = Log(
            service=service,
            message="Boundary",
            status_code=100,
        )

        log.full_clean()

    def test_valid_status_code_upper_boundary(self, service):
        log = Log(
            service=service,
            message="Boundary",
            status_code=599,
        )

        log.full_clean()

    def test_status_code_below_range_fails_validation(self, service):
        log = Log(
            service=service,
            message="Bad",
            status_code=99,
        )

        with pytest.raises(Exception):
            log.full_clean()

    def test_status_code_above_range_fails_validation(self, service):
        log = Log(
            service=service,
            message="Bad",
            status_code=600,
        )

        with pytest.raises(Exception):
            log.full_clean()

    # ---------------------------------------------------------
    # Response Time
    # ---------------------------------------------------------

    def test_response_time_can_be_zero(self, service):
        log = Log.objects.create(
            service=service,
            message="Instant",
            response_time_ms=0,
        )

        assert log.response_time_ms == 0

    def test_response_time_can_store_large_values(self, service):
        log = Log.objects.create(
            service=service,
            message="Slow",
            response_time_ms=999999,
        )

        assert log.response_time_ms == 999999

    # ---------------------------------------------------------
    # Ordering
    # ---------------------------------------------------------

    def test_logs_are_ordered_newest_first(self, service):
        old = Log.objects.create(
            service=service,
            message="Old",
        )

        new = Log.objects.create(
            service=service,
            message="New",
        )

        logs = list(Log.objects.all())

        assert logs[0] == new
        assert logs[1] == old

    # ---------------------------------------------------------
    # Timestamp
    # ---------------------------------------------------------

    def test_created_at_is_set(self, service):
        log = Log.objects.create(
            service=service,
            message="Timestamp",
        )

        assert log.created_at is not None

    # ---------------------------------------------------------
    # Cascade Delete
    # ---------------------------------------------------------

    def test_logs_are_deleted_when_service_is_deleted(self, service):
        Log.objects.create(
            service=service,
            message="One",
        )

        Log.objects.create(
            service=service,
            message="Two",
        )

        assert Log.objects.count() == 2

        service.delete()

        assert Log.objects.count() == 0

    # ---------------------------------------------------------
    # Nullable Fields
    # ---------------------------------------------------------

    def test_nullable_fields_accept_none(self, service):
        log = Log.objects.create(
            service=service,
            message="Nullable",
            status_code=None,
            response_time_ms=None,
        )

        assert log.status_code is None
        assert log.response_time_ms is None

    # ---------------------------------------------------------
    # Foreign Key
    # ---------------------------------------------------------

    def test_log_belongs_to_correct_service(self, service):
        another = ServiceFactory(
            created_by=service.created_by,
        )

        first_log = Log.objects.create(
            service=service,
            message="API",
        )

        second_log = Log.objects.create(
            service=another,
            message="Payments",
        )

        assert service.logs.count() == 1
        assert another.logs.count() == 1
        assert service.logs.first() == first_log
        assert another.logs.first() == second_log
