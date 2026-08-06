import pytest
from django.db import IntegrityError
from django.utils import timezone

from alerts.models import (
    Alert,
    AlertType,
    AlertStatus,
    AlertSeverity,
)

from tests.factories import AlertFactory


@pytest.mark.django_db
class TestAlertModel:
    """
    Unit tests for Alert model.
    """

    # ---------------------------------------------------------
    # Object Creation
    # ---------------------------------------------------------

    def test_create_alert_successfully(self, service, log):
        alert = Alert.objects.create(
            service=service,
            log=log,
            alert_type=AlertType.ERROR,
            message="500 server error",
            alert_key="error:500",
        )

        assert alert.service == service
        assert alert.log == log
        assert alert.alert_type == AlertType.ERROR
        assert alert.message == "500 server error"
        assert alert.alert_key == "error:500"

    # ---------------------------------------------------------
    # Defaults
    # ---------------------------------------------------------

    def test_default_status_is_open(self, service):
        alert = Alert.objects.create(
            service=service,
            message="Error",
            alert_type=AlertType.ERROR,
            alert_key="error",
        )
        assert alert.status == AlertStatus.OPEN

    def test_default_severity_is_medium(self, service):
        alert = Alert.objects.create(
            service=service,
            message="Latency issue",
            alert_type=AlertType.HIGH_LATENCY,
            alert_key="latency",
        )
        assert alert.severity == AlertSeverity.MEDIUM

    def test_default_trigger_count_is_one(self, service):
        alert = Alert.objects.create(
            service=service,
            message="Down",
            alert_type=AlertType.DOWNTIME,
            alert_key="downtime",
        )
        assert alert.trigger_count == 1

    def test_last_triggered_at_is_set(self, service):
        alert = Alert.objects.create(
            service=service,
            message="Down",
            alert_type=AlertType.DOWNTIME,
            alert_key="downtime",
        )
        assert alert.last_triggered_at is not None

    # ---------------------------------------------------------
    # String Representation
    # ---------------------------------------------------------

    def test_string_representation(self, service):
        alert = AlertFactory(
            service=service,
            message="Server Error",
            alert_type=AlertType.ERROR,
            status=AlertStatus.OPEN,
        )
        assert str(alert) == f"Error - {service.name} (open)"

    # ---------------------------------------------------------
    # Choice Fields
    # ---------------------------------------------------------

    def test_all_alert_types_work(self, service):
        for alert_type in AlertType.values:
            alert = AlertFactory(
                service=service,
                message="Testing",
                alert_type=alert_type,
            )
            assert alert.alert_type == alert_type

    def test_all_status_choices_work(self, service):
        for status in AlertStatus.values:
            alert = AlertFactory(
                service=service,
                status=status,
            )
            assert alert.status == status

    def test_all_severity_choices_work(self, service):
        for severity in AlertSeverity.values:
            alert = AlertFactory(
                service=service,
                severity=severity,
            )
            assert alert.severity == severity

    # ---------------------------------------------------------
    # is_active Property
    # ---------------------------------------------------------

    def test_is_active_true_when_open(self, service):
        alert = AlertFactory(
            service=service,
            status=AlertStatus.OPEN,
        )
        assert alert.is_active is True

    def test_is_active_true_when_acknowledged(self, service):
        alert = AlertFactory(
            service=service,
            status=AlertStatus.ACKNOWLEDGED,
        )
        assert alert.is_active is True

    def test_is_active_false_when_resolved(self, service):
        alert = AlertFactory(
            service=service,
            status=AlertStatus.RESOLVED,
        )
        assert alert.is_active is False

    # ---------------------------------------------------------
    # mark_resolved()
    # ---------------------------------------------------------

    def test_mark_resolved_updates_status(self, service):
        alert = AlertFactory(
            service=service,
            status=AlertStatus.OPEN,
        )
        alert.mark_resolved()
        alert.refresh_from_db()
        assert alert.status == AlertStatus.RESOLVED

    def test_mark_resolved_sets_resolved_at(self, service):
        alert = AlertFactory(
            service=service,
            status=AlertStatus.OPEN,
        )
        alert.mark_resolved()
        alert.refresh_from_db()
        assert alert.resolved_at is not None

    # ---------------------------------------------------------
    # increment()
    # ---------------------------------------------------------

    def test_increment_increases_trigger_count(self, service):
        alert = AlertFactory(
            service=service,
            trigger_count=1,
        )
        timestamp = timezone.now()
        alert.increment(timestamp)
        alert.refresh_from_db()
        assert alert.trigger_count == 2

    def test_increment_updates_last_triggered_at(self, service):
        alert = AlertFactory(
            service=service,
        )
        timestamp = timezone.now()
        alert.increment(timestamp)
        alert.refresh_from_db()
        assert alert.last_triggered_at == timestamp

    # ---------------------------------------------------------
    # Unique Constraint
    # ---------------------------------------------------------

    def test_only_one_active_alert_allowed_same_service_type_key(self, service):
        AlertFactory(
            service=service,
            alert_type=AlertType.ERROR,
            alert_key="500",
            status=AlertStatus.OPEN,
        )
        with pytest.raises(IntegrityError):
            Alert.objects.create(
                service=service,
                message="Second",
                alert_type=AlertType.ERROR,
                alert_key="500",
                status=AlertStatus.OPEN,
            )

    def test_resolved_alert_allows_new_active_alert(self, service):
        AlertFactory(
            service=service,
            alert_type=AlertType.ERROR,
            alert_key="500",
            status=AlertStatus.RESOLVED,
        )
        alert = Alert.objects.create(
            service=service,
            message="New",
            alert_type=AlertType.ERROR,
            alert_key="500",
            status=AlertStatus.OPEN,
        )
        assert alert.status == AlertStatus.OPEN

    # ---------------------------------------------------------
    # Foreign Key Behaviour
    # ---------------------------------------------------------

    def test_alert_deleted_when_service_deleted(self, service):
        AlertFactory(
            service=service,
        )
        service.delete()
        assert Alert.objects.count() == 0

    def test_log_can_be_null(self, service):
        alert = AlertFactory(
            service=service,
            log=None,
        )
        assert alert.log is None

    # ---------------------------------------------------------
    # Ordering
    # ---------------------------------------------------------

    def test_alerts_ordered_by_latest_trigger_first(self, service):
        old = AlertFactory(
            service=service,
            last_triggered_at=timezone.now() - timezone.timedelta(hours=1),
        )
        new = AlertFactory(
            service=service,
            last_triggered_at=timezone.now(),
        )

        alerts = list(Alert.objects.all())
        assert alerts[0] == new
        assert alerts[1] == old

    # ---------------------------------------------------------
    # Meta
    # ---------------------------------------------------------

    def test_meta_ordering(self):
        assert Alert._meta.ordering == ["-last_triggered_at"]

    def test_expected_indexes_exist(self):
        indexes = {index.name for index in Alert._meta.indexes}
        expected_indexes = {
            "idx_alert_service_status",
            "idx_alert_created_at",
            "idx_service_alert_type",
            "idx_service_severity",
            "idx_active_alerts_per_service",
            "idx_active_ser_last_triggered",
            "idx_status_last_triggered",
        }
        assert expected_indexes.issubset(indexes)