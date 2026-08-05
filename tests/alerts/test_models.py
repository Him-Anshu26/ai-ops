from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

from accounts.models import User
from monitoring.models import Service, Log, LogStatus

from alerts.models import (
    Alert,
    AlertType,
    AlertStatus,
    AlertSeverity,
)


class AlertModelTests(TestCase):
    """
    Unit tests for Alert model.

    Covers:
    - Object creation
    - Default values
    - __str__
    - Choice fields
    - is_active property
    - mark_resolved()
    - increment()
    - Unique constraint
    - Foreign key behaviour
    - Nullable fields
    - Ordering
    - Indexes
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

        self.log = Log.objects.create(
            service=self.service,
            message="Server error",
            status=LogStatus.ERROR,
        )

    # ---------------------------------------------------------
    # Object Creation
    # ---------------------------------------------------------

    def test_create_alert_successfully(self):
        alert = Alert.objects.create(
            service=self.service,
            log=self.log,
            alert_type=AlertType.ERROR,
            message="500 server error",
            alert_key="error:500",
        )

        self.assertEqual(
            alert.service,
            self.service,
        )

        self.assertEqual(
            alert.log,
            self.log,
        )

        self.assertEqual(
            alert.alert_type,
            AlertType.ERROR,
        )

        self.assertEqual(
            alert.message,
            "500 server error",
        )

        self.assertEqual(
            alert.alert_key,
            "error:500",
        )

    # ---------------------------------------------------------
    # Defaults
    # ---------------------------------------------------------

    def test_default_status_is_open(self):
        alert = Alert.objects.create(
            service=self.service,
            message="Error",
            alert_type=AlertType.ERROR,
            alert_key="error",
        )

        self.assertEqual(
            alert.status,
            AlertStatus.OPEN,
        )

    def test_default_severity_is_medium(self):
        alert = Alert.objects.create(
            service=self.service,
            message="Latency issue",
            alert_type=AlertType.HIGH_LATENCY,
            alert_key="latency",
        )

        self.assertEqual(
            alert.severity,
            AlertSeverity.MEDIUM,
        )

    def test_default_trigger_count_is_one(self):
        alert = Alert.objects.create(
            service=self.service,
            message="Down",
            alert_type=AlertType.DOWNTIME,
            alert_key="downtime",
        )

        self.assertEqual(
            alert.trigger_count,
            1,
        )

    def test_last_triggered_at_is_set(self):
        alert = Alert.objects.create(
            service=self.service,
            message="Down",
            alert_type=AlertType.DOWNTIME,
            alert_key="downtime",
        )

        self.assertIsNotNone(
            alert.last_triggered_at,
        )

    # ---------------------------------------------------------
    # String Representation
    # ---------------------------------------------------------

    def test_string_representation(self):
        alert = Alert.objects.create(
            service=self.service,
            message="Server Error",
            alert_type=AlertType.ERROR,
            alert_key="error",
            status=AlertStatus.OPEN,
        )

        self.assertEqual(
            str(alert),
            f"Error - {self.service.name} (open)",
        )

    # ---------------------------------------------------------
    # Choice Fields
    # ---------------------------------------------------------

    def test_all_alert_types_work(self):
        for alert_type in AlertType.values:
            alert = Alert.objects.create(
                service=self.service,
                message="Testing",
                alert_type=alert_type,
                alert_key=f"type-{alert_type}",
            )

            self.assertEqual(
                alert.alert_type,
                alert_type,
            )

    def test_all_status_choices_work(self):
        for status in AlertStatus.values:
            alert = Alert.objects.create(
                service=self.service,
                message="Testing",
                alert_type=AlertType.ERROR,
                alert_key=f"status-{status}",
                status=status,
            )

            self.assertEqual(
                alert.status,
                status,
            )

    def test_all_severity_choices_work(self):
        for severity in AlertSeverity.values:
            alert = Alert.objects.create(
                service=self.service,
                message="Testing",
                alert_type=AlertType.ERROR,
                alert_key=f"severity-{severity}",
                severity=severity,
            )

            self.assertEqual(
                alert.severity,
                severity,
            )

    # ---------------------------------------------------------
    # is_active Property
    # ---------------------------------------------------------

    def test_is_active_true_when_open(self):
        alert = Alert.objects.create(
            service=self.service,
            message="Error",
            alert_type=AlertType.ERROR,
            alert_key="open",
            status=AlertStatus.OPEN,
        )

        self.assertTrue(
            alert.is_active,
        )

    def test_is_active_true_when_acknowledged(self):
        alert = Alert.objects.create(
            service=self.service,
            message="Error",
            alert_type=AlertType.ERROR,
            alert_key="ack",
            status=AlertStatus.ACKNOWLEDGED,
        )

        self.assertTrue(
            alert.is_active,
        )

    def test_is_active_false_when_resolved(self):
        alert = Alert.objects.create(
            service=self.service,
            message="Error",
            alert_type=AlertType.ERROR,
            alert_key="resolved",
            status=AlertStatus.RESOLVED,
        )

        self.assertFalse(
            alert.is_active,
        )

    # ---------------------------------------------------------
    # mark_resolved()
    # ---------------------------------------------------------

    def test_mark_resolved_updates_status(self):
        alert = Alert.objects.create(
            service=self.service,
            message="Failure",
            alert_type=AlertType.ERROR,
            alert_key="failure",
        )

        alert.mark_resolved()

        alert.refresh_from_db()

        self.assertEqual(
            alert.status,
            AlertStatus.RESOLVED,
        )

    def test_mark_resolved_sets_resolved_at(self):
        alert = Alert.objects.create(
            service=self.service,
            message="Failure",
            alert_type=AlertType.ERROR,
            alert_key="failure-time",
        )

        alert.mark_resolved()

        alert.refresh_from_db()

        self.assertIsNotNone(
            alert.resolved_at,
        )

    # ---------------------------------------------------------
    # increment()
    # ---------------------------------------------------------

    def test_increment_increases_trigger_count(self):
        alert = Alert.objects.create(
            service=self.service,
            message="Repeated error",
            alert_type=AlertType.ERROR,
            alert_key="repeat",
            trigger_count=1,
        )

        timestamp = timezone.now()

        alert.increment(timestamp)

        alert.refresh_from_db()

        self.assertEqual(
            alert.trigger_count,
            2,
        )

    def test_increment_updates_last_triggered_at(self):
        alert = Alert.objects.create(
            service=self.service,
            message="Repeated",
            alert_type=AlertType.ERROR,
            alert_key="repeat-time",
        )

        timestamp = timezone.now()

        alert.increment(timestamp)

        alert.refresh_from_db()

        self.assertEqual(
            alert.last_triggered_at,
            timestamp,
        )

    # ---------------------------------------------------------
    # Unique Constraint
    # ---------------------------------------------------------

    def test_only_one_active_alert_allowed_same_service_type_key(self):
        Alert.objects.create(
            service=self.service,
            message="First",
            alert_type=AlertType.ERROR,
            alert_key="500",
            status=AlertStatus.OPEN,
        )

        with self.assertRaises(IntegrityError):
            Alert.objects.create(
                service=self.service,
                message="Second",
                alert_type=AlertType.ERROR,
                alert_key="500",
                status=AlertStatus.OPEN,
            )

    def test_resolved_alert_allows_new_active_alert(self):
        Alert.objects.create(
            service=self.service,
            message="Old",
            alert_type=AlertType.ERROR,
            alert_key="500",
            status=AlertStatus.RESOLVED,
        )

        alert = Alert.objects.create(
            service=self.service,
            message="New",
            alert_type=AlertType.ERROR,
            alert_key="500",
            status=AlertStatus.OPEN,
        )

        self.assertEqual(
            alert.status,
            AlertStatus.OPEN,
        )

    # ---------------------------------------------------------
    # Foreign Key Behaviour
    # ---------------------------------------------------------

    def test_alert_deleted_when_service_deleted(self):
        Alert.objects.create(
            service=self.service,
            message="Delete",
            alert_type=AlertType.ERROR,
            alert_key="delete",
        )

        self.service.delete()

        self.assertEqual(
            Alert.objects.count(),
            0,
        )

    def test_log_can_be_null(self):
        alert = Alert.objects.create(
            service=self.service,
            message="No log",
            alert_type=AlertType.ERROR,
            alert_key="nolog",
            log=None,
        )

        self.assertIsNone(
            alert.log,
        )

    # ---------------------------------------------------------
    # Ordering
    # ---------------------------------------------------------

    def test_alerts_ordered_by_latest_trigger_first(self):
        old = Alert.objects.create(
            service=self.service,
            message="Old",
            alert_type=AlertType.ERROR,
            alert_key="old",
            last_triggered_at=timezone.now() - timezone.timedelta(hours=1),
        )

        new = Alert.objects.create(
            service=self.service,
            message="New",
            alert_type=AlertType.ERROR,
            alert_key="new",
            last_triggered_at=timezone.now(),
        )

        alerts = list(Alert.objects.all())

        self.assertEqual(
            alerts[0],
            new,
        )

        self.assertEqual(
            alerts[1],
            old,
        )

    # ---------------------------------------------------------
    # Meta
    # ---------------------------------------------------------

    def test_meta_ordering(self):
        self.assertEqual(
            Alert._meta.ordering,
            ["-last_triggered_at"],
        )

    def test_expected_indexes_exist(self):
        indexes = {
            index.name
            for index in Alert._meta.indexes
        }

        expected_indexes = {
            "idx_alert_service_status",
            "idx_alert_created_at",
            "idx_service_alert_type",
            "idx_service_severity",
            "idx_active_alerts_per_service",
            "idx_active_ser_last_triggered",
            "idx_status_last_triggered",
        }

        self.assertTrue(
            expected_indexes.issubset(indexes)
        )