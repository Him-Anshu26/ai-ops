from django.test import TestCase
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

from tests.factories import (
    UserFactory,
    ServiceFactory,
    AlertFactory,
)


class AlertWriteSerializerTests(TestCase):

    def setUp(self):
        self.user = UserFactory()

        self.service = ServiceFactory(
            created_by=self.user
        )

    # ---------------------------------------------------------
    # Valid Data
    # ---------------------------------------------------------

    def test_valid_alert_creation(self):
        serializer = AlertWriteSerializer(
            data={
                "service": self.service.id,
                "alert_type": AlertType.ERROR,
                "alert_key": "error:500",
                "severity": AlertSeverity.HIGH,
                "status": AlertStatus.OPEN,
                "message": "Server error",
            }
        )

        self.assertTrue(
            serializer.is_valid(),
            serializer.errors,
        )


    # ---------------------------------------------------------
    # Severity Validation
    # ---------------------------------------------------------

    def test_invalid_severity_fails(self):

        serializer = AlertWriteSerializer(
            data={
                "service": self.service.id,
                "alert_type": AlertType.ERROR,
                "alert_key": "error:500",
                "severity": "invalid",
                "status": AlertStatus.OPEN,
            }
        )

        self.assertFalse(
            serializer.is_valid()
        )

        self.assertEqual(
            serializer.errors["severity"][0],
            ErrorDetail(
                '"invalid" is not a valid choice.',
                code="invalid_choice",
            ),
        )


    # ---------------------------------------------------------
    # Status Validation
    # ---------------------------------------------------------

    def test_invalid_status_fails(self):

        serializer = AlertWriteSerializer(
            data={
                "service": self.service.id,
                "alert_type": AlertType.ERROR,
                "alert_key": "error:500",
                "status": "invalid",
            }
        )

        self.assertFalse(
            serializer.is_valid()
        )

        self.assertEqual(
            serializer.errors["status"][0],
            ErrorDetail(
                '"invalid" is not a valid choice.',
                code="invalid_choice",
            ),
        )


    # ---------------------------------------------------------
    # Alert Type Validation
    # ---------------------------------------------------------

    def test_invalid_alert_type_fails(self):

        serializer = AlertWriteSerializer(
            data={
                "service": self.service.id,
                "alert_type": "invalid",
                "alert_key": "error:500",
            }
        )

        self.assertFalse(
            serializer.is_valid()
        )

        self.assertEqual(
            serializer.errors["alert_type"][0],
            ErrorDetail(
                '"invalid" is not a valid choice.',
                code="invalid_choice",
            ),
        )


    # ---------------------------------------------------------
    # Alert Key Validation
    # ---------------------------------------------------------

    def test_alert_key_is_trimmed(self):

        serializer = AlertWriteSerializer(
            data={
                "service": self.service.id,
                "alert_type": AlertType.ERROR,
                "alert_key": "  error:500  ",
            }
        )

        self.assertTrue(
            serializer.is_valid(),
            serializer.errors,
        )

        self.assertEqual(
            serializer.validated_data["alert_key"],
            "error:500",
        )


    def test_empty_alert_key_fails(self):

        serializer = AlertWriteSerializer(
            data={
                "service": self.service.id,
                "alert_type": AlertType.ERROR,
                "alert_key": "",
            }
        )

        self.assertFalse(
            serializer.is_valid()
        )

        self.assertEqual(
            serializer.errors["alert_key"][0],
            ErrorDetail(
                "This field may not be blank.",
                code="blank",
            ),
        )


    def test_invalid_alert_key_format_fails(self):

        serializer = AlertWriteSerializer(
            data={
                "service": self.service.id,
                "alert_type": AlertType.ERROR,
                "alert_key": "server-error",
            }
        )

        self.assertFalse(
            serializer.is_valid()
        )

        self.assertEqual(
            serializer.errors["alert_key"][0],
            ErrorDetail(
                "Alert key format must be '<type>:<id>'.",
                code="invalid",
            ),
        )


    # ---------------------------------------------------------
    # Optional Message
    # ---------------------------------------------------------

    def test_message_can_be_blank(self):

        serializer = AlertWriteSerializer(
            data={
                "service": self.service.id,
                "alert_type": AlertType.ERROR,
                "alert_key": "error:500",
                "message": "",
            }
        )

        self.assertTrue(
            serializer.is_valid(),
            serializer.errors,
        )



class AlertReadSerializerTests(TestCase):

    def test_read_serializer_returns_expected_fields(self):

        alert = AlertFactory()

        serializer = AlertReadSerializer(alert)

        data = serializer.data

        self.assertEqual(
            data["id"],
            alert.id,
        )

        self.assertEqual(
            data["service"],
            alert.service.id,
        )

        self.assertEqual(
            data["service_name"],
            alert.service.name,
        )

        self.assertEqual(
            data["message"],
            alert.message,
        )


    def test_read_serializer_contains_read_only_fields(self):

        alert = AlertFactory()

        serializer = AlertReadSerializer(alert)

        self.assertIn(
            "created_at",
            serializer.data,
        )

        self.assertIn(
            "last_triggered_at",
            serializer.data,
        )



class AlertResolveSerializerTests(TestCase):

    def test_resolving_alert_requires_note(self):

        serializer = AlertResolveSerializer(
            data={
                "status": AlertStatus.RESOLVED,
                "resolution_note": "",
            }
        )

        self.assertFalse(
            serializer.is_valid()
        )

        self.assertEqual(
            serializer.errors["resolution_note"][0],
            ErrorDetail(
                "Resolution note is required.",
                code="invalid",
            ),
        )


    def test_resolving_alert_with_note_is_valid(self):

        serializer = AlertResolveSerializer(
            data={
                "status": AlertStatus.RESOLVED,
                "resolution_note": "Fixed database issue",
            }
        )

        self.assertTrue(
            serializer.is_valid(),
            serializer.errors,
        )


    def test_open_status_without_note_is_valid(self):

        serializer = AlertResolveSerializer(
            data={
                "status": AlertStatus.OPEN,
            }
        )

        self.assertTrue(
            serializer.is_valid(),
            serializer.errors,
        )