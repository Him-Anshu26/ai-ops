from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest

from django.db import IntegrityError
from django.utils import timezone

from alerts.models import (
    Alert,
    AlertSeverity,
    AlertStatus,
    AlertType,
)

from monitoring.models import LogStatus

from monitoring.services.alert_service import (
    ALERT_COOLDOWN_SECONDS,
    _build_alert_key,
    _create_or_update_alert,
    _determine_error_severity,
    _get_matching_rules,
    _process_rule,
)

from tests.monitoring.conftest import make_log


@pytest.mark.django_db
class TestBuildAlertKey:
    """
    Tests for _build_alert_key()
    """

    # ---------------------------------------------------------
    # ERROR KEYS
    # ---------------------------------------------------------

    def test_error_key_contains_service_and_status_code(self, service):
        log = make_log(service, status=LogStatus.ERROR, status_code=500)

        key = _build_alert_key(AlertType.ERROR, log)

        assert key == f"error:{service.id}:500"

    def test_error_key_unknown_status_code(self, service):
        log = make_log(service, status=LogStatus.ERROR, status_code=None)

        key = _build_alert_key(AlertType.ERROR, log)

        assert key == f"error:{service.id}:unknown"

    # ---------------------------------------------------------
    # LATENCY KEYS
    # ---------------------------------------------------------

    def test_latency_medium_bucket(self, service):
        log = make_log(service, response_time_ms=1500)

        key = _build_alert_key(AlertType.HIGH_LATENCY, log)

        assert key == f"latency:{service.id}:medium"

    def test_latency_high_bucket(self, service):
        log = make_log(service, response_time_ms=2500)

        key = _build_alert_key(AlertType.HIGH_LATENCY, log)

        assert key == f"latency:{service.id}:high"

    def test_latency_very_high_bucket(self, service):
        log = make_log(service, response_time_ms=6000)

        key = _build_alert_key(AlertType.HIGH_LATENCY, log)

        assert key == f"latency:{service.id}:very_high"

    # ---------------------------------------------------------
    # DOWNTIME
    # ---------------------------------------------------------

    def test_downtime_key(self, service):
        log = make_log(service)

        key = _build_alert_key(AlertType.DOWNTIME, log)

        assert key == f"downtime:{service.id}"

    # ---------------------------------------------------------
    # DEFAULT
    # ---------------------------------------------------------

    def test_default_key(self, service):
        log = make_log(service)

        key = _build_alert_key("custom", log)

        assert key == f"custom:{service.id}"


@pytest.mark.django_db
class TestDetermineSeverity:
    """
    Tests for _determine_error_severity()
    """

    def _log(self, service, code):
        return make_log(
            service,
            status=LogStatus.ERROR,
            status_code=code,
            message="Failure",
        )

    # ---------------------------------------------------------
    # CRITICAL
    # ---------------------------------------------------------

    def test_503_is_critical(self, service):
        severity = _determine_error_severity(self._log(service, 503))
        assert severity == AlertSeverity.CRITICAL

    # ---------------------------------------------------------
    # HIGH
    # ---------------------------------------------------------

    def test_500_is_high(self, service):
        severity = _determine_error_severity(self._log(service, 500))
        assert severity == AlertSeverity.HIGH

    def test_502_is_high(self, service):
        severity = _determine_error_severity(self._log(service, 502))
        assert severity == AlertSeverity.HIGH

    def test_599_is_high(self, service):
        severity = _determine_error_severity(self._log(service, 599))
        assert severity == AlertSeverity.HIGH

    # ---------------------------------------------------------
    # MEDIUM
    # ---------------------------------------------------------

    def test_404_is_medium(self, service):
        severity = _determine_error_severity(self._log(service, 404))
        assert severity == AlertSeverity.MEDIUM

    def test_200_is_medium(self, service):
        severity = _determine_error_severity(self._log(service, 200))
        assert severity == AlertSeverity.MEDIUM

    def test_none_status_code_is_medium(self, service):
        severity = _determine_error_severity(self._log(service, None))
        assert severity == AlertSeverity.MEDIUM


@pytest.mark.django_db
class TestGetMatchingRules:
    """
    Tests for _get_matching_rules()
    """

    # ---------------------------------------------------------
    # NO MATCH
    # ---------------------------------------------------------

    def test_success_log_returns_no_rules(self, service):
        log = make_log(service)

        rules = _get_matching_rules(log)

        assert rules == []

    # ---------------------------------------------------------
    # ERROR
    # ---------------------------------------------------------

    def test_error_status_matches_error_rule(self, service):
        log = make_log(service, status=LogStatus.ERROR, status_code=500)

        rules = _get_matching_rules(log)

        assert len(rules) == 1
        assert rules[0]["type"] == AlertType.ERROR

    def test_status_code_500_matches_error_rule(self, service):
        log = make_log(service, status=LogStatus.SUCCESS, status_code=500)

        rules = _get_matching_rules(log)

        assert len(rules) == 1
        assert rules[0]["type"] == AlertType.ERROR

    # ---------------------------------------------------------
    # LATENCY
    # ---------------------------------------------------------

    def test_high_latency_matches_latency_rule(self, service):
        log = make_log(service, response_time_ms=1501)

        rules = _get_matching_rules(log)

        assert len(rules) == 1
        assert rules[0]["type"] == AlertType.HIGH_LATENCY

    def test_exact_threshold_not_matched(self, service):
        log = make_log(service, response_time_ms=1000)

        rules = _get_matching_rules(log)

        assert rules == []

    # ---------------------------------------------------------
    # BOTH
    # ---------------------------------------------------------

    def test_error_and_latency_match_two_rules(self, service):
        log = make_log(
            service,
            status=LogStatus.ERROR,
            status_code=500,
            response_time_ms=3000,
        )

        rules = _get_matching_rules(log)

        assert len(rules) == 2

        types = {rule["type"] for rule in rules}
        assert AlertType.ERROR in types
        assert AlertType.HIGH_LATENCY in types

    # ---------------------------------------------------------
    # EDGE CASES
    # ---------------------------------------------------------

    def test_none_response_time(self, service):
        log = make_log(service, response_time_ms=None)

        rules = _get_matching_rules(log)

        assert rules == []

    def test_none_status_code(self, service):
        log = make_log(service, status_code=None)

        rules = _get_matching_rules(log)

        assert rules == []


@pytest.mark.django_db
class TestProcessRule:
    """
    Tests for _process_rule()
    """

    def _log(self, service, response_time_ms=2500):
        return make_log(
            service,
            status=LogStatus.ERROR,
            status_code=500,
            response_time_ms=response_time_ms,
            message="Failure",
        )

    # ---------------------------------------------------------
    # ERROR RULE
    # ---------------------------------------------------------

    @patch("monitoring.services.alert_service._create_or_update_alert")
    def test_error_rule_calls_create_update(self, mock_create, service):
        mock_alert = MagicMock()
        mock_alert.id = 1
        mock_create.return_value = mock_alert

        log = self._log(service)
        rule = {"type": AlertType.ERROR}

        alert = _process_rule(log, rule)

        assert alert == mock_alert
        mock_create.assert_called_once()

        kwargs = mock_create.call_args.kwargs
        assert kwargs["alert_type"] == AlertType.ERROR
        assert kwargs["severity"] == AlertSeverity.HIGH
        assert kwargs["service"] == service
        assert kwargs["log"] == log

    # ---------------------------------------------------------
    # LATENCY RULE
    # ---------------------------------------------------------

    @patch("monitoring.services.alert_service._create_or_update_alert")
    def test_latency_rule_calls_create_update(self, mock_create, service):
        mock_alert = MagicMock()
        mock_alert.id = 5
        mock_create.return_value = mock_alert

        log = self._log(service, response_time_ms=2500)
        rule = {"type": AlertType.HIGH_LATENCY}

        alert = _process_rule(log, rule)

        assert alert == mock_alert

        kwargs = mock_create.call_args.kwargs
        assert kwargs["alert_type"] == AlertType.HIGH_LATENCY
        assert kwargs["severity"] == AlertSeverity.MEDIUM

    @patch("monitoring.services.alert_service._create_or_update_alert")
    def test_very_high_latency_is_high_severity(self, mock_create, service):
        mock_alert = MagicMock()
        mock_create.return_value = mock_alert

        log = self._log(service, response_time_ms=5001)

        _process_rule(
            log,
            {"type": AlertType.HIGH_LATENCY},
        )

        kwargs = mock_create.call_args.kwargs
        assert kwargs["severity"] == AlertSeverity.HIGH

    # ---------------------------------------------------------
    # UNKNOWN RULE
    # ---------------------------------------------------------

    @patch("monitoring.services.alert_service._create_or_update_alert")
    def test_unknown_rule_returns_none(self, mock_create, service):
        log = self._log(service)

        alert = _process_rule(
            log,
            {"type": "something-random"},
        )

        assert alert is None
        mock_create.assert_not_called()


@pytest.mark.django_db
class TestCreateOrUpdateAlert:
    def _create_base_log(self, service):
        return make_log(
            service,
            status=LogStatus.ERROR,
            status_code=500,
            message="Boom",
        )

    def test_create_new_alert(self, service):
        log = self._create_base_log(service)

        alert = _create_or_update_alert(
            service=service,
            log=log,
            alert_type=AlertType.ERROR,
            severity=AlertSeverity.HIGH,
            alert_key="error:1:500",
            message="Server error",
        )

        assert alert is not None
        assert Alert.objects.count() == 1

        alert.refresh_from_db()

        assert alert.service == service
        assert alert.log == log
        assert alert.trigger_count == 1
        assert alert.status == AlertStatus.OPEN

    def test_existing_alert_increments_trigger_count(self, service):
        log = self._create_base_log(service)

        alert = Alert.objects.create(
            service=service,
            log=log,
            alert_type=AlertType.ERROR,
            alert_key="error:1:500",
            severity=AlertSeverity.HIGH,
            message="Old",
        )

        alert.last_triggered_at = timezone.now() - timedelta(minutes=5)
        alert.save(update_fields=["last_triggered_at"])

        _create_or_update_alert(
            service=service,
            log=log,
            alert_type=AlertType.ERROR,
            severity=AlertSeverity.CRITICAL,
            alert_key="error:1:500",
            message="Updated",
        )

        alert.refresh_from_db()

        assert alert.trigger_count == 2
        assert alert.severity == AlertSeverity.CRITICAL
        assert alert.log == log

    def test_alert_in_cooldown_not_incremented(self, service):
        log = self._create_base_log(service)

        alert = Alert.objects.create(
            service=service,
            log=log,
            alert_type=AlertType.ERROR,
            alert_key="error:1:500",
            severity=AlertSeverity.HIGH,
            message="Old",
        )

        alert.last_triggered_at = timezone.now()
        alert.save(update_fields=["last_triggered_at"])

        _create_or_update_alert(
            service=service,
            log=log,
            alert_type=AlertType.ERROR,
            severity=AlertSeverity.CRITICAL,
            alert_key="error:1:500",
            message="Again",
        )

        alert.refresh_from_db()

        assert alert.trigger_count == 1

    def test_integrity_error_recovery_existing_alert(self, service):
        log = self._create_base_log(service)

        alert = Alert.objects.create(
            service=service,
            log=log,
            alert_type=AlertType.ERROR,
            alert_key="error:1:500",
            severity=AlertSeverity.HIGH,
            message="Existing",
        )

        alert.last_triggered_at = timezone.now() - timedelta(
            seconds=ALERT_COOLDOWN_SECONDS + 5
        )
        alert.save(update_fields=["last_triggered_at"])

        with patch(
            "monitoring.services.alert_service.Alert.objects.create",
            side_effect=IntegrityError,
        ):
            recovered = _create_or_update_alert(
                service=service,
                log=log,
                alert_type=AlertType.ERROR,
                severity=AlertSeverity.CRITICAL,
                alert_key="error:1:500",
                message="Recovered",
            )

        recovered.refresh_from_db()

        assert recovered.trigger_count == 2

    @patch("monitoring.services.alert_service.Alert.objects.filter")
    @patch("monitoring.services.alert_service.Alert.objects.create")
    def test_integrity_error_recovery_creates_new_alert(
        self, mock_create, mock_filter, service
    ):
        log = self._create_base_log(service)

        mock_create.side_effect = [
            IntegrityError,
            Alert(
                service=service,
                log=log,
                alert_type=AlertType.ERROR,
                alert_key="error",
                severity=AlertSeverity.HIGH,
                message="Recovered",
            ),
        ]

        mock_filter.return_value.first.return_value = None

        alert = _create_or_update_alert(
            service=service,
            log=log,
            alert_type=AlertType.ERROR,
            severity=AlertSeverity.HIGH,
            alert_key="error",
            message="Recovered",
        )

        assert alert is not None