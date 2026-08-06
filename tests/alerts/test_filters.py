from datetime import timedelta

import pytest
from django.utils import timezone

from alerts.filters import AlertFilter
from alerts.models import (
    Alert,
    AlertSeverity,
    AlertStatus,
    AlertType,
)

from tests.factories import (
    AlertFactory,
    ServiceFactory,
)

# ============================================================
# AlertFilter Tests
# ============================================================


@pytest.mark.django_db
class TestAlertFilter:
    """
    Unit tests for AlertFilter.
    """

    def test_filter_by_service(self):
        service_one = ServiceFactory()
        service_two = ServiceFactory()

        alert_one = AlertFactory(service=service_one)
        AlertFactory(service=service_two)

        queryset = AlertFilter(
            data={"service": service_one.id},
            queryset=Alert.objects.all(),
        ).qs

        assert queryset.count() == 1
        assert queryset.first() == alert_one

    def test_filter_by_status_case_insensitive(self):
        alert = AlertFactory(status=AlertStatus.OPEN)
        AlertFactory(status=AlertStatus.RESOLVED)

        queryset = AlertFilter(
            data={"status": "open"},
            queryset=Alert.objects.all(),
        ).qs

        assert queryset.count() == 1
        assert queryset.first() == alert

    def test_filter_by_alert_type_case_insensitive(self):
        alert = AlertFactory(alert_type=AlertType.ERROR)
        AlertFactory(alert_type=AlertType.HIGH_LATENCY)

        queryset = AlertFilter(
            data={"alert_type": "error"},
            queryset=Alert.objects.all(),
        ).qs

        assert queryset.count() == 1
        assert queryset.first() == alert

    def test_filter_by_severity_case_insensitive(self):
        alert = AlertFactory(severity=AlertSeverity.CRITICAL)
        AlertFactory(severity=AlertSeverity.HIGH)

        queryset = AlertFilter(
            data={"severity": "critical"},
            queryset=Alert.objects.all(),
        ).qs

        assert queryset.count() == 1
        assert queryset.first() == alert

    def test_filter_by_message_icontains(self):
        alert = AlertFactory(message="Database connection failed")
        AlertFactory(message="CPU usage high")

        queryset = AlertFilter(
            data={"message": "connection"},
            queryset=Alert.objects.all(),
        ).qs

        assert queryset.count() == 1
        assert queryset.first() == alert

    def test_message_filter_is_case_insensitive(self):
        alert = AlertFactory(message="Database Error")
        AlertFactory(message="Disk Failure")

        queryset = AlertFilter(
            data={"message": "database"},
            queryset=Alert.objects.all(),
        ).qs

        assert queryset.count() == 1
        assert queryset.first() == alert

    def test_filter_by_created_after(self):
        older = AlertFactory()
        newer = AlertFactory()

        older.created_at = timezone.now() - timedelta(days=5)
        newer.created_at = timezone.now()

        older.save(update_fields=["created_at"])
        newer.save(update_fields=["created_at"])

        queryset = AlertFilter(
            data={"created_after": (timezone.now() - timedelta(days=1))},
            queryset=Alert.objects.all(),
        ).qs

        assert list(queryset) == [newer]

    def test_filter_by_created_before(self):
        older = AlertFactory()
        newer = AlertFactory()

        older.created_at = timezone.now() - timedelta(days=5)
        newer.created_at = timezone.now()

        older.save(update_fields=["created_at"])
        newer.save(update_fields=["created_at"])

        queryset = AlertFilter(
            data={"created_before": (timezone.now() - timedelta(days=1))},
            queryset=Alert.objects.all(),
        ).qs

        assert list(queryset) == [older]

    def test_filter_by_last_triggered_after(self):
        older = AlertFactory()
        newer = AlertFactory()

        older.last_triggered_at = timezone.now() - timedelta(days=7)
        newer.last_triggered_at = timezone.now()

        older.save(update_fields=["last_triggered_at"])
        newer.save(update_fields=["last_triggered_at"])

        queryset = AlertFilter(
            data={"last_triggered_after": (timezone.now() - timedelta(days=1))},
            queryset=Alert.objects.all(),
        ).qs

        assert list(queryset) == [newer]

    def test_filter_by_last_triggered_before(self):
        older = AlertFactory()
        newer = AlertFactory()

        older.last_triggered_at = timezone.now() - timedelta(days=7)
        newer.last_triggered_at = timezone.now()

        older.save(update_fields=["last_triggered_at"])
        newer.save(update_fields=["last_triggered_at"])

        queryset = AlertFilter(
            data={"last_triggered_before": (timezone.now() - timedelta(days=1))},
            queryset=Alert.objects.all(),
        ).qs

        assert list(queryset) == [older]

    def test_filter_by_min_trigger_count(self):
        AlertFactory(trigger_count=2)
        alert = AlertFactory(trigger_count=10)

        queryset = AlertFilter(
            data={"min_trigger_count": 5},
            queryset=Alert.objects.all(),
        ).qs

        assert list(queryset) == [alert]

    def test_filter_by_max_trigger_count(self):
        alert = AlertFactory(trigger_count=2)
        AlertFactory(trigger_count=10)

        queryset = AlertFilter(
            data={"max_trigger_count": 5},
            queryset=Alert.objects.all(),
        ).qs

        assert list(queryset) == [alert]

    def test_multiple_filters_can_be_combined(self):
        service = ServiceFactory()
        matching = AlertFactory(service=service, status=AlertStatus.OPEN)
        AlertFactory(service=service, status=AlertStatus.RESOLVED)
        AlertFactory(status=AlertStatus.OPEN)

        queryset = AlertFilter(
            data={
                "service": service.id,
                "status": "open",
            },
            queryset=Alert.objects.all(),
        ).qs

        assert list(queryset) == [matching]

    def test_returns_empty_queryset_when_no_match(self):
        AlertFactory(status=AlertStatus.OPEN)

        queryset = AlertFilter(
            data={"status": "resolved"},
            queryset=Alert.objects.all(),
        ).qs

        assert not queryset.exists()

    def test_empty_filter_returns_all_alerts(self):
        AlertFactory.create_batch(3)

        queryset = AlertFilter(
            data={},
            queryset=Alert.objects.all(),
        ).qs

        assert queryset.count() == 3

    def test_invalid_service_returns_empty_queryset(self):
        AlertFactory.create_batch(2)

        queryset = AlertFilter(
            data={"service": 999999},
            queryset=Alert.objects.all(),
        ).qs

        assert not queryset.exists()

    def test_filterset_model(self):
        assert AlertFilter._meta.model == Alert

    def test_filterset_fields(self):
        assert list(AlertFilter._meta.fields) == [
            "service",
            "status",
            "alert_type",
            "severity",
            "created_after",
            "created_before",
            "last_triggered_after",
            "last_triggered_before",
            "min_trigger_count",
            "max_trigger_count",
            "message",
        ]