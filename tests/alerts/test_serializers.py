import pytest
from rest_framework.exceptions import ErrorDetail

from alerts.models import (
    AlertStatus,
    AlertSeverity,
    AlertType,
)

from alerts.serializers.alert_serializer import (
    AlertWriteSerializer,
    AlertReadSerializer,
    AlertResolveSerializer,
)

from tests.factories import AlertFactory


@pytest.mark.django_db
class TestAlertWriteSerializer:

    # ---------------------------------------------------------
    # Valid Data
    # ---------------------------------------------------------

    def test_valid_alert_creation(self, service):
        serializer = AlertWriteSerializer(
            data={
                "service": service.id,
                "alert_type": AlertType.ERROR,
                "alert_key": "error:500",
                "severity": AlertSeverity.HIGH,
                "status": AlertStatus.OPEN,
                "message": "Server error",
            }
        )

        assert serializer.is_valid(), serializer.errors


    # ---------------------------------------------------------
    # Severity Validation
    # ---------------------------------------------------------

    def test_invalid_severity_fails(self, service):
        serializer = AlertWriteSerializer(
            data={
                "service": service.id,
                "alert_type": AlertType.ERROR,
                "alert_key": "error:500",
                "severity": "invalid",
                "status": AlertStatus.OPEN,
            }
        )

        assert not serializer.is_valid()
        assert serializer.errors["severity"][0] == ErrorDetail(
            '"invalid" is not a valid choice.',
            code="invalid_choice",
        )


    # ---------------------------------------------------------
    # Status Validation
    # ---------------------------------------------------------

    def test_invalid_status_fails(self, service):
        serializer = AlertWriteSerializer(
            data={
                "service": service.id,
                "alert_type": AlertType.ERROR,
                "alert_key": "error:500",
                "status": "invalid",
            }
        )

        assert not serializer.is_valid()
        assert serializer.errors["status"][0] == ErrorDetail(
            '"invalid" is not a valid choice.',
            code="invalid_choice",
        )


    # ---------------------------------------------------------
    # Alert Type Validation
    # ---------------------------------------------------------

    def test_invalid_alert_type_fails(self, service):
        serializer = AlertWriteSerializer(
            data={
                "service": service.id,
                "alert_type": "invalid",
                "alert_key": "error:500",
            }
        )

        assert not serializer.is_valid()
        assert serializer.errors["alert_type"][0] == ErrorDetail(
            '"invalid" is not a valid choice.',
            code="invalid_choice",
        )


    # ---------------------------------------------------------
    # Alert Key Validation
    # ---------------------------------------------------------

    def test_alert_key_is_trimmed(self, service):
        serializer = AlertWriteSerializer(
            data={
                "service": service.id,
                "alert_type": AlertType.ERROR,
                "alert_key": "  error:500  ",
            }
        )

        assert serializer.is_valid(), serializer.errors
        assert serializer.validated_data["alert_key"] == "error:500"


    def test_empty_alert_key_fails(self, service):
        serializer = AlertWriteSerializer(
            data={
                "service": service.id,
                "alert_type": AlertType.ERROR,
                "alert_key": "",
            }
        )

        assert not serializer.is_valid()
        assert serializer.errors["alert_key"][0] == ErrorDetail(
            "This field may not be blank.",
            code="blank",
        )


    def test_invalid_alert_key_format_fails(self, service):
        serializer = AlertWriteSerializer(
            data={
                "service": service.id,
                "alert_type": AlertType.ERROR,
                "alert_key": "server-error",
            }
        )

        assert not serializer.is_valid()
        assert serializer.errors["alert_key"][0] == ErrorDetail(
            "Alert key format must be '<type>:<id>'.",
            code="invalid",
        )


    # ---------------------------------------------------------
    # Optional Message
    # ---------------------------------------------------------

    def test_message_can_be_blank(self, service):
        serializer = AlertWriteSerializer(
            data={
                "service": service.id,
                "alert_type": AlertType.ERROR,
                "alert_key": "error:500",
                "message": "",
            }
        )

        assert serializer.is_valid(), serializer.errors



@pytest.mark.django_db
class TestAlertReadSerializer:

    def test_read_serializer_returns_expected_fields(self):
        alert = AlertFactory()
        serializer = AlertReadSerializer(alert)
        data = serializer.data

        assert data["id"] == alert.id
        assert data["service"] == alert.service.id
        assert data["service_name"] == alert.service.name
        assert data["message"] == alert.message

    def test_read_serializer_contains_read_only_fields(self):
        alert = AlertFactory()
        serializer = AlertReadSerializer(alert)

        assert "created_at" in serializer.data
        assert "last_triggered_at" in serializer.data



class TestAlertResolveSerializer:

    def test_resolving_alert_requires_note(self):
        serializer = AlertResolveSerializer(
            data={
                "status": AlertStatus.RESOLVED,
                "resolution_note": "",
            }
        )

        assert not serializer.is_valid()
        assert serializer.errors["resolution_note"][0] == ErrorDetail(
            "Resolution note is required.",
            code="invalid",
        )

    def test_resolving_alert_with_note_is_valid(self):
        serializer = AlertResolveSerializer(
            data={
                "status": AlertStatus.RESOLVED,
                "resolution_note": "Fixed database issue",
            }
        )

        assert serializer.is_valid(), serializer.errors

    def test_open_status_without_note_is_valid(self):
        serializer = AlertResolveSerializer(
            data={
                "status": AlertStatus.OPEN,
            }
        )

        assert serializer.is_valid(), serializer.errors