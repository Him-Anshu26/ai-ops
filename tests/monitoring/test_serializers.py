import pytest

from monitoring.models import Log, LogStatus
from monitoring.serializers.log_serializer import (
    LogReadSerializer,
    LogWriteSerializer,
)

from tests.factories import LogFactory


@pytest.mark.django_db
class TestLogWriteSerializer:
    """
    Unit tests for LogWriteSerializer.

    Covers:
    - valid payloads
    - field validation
    - object validation
    - fallback message generation
    - serializer save()
    """

    # ---------------------------------------------------------
    # Valid Payloads
    # ---------------------------------------------------------

    def test_valid_success_log(self, service):
        serializer = LogWriteSerializer(
            data={
                "service": service.id,
                "status": LogStatus.SUCCESS,
                "status_code": 200,
                "response_time_ms": 125,
                "message": "Everything works",
            }
        )

        assert serializer.is_valid(), serializer.errors

    def test_valid_warning_log(self, service):
        serializer = LogWriteSerializer(
            data={
                "service": service.id,
                "status": LogStatus.WARNING,
                "status_code": 429,
                "response_time_ms": 900,
                "message": "Slow response",
            }
        )

        assert serializer.is_valid(), serializer.errors

    def test_valid_error_log(self, service):
        serializer = LogWriteSerializer(
            data={
                "service": service.id,
                "status": LogStatus.ERROR,
                "status_code": 500,
                "response_time_ms": 2500,
                "message": "Internal server error",
            }
        )

        assert serializer.is_valid(), serializer.errors

    def test_valid_without_status_code(self, service):
        serializer = LogWriteSerializer(
            data={
                "service": service.id,
                "status": LogStatus.SUCCESS,
                "response_time_ms": 120,
                "message": "No status code",
            }
        )

        assert serializer.is_valid(), serializer.errors

    def test_valid_without_response_time(self, service):
        serializer = LogWriteSerializer(
            data={
                "service": service.id,
                "status": LogStatus.SUCCESS,
                "status_code": 200,
                "message": "No response time",
            }
        )

        assert serializer.is_valid(), serializer.errors

    def test_valid_with_zero_response_time(self, service):
        serializer = LogWriteSerializer(
            data={
                "service": service.id,
                "status": LogStatus.SUCCESS,
                "status_code": 200,
                "response_time_ms": 0,
                "message": "Instant response",
            }
        )

        assert serializer.is_valid(), serializer.errors

    # ---------------------------------------------------------
    # Save()
    # ---------------------------------------------------------

    def test_serializer_creates_log(self, service):
        serializer = LogWriteSerializer(
            data={
                "service": service.id,
                "status": LogStatus.SUCCESS,
                "status_code": 200,
                "response_time_ms": 300,
                "message": "Created",
            }
        )

        assert serializer.is_valid(), serializer.errors

        log = serializer.save()

        assert isinstance(log, Log)
        assert log.service == service
        assert log.status == LogStatus.SUCCESS
        assert log.status_code == 200
        assert log.response_time_ms == 300
        assert log.message == "Created"

    # ---------------------------------------------------------
    # response_time_ms Validation
    # ---------------------------------------------------------

    def test_negative_response_time_fails(self, service):
        serializer = LogWriteSerializer(
            data={
                "service": service.id,
                "status": LogStatus.SUCCESS,
                "response_time_ms": -10,
            }
        )

        assert not serializer.is_valid()
        assert "response_time_ms" in serializer.errors

    def test_none_response_time_is_valid(self, service):
        serializer = LogWriteSerializer(
            data={
                "service": service.id,
                "status": LogStatus.SUCCESS,
                "response_time_ms": None,
            }
        )

        assert serializer.is_valid(), serializer.errors

    # ---------------------------------------------------------
    # status_code Validation
    # ---------------------------------------------------------

    def test_status_code_100_is_valid(self, service):
        serializer = LogWriteSerializer(
            data={
                "service": service.id,
                "status": LogStatus.SUCCESS,
                "status_code": 100,
            }
        )

        assert serializer.is_valid(), serializer.errors

    def test_status_code_599_is_valid(self, service):
        serializer = LogWriteSerializer(
            data={
                "service": service.id,
                "status": LogStatus.SUCCESS,
                "status_code": 599,
            }
        )

        assert serializer.is_valid(), serializer.errors

    def test_status_code_below_100_fails(self, service):
        serializer = LogWriteSerializer(
            data={
                "service": service.id,
                "status": LogStatus.SUCCESS,
                "status_code": 99,
            }
        )

        assert not serializer.is_valid()
        assert "status_code" in serializer.errors

    def test_status_code_above_599_fails(self, service):
        serializer = LogWriteSerializer(
            data={
                "service": service.id,
                "status": LogStatus.SUCCESS,
                "status_code": 600,
            }
        )

        assert not serializer.is_valid()
        assert "status_code" in serializer.errors

    # ---------------------------------------------------------
    # Object Validation
    # ---------------------------------------------------------

    def test_missing_status_fails(self, service):
        serializer = LogWriteSerializer(
            data={
                "service": service.id,
                "message": "Missing status",
            }
        )

        assert not serializer.is_valid()
        assert "non_field_errors" in serializer.errors

    def test_invalid_status_fails(self, service):
        serializer = LogWriteSerializer(
            data={
                "service": service.id,
                "status": "invalid",
                "message": "Wrong status",
            }
        )

        assert not serializer.is_valid()
        assert "status" in serializer.errors

    def test_error_status_with_399_status_code_fails(self, service):
        serializer = LogWriteSerializer(
            data={
                "service": service.id,
                "status": LogStatus.ERROR,
                "status_code": 399,
                "message": "Should fail",
            }
        )

        assert not serializer.is_valid()
        assert "non_field_errors" in serializer.errors

    def test_error_status_with_400_status_code_is_valid(self, service):
        serializer = LogWriteSerializer(
            data={
                "service": service.id,
                "status": LogStatus.ERROR,
                "status_code": 400,
                "message": "Client error",
            }
        )

        assert serializer.is_valid(), serializer.errors

    def test_error_status_with_500_status_code_is_valid(self, service):
        serializer = LogWriteSerializer(
            data={
                "service": service.id,
                "status": LogStatus.ERROR,
                "status_code": 500,
                "message": "Server error",
            }
        )

        assert serializer.is_valid(), serializer.errors

    def test_error_status_without_status_code_is_valid(self, service):
        serializer = LogWriteSerializer(
            data={
                "service": service.id,
                "status": LogStatus.ERROR,
                "message": "No status code",
            }
        )

        assert serializer.is_valid(), serializer.errors

    def test_success_status_with_200_status_code_is_valid(self, service):
        serializer = LogWriteSerializer(
            data={
                "service": service.id,
                "status": LogStatus.SUCCESS,
                "status_code": 200,
                "message": "OK",
            }
        )

        assert serializer.is_valid(), serializer.errors

    def test_warning_status_with_300_status_code_is_valid(self, service):
        serializer = LogWriteSerializer(
            data={
                "service": service.id,
                "status": LogStatus.WARNING,
                "status_code": 302,
                "message": "Redirect",
            }
        )

        assert serializer.is_valid(), serializer.errors

    # ---------------------------------------------------------
    # Message Fallback Behaviour
    # ---------------------------------------------------------

    def test_message_is_preserved_when_given(self, service):
        serializer = LogWriteSerializer(
            data={
                "service": service.id,
                "status": LogStatus.SUCCESS,
                "message": "Custom message",
            }
        )

        assert serializer.is_valid(), serializer.errors
        assert serializer.validated_data["message"] == "Custom message"

    def test_message_fallback_when_blank(self, service):
        serializer = LogWriteSerializer(
            data={
                "service": service.id,
                "status": LogStatus.SUCCESS,
                "message": "",
            }
        )

        assert serializer.is_valid(), serializer.errors
        assert serializer.validated_data["message"] == "success log"

    def test_message_fallback_when_none(self, service):
        serializer = LogWriteSerializer(
            data={
                "service": service.id,
                "status": LogStatus.WARNING,
                "message": None,
            }
        )

        assert serializer.is_valid(), serializer.errors
        assert serializer.validated_data["message"] == "warning log"

    def test_message_fallback_when_missing(self, service):
        serializer = LogWriteSerializer(
            data={
                "service": service.id,
                "status": LogStatus.ERROR,
            }
        )

        assert serializer.is_valid(), serializer.errors
        assert serializer.validated_data["message"] == "error log"

    # ---------------------------------------------------------
    # Save() With Fallback Message
    # ---------------------------------------------------------

    def test_save_uses_generated_fallback_message(self, service):
        serializer = LogWriteSerializer(
            data={
                "service": service.id,
                "status": LogStatus.SUCCESS,
            }
        )

        assert serializer.is_valid(), serializer.errors

        log = serializer.save()

        assert log.message == "success log"

    def test_save_with_none_message_generates_fallback(self, service):
        serializer = LogWriteSerializer(
            data={
                "service": service.id,
                "status": LogStatus.WARNING,
                "message": None,
            }
        )

        assert serializer.is_valid(), serializer.errors

        log = serializer.save()

        assert log.message == "warning log"


@pytest.mark.django_db
class TestLogReadSerializer:
    """
    Unit tests for LogReadSerializer.

    Covers:
    - serialization
    - service_name
    - read_only fields
    - Meta configuration
    """

    @pytest.fixture()
    def log(self, service):
        return LogFactory(
            service=service,
            status=LogStatus.SUCCESS,
            status_code=200,
            response_time_ms=150,
            message="Everything is working",
        )

    # ---------------------------------------------------------
    # Serialization
    # ---------------------------------------------------------

    def test_serializer_returns_correct_fields(self, service, log):
        serializer = LogReadSerializer(log)

        data = serializer.data

        assert data["id"] == log.id
        assert data["service"] == service.id
        assert data["service_name"] == service.name
        assert data["status"] == LogStatus.SUCCESS
        assert data["status_code"] == 200
        assert data["response_time_ms"] == 150
        assert data["message"] == "Everything is working"

    def test_service_name_is_serialized(self, service, log):
        serializer = LogReadSerializer(log)

        assert serializer.data["service_name"] == service.name

    def test_created_at_is_present(self, log):
        serializer = LogReadSerializer(log)

        assert "created_at" in serializer.data
        assert serializer.data["created_at"] is not None

    # ---------------------------------------------------------
    # Read Only Behaviour
    # ---------------------------------------------------------

    def test_serializer_is_read_only(self, log):
        serializer = LogReadSerializer(
            instance=log,
            data={
                "message": "Modified",
            },
            partial=True,
        )

        serializer.is_valid()

        assert serializer.validated_data == {}

    # ---------------------------------------------------------
    # Meta Tests
    # ---------------------------------------------------------

    def test_meta_model(self):
        assert LogReadSerializer.Meta.model == Log

    def test_meta_fields(self):
        expected_fields = [
            "id",
            "service",
            "service_name",
            "status",
            "status_code",
            "response_time_ms",
            "message",
            "created_at",
        ]

        assert list(LogReadSerializer.Meta.fields) == expected_fields

    def test_meta_read_only_fields(self):
        assert (
            list(LogReadSerializer.Meta.read_only_fields)
            == list(LogReadSerializer.Meta.fields)
        )

    # ---------------------------------------------------------
    # Serializer Output Types
    # ---------------------------------------------------------

    def test_service_name_is_string(self, log):
        serializer = LogReadSerializer(log)

        assert isinstance(serializer.data["service_name"], str)

    def test_status_code_is_integer(self, log):
        serializer = LogReadSerializer(log)

        assert serializer.data["status_code"] == 200

    def test_response_time_is_integer(self, log):
        serializer = LogReadSerializer(log)

        assert serializer.data["response_time_ms"] == 150

    def test_message_is_string(self, log):
        serializer = LogReadSerializer(log)

        assert serializer.data["message"] == "Everything is working"

    # ---------------------------------------------------------
    # Nullable Fields
    # ---------------------------------------------------------

    def test_serializer_handles_null_values(self, service):
        log = LogFactory(
            service=service,
            status=LogStatus.WARNING,
            status_code=None,
            response_time_ms=None,
            message="No values",
        )

        serializer = LogReadSerializer(log)

        assert serializer.data["status_code"] is None
        assert serializer.data["response_time_ms"] is None

    # ---------------------------------------------------------
    # Multiple Objects
    # ---------------------------------------------------------

    def test_serializer_many(self, service, log):
        second = LogFactory(
            service=service,
            status=LogStatus.ERROR,
            status_code=500,
            response_time_ms=2500,
            message="Internal error",
        )

        serializer = LogReadSerializer(
            [log, second],
            many=True,
        )

        assert len(serializer.data) == 2
        assert serializer.data[0]["service_name"] == service.name
        assert serializer.data[1]["status"] == LogStatus.ERROR