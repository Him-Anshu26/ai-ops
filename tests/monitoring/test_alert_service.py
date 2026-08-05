from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

from alerts.models import (
    Alert,
    AlertSeverity,
    AlertStatus,
    AlertType,
)

from monitoring.models import (
    Log,
    LogStatus,
    Service,
)

from monitoring.services.alert_service import (
    ALERT_COOLDOWN_SECONDS,
    _build_alert_key,
    _create_or_update_alert,
    _determine_error_severity,
    _get_matching_rules,
    _process_rule,
)

User = get_user_model()


class BuildAlertKeyTests(TestCase):
    """
    Tests for _build_alert_key()
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

    def _create_log(
        self,
        status=LogStatus.SUCCESS,
        status_code=200,
        response_time_ms=100,
    ):
        return Log.objects.create(
            service=self.service,
            status=status,
            status_code=status_code,
            response_time_ms=response_time_ms,
            message="Test log",
        )

    # ---------------------------------------------------------
    # ERROR KEYS
    # ---------------------------------------------------------

    def test_error_key_contains_service_and_status_code(self):
        log = self._create_log(
            status=LogStatus.ERROR,
            status_code=500,
        )

        key = _build_alert_key(
            AlertType.ERROR,
            log,
        )

        self.assertEqual(
            key,
            f"error:{self.service.id}:500",
        )

    def test_error_key_unknown_status_code(self):
        log = self._create_log(
            status=LogStatus.ERROR,
            status_code=None,
        )

        key = _build_alert_key(
            AlertType.ERROR,
            log,
        )

        self.assertEqual(
            key,
            f"error:{self.service.id}:unknown",
        )

    # ---------------------------------------------------------
    # LATENCY KEYS
    # ---------------------------------------------------------

    def test_latency_medium_bucket(self):
        log = self._create_log(
            response_time_ms=1500,
        )

        key = _build_alert_key(
            AlertType.HIGH_LATENCY,
            log,
        )

        self.assertEqual(
            key,
            f"latency:{self.service.id}:medium",
        )

    def test_latency_high_bucket(self):
        log = self._create_log(
            response_time_ms=2500,
        )

        key = _build_alert_key(
            AlertType.HIGH_LATENCY,
            log,
        )

        self.assertEqual(
            key,
            f"latency:{self.service.id}:high",
        )

    def test_latency_very_high_bucket(self):
        log = self._create_log(
            response_time_ms=6000,
        )

        key = _build_alert_key(
            AlertType.HIGH_LATENCY,
            log,
        )

        self.assertEqual(
            key,
            f"latency:{self.service.id}:very_high",
        )

    # ---------------------------------------------------------
    # DOWNTIME
    # ---------------------------------------------------------

    def test_downtime_key(self):
        log = self._create_log()

        key = _build_alert_key(
            AlertType.DOWNTIME,
            log,
        )

        self.assertEqual(
            key,
            f"downtime:{self.service.id}",
        )

    # ---------------------------------------------------------
    # DEFAULT
    # ---------------------------------------------------------

    def test_default_key(self):
        log = self._create_log()

        key = _build_alert_key(
            "custom",
            log,
        )

        self.assertEqual(
            key,
            f"custom:{self.service.id}",
        )


class DetermineSeverityTests(TestCase):
    """
    Tests for _determine_error_severity()
    """

    def setUp(self):
        self.user = User.objects.create_user(
            email="owner@example.com",
            password="Password@123",
        )

        self.service = Service.objects.create(
            name="Backend",
            created_by=self.user,
        )

    def _log(self, code):
        return Log.objects.create(
            service=self.service,
            status=LogStatus.ERROR,
            status_code=code,
            message="Failure",
        )

    # ---------------------------------------------------------
    # CRITICAL
    # ---------------------------------------------------------

    def test_503_is_critical(self):
        severity = _determine_error_severity(
            self._log(503)
        )

        self.assertEqual(
            severity,
            AlertSeverity.CRITICAL,
        )

    # ---------------------------------------------------------
    # HIGH
    # ---------------------------------------------------------

    def test_500_is_high(self):
        severity = _determine_error_severity(
            self._log(500)
        )

        self.assertEqual(
            severity,
            AlertSeverity.HIGH,
        )

    def test_502_is_high(self):
        severity = _determine_error_severity(
            self._log(502)
        )

        self.assertEqual(
            severity,
            AlertSeverity.HIGH,
        )

    def test_599_is_high(self):
        severity = _determine_error_severity(
            self._log(599)
        )

        self.assertEqual(
            severity,
            AlertSeverity.HIGH,
        )

    # ---------------------------------------------------------
    # MEDIUM
    # ---------------------------------------------------------

    def test_404_is_medium(self):
        severity = _determine_error_severity(
            self._log(404)
        )

        self.assertEqual(
            severity,
            AlertSeverity.MEDIUM,
        )

    def test_200_is_medium(self):
        severity = _determine_error_severity(
            self._log(200)
        )

        self.assertEqual(
            severity,
            AlertSeverity.MEDIUM,
        )

    def test_none_status_code_is_medium(self):
        severity = _determine_error_severity(
            self._log(None)
        )

        self.assertEqual(
            severity,
            AlertSeverity.MEDIUM,
        )


class GetMatchingRulesTests(TestCase):
    """
    Tests for _get_matching_rules()
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

    def _log(
        self,
        status=LogStatus.SUCCESS,
        status_code=200,
        response_time_ms=100,
    ):
        return Log.objects.create(
            service=self.service,
            status=status,
            status_code=status_code,
            response_time_ms=response_time_ms,
            message="Test",
        )

    # ---------------------------------------------------------
    # NO MATCH
    # ---------------------------------------------------------

    def test_success_log_returns_no_rules(self):
        log = self._log()

        rules = _get_matching_rules(log)

        self.assertEqual(rules, [])

    # ---------------------------------------------------------
    # ERROR
    # ---------------------------------------------------------

    def test_error_status_matches_error_rule(self):
        log = self._log(
            status=LogStatus.ERROR,
            status_code=500,
        )

        rules = _get_matching_rules(log)

        self.assertEqual(len(rules), 1)
        self.assertEqual(
            rules[0]["type"],
            AlertType.ERROR,
        )

    def test_status_code_500_matches_error_rule(self):
        log = self._log(
            status=LogStatus.SUCCESS,
            status_code=500,
        )

        rules = _get_matching_rules(log)

        self.assertEqual(len(rules), 1)
        self.assertEqual(
            rules[0]["type"],
            AlertType.ERROR,
        )

    # ---------------------------------------------------------
    # LATENCY
    # ---------------------------------------------------------

    def test_high_latency_matches_latency_rule(self):
        log = self._log(
            response_time_ms=1501,
        )

        rules = _get_matching_rules(log)

        self.assertEqual(len(rules), 1)
        self.assertEqual(
            rules[0]["type"],
            AlertType.HIGH_LATENCY,
        )

    def test_exact_threshold_not_matched(self):
        log = self._log(
            response_time_ms=1000,
        )

        rules = _get_matching_rules(log)

        self.assertEqual(rules, [])

    # ---------------------------------------------------------
    # BOTH
    # ---------------------------------------------------------

    def test_error_and_latency_match_two_rules(self):
        log = self._log(
            status=LogStatus.ERROR,
            status_code=500,
            response_time_ms=3000,
        )

        rules = _get_matching_rules(log)

        self.assertEqual(len(rules), 2)

        types = {rule["type"] for rule in rules}

        self.assertIn(AlertType.ERROR, types)
        self.assertIn(AlertType.HIGH_LATENCY, types)

    # ---------------------------------------------------------
    # EDGE CASES
    # ---------------------------------------------------------

    def test_none_response_time(self):
        log = self._log(
            response_time_ms=None,
        )

        rules = _get_matching_rules(log)

        self.assertEqual(rules, [])

    def test_none_status_code(self):
        log = self._log(
            status_code=None,
        )

        rules = _get_matching_rules(log)

        self.assertEqual(rules, [])


class ProcessRuleTests(TestCase):
    """
    Tests for _process_rule()
    """

    def setUp(self):
        self.user = User.objects.create_user(
            email="owner@example.com",
            password="Password@123",
        )

        self.service = Service.objects.create(
            name="Backend",
            created_by=self.user,
        )

    def _log(
        self,
        status=LogStatus.ERROR,
        status_code=500,
        response_time_ms=2500,
    ):
        return Log.objects.create(
            service=self.service,
            status=status,
            status_code=status_code,
            response_time_ms=response_time_ms,
            message="Failure",
        )

    # ---------------------------------------------------------
    # ERROR RULE
    # ---------------------------------------------------------

    @patch("monitoring.services.alert_service._create_or_update_alert")
    def test_error_rule_calls_create_update(
        self,
        mock_create,
    ):
        mock_alert = MagicMock()
        mock_alert.id = 1

        mock_create.return_value = mock_alert

        log = self._log()

        rule = {
            "type": AlertType.ERROR,
        }

        alert = _process_rule(
            log,
            rule,
        )

        self.assertEqual(alert, mock_alert)

        mock_create.assert_called_once()

        kwargs = mock_create.call_args.kwargs

        self.assertEqual(
            kwargs["alert_type"],
            AlertType.ERROR,
        )

        self.assertEqual(
            kwargs["severity"],
            AlertSeverity.HIGH,
        )

        self.assertEqual(
            kwargs["service"],
            self.service,
        )

        self.assertEqual(
            kwargs["log"],
            log,
        )

    # ---------------------------------------------------------
    # LATENCY RULE
    # ---------------------------------------------------------

    @patch("monitoring.services.alert_service._create_or_update_alert")
    def test_latency_rule_calls_create_update(
        self,
        mock_create,
    ):
        mock_alert = MagicMock()
        mock_alert.id = 5

        mock_create.return_value = mock_alert

        log = self._log(
            response_time_ms=2500,
        )

        rule = {
            "type": AlertType.HIGH_LATENCY,
        }

        alert = _process_rule(
            log,
            rule,
        )

        self.assertEqual(alert, mock_alert)

        kwargs = mock_create.call_args.kwargs

        self.assertEqual(
            kwargs["alert_type"],
            AlertType.HIGH_LATENCY,
        )

        self.assertEqual(
            kwargs["severity"],
            AlertSeverity.MEDIUM,
        )

    @patch("monitoring.services.alert_service._create_or_update_alert")
    def test_very_high_latency_is_high_severity(
        self,
        mock_create,
    ):
        mock_alert = MagicMock()
        mock_create.return_value = mock_alert

        log = self._log(
            response_time_ms=5001,
        )

        _process_rule(
            log,
            {
                "type": AlertType.HIGH_LATENCY,
            },
        )

        kwargs = mock_create.call_args.kwargs

        self.assertEqual(
            kwargs["severity"],
            AlertSeverity.HIGH,
        )

    # ---------------------------------------------------------
    # UNKNOWN RULE
    # ---------------------------------------------------------

    @patch("monitoring.services.alert_service._create_or_update_alert")
    def test_unknown_rule_returns_none(
        self,
        mock_create,
    ):
        log = self._log()

        alert = _process_rule(
            log,
            {
                "type": "something-random",
            },
        )

        self.assertIsNone(alert)

        mock_create.assert_not_called()


class CreateOrUpdateAlertTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email="owner@example.com",
            password="Password@123",
        )

        self.service = Service.objects.create(
            name="API",
            created_by=self.user,
        )

        self.log = Log.objects.create(
            service=self.service,
            status=LogStatus.ERROR,
            status_code=500,
            message="Boom",
        )

    def test_create_new_alert(self):
        alert = _create_or_update_alert(
            service=self.service,
            log=self.log,
            alert_type=AlertType.ERROR,
            severity=AlertSeverity.HIGH,
            alert_key="error:1:500",
            message="Server error",
        )

        self.assertIsNotNone(alert)
        self.assertEqual(Alert.objects.count(), 1)

        alert.refresh_from_db()

        self.assertEqual(alert.service, self.service)
        self.assertEqual(alert.log, self.log)
        self.assertEqual(alert.trigger_count, 1)
        self.assertEqual(alert.status, AlertStatus.OPEN)

    def test_existing_alert_increments_trigger_count(self):
        alert = Alert.objects.create(
            service=self.service,
            log=self.log,
            alert_type=AlertType.ERROR,
            alert_key="error:1:500",
            severity=AlertSeverity.HIGH,
            message="Old",
        )

        alert.last_triggered_at = timezone.now() - timedelta(minutes=5)
        alert.save(update_fields=["last_triggered_at"])

        _create_or_update_alert(
            service=self.service,
            log=self.log,
            alert_type=AlertType.ERROR,
            severity=AlertSeverity.CRITICAL,
            alert_key="error:1:500",
            message="Updated",
        )

        alert.refresh_from_db()

        self.assertEqual(alert.trigger_count, 2)
        self.assertEqual(alert.severity, AlertSeverity.CRITICAL)
        self.assertEqual(alert.log, self.log)

    def test_alert_in_cooldown_not_incremented(self):
        alert = Alert.objects.create(
            service=self.service,
            log=self.log,
            alert_type=AlertType.ERROR,
            alert_key="error:1:500",
            severity=AlertSeverity.HIGH,
            message="Old",
        )

        alert.last_triggered_at = timezone.now()
        alert.save(update_fields=["last_triggered_at"])

        _create_or_update_alert(
            service=self.service,
            log=self.log,
            alert_type=AlertType.ERROR,
            severity=AlertSeverity.CRITICAL,
            alert_key="error:1:500",
            message="Again",
        )

        alert.refresh_from_db()

        self.assertEqual(alert.trigger_count, 1)


    def test_integrity_error_recovery_existing_alert(self):

        alert = Alert.objects.create(
            service=self.service,
            log=self.log,
            alert_type=AlertType.ERROR,
            alert_key="error:1:500",
            severity=AlertSeverity.HIGH,
            message="Existing",
        )

        alert.last_triggered_at = (
            timezone.now()
            - timedelta(seconds=ALERT_COOLDOWN_SECONDS + 5)
        )
        alert.save(update_fields=["last_triggered_at"])

        with patch(
            "monitoring.services.alert_service.Alert.objects.create",
            side_effect=IntegrityError,
        ):

            recovered = _create_or_update_alert(
                service=self.service,
                log=self.log,
                alert_type=AlertType.ERROR,
                severity=AlertSeverity.CRITICAL,
                alert_key="error:1:500",
                message="Recovered",
            )

        recovered.refresh_from_db()

        self.assertEqual(recovered.trigger_count, 2)

    @patch(
        "monitoring.services.alert_service.Alert.objects.filter"
    )
    @patch(
        "monitoring.services.alert_service.Alert.objects.create"
    )
    def test_integrity_error_recovery_creates_new_alert(
        self,
        mock_create,
        mock_filter,
    ):
        mock_create.side_effect = [
            IntegrityError,
            Alert(
                service=self.service,
                log=self.log,
                alert_type=AlertType.ERROR,
                alert_key="error",
                severity=AlertSeverity.HIGH,
                message="Recovered",
            ),
        ]

        mock_filter.return_value.first.return_value = None

        alert = _create_or_update_alert(
            service=self.service,
            log=self.log,
            alert_type=AlertType.ERROR,
            severity=AlertSeverity.HIGH,
            alert_key="error",
            message="Recovered",
        )

        self.assertIsNotNone(alert)