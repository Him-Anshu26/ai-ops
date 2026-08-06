from unittest.mock import patch

from django.conf import settings

from django.test import TestCase

from alerts.models import (
    AlertSeverity,
    AlertStatus,
    AlertType,
)
from alerts.services.email_service import (
    _build_body,
    _build_subject,
)

from tests.factories import AlertFactory

from alerts.services.email_service import send_alert_email


# ============================================================
# Subject Builder Tests
# ============================================================

class EmailSubjectTests(TestCase):
    """
    Unit tests for _build_subject().
    """

    def test_build_subject_returns_expected_format(self):
        alert = AlertFactory(
            severity=AlertSeverity.CRITICAL,
            alert_type=AlertType.ERROR,
        )

        subject = _build_subject(alert)

        expected = (
            f"[CRITICAL] "
            f"Error - "
            f"{alert.service.name}"
        )

        self.assertEqual(
            subject,
            expected,
        )

    def test_subject_contains_uppercase_severity(self):
        alert = AlertFactory(
            severity=AlertSeverity.HIGH,
        )

        subject = _build_subject(alert)

        self.assertIn(
            "[HIGH]",
            subject,
        )

    def test_subject_contains_alert_type_display(self):
        alert = AlertFactory(
            alert_type=AlertType.DOWNTIME,
        )

        subject = _build_subject(alert)

        self.assertIn(
            "Downtime",
            subject,
        )

    def test_subject_contains_service_name(self):
        alert = AlertFactory()

        subject = _build_subject(alert)

        self.assertIn(
            alert.service.name,
            subject,
        )

    def test_subject_for_high_latency_alert(self):
        alert = AlertFactory(
            alert_type=AlertType.HIGH_LATENCY,
            severity=AlertSeverity.MEDIUM,
        )

        subject = _build_subject(alert)

        self.assertEqual(
            subject,
            f"[MEDIUM] High Latency - {alert.service.name}",
        )

    def test_subject_has_three_sections(self):
        alert = AlertFactory()

        subject = _build_subject(alert)

        self.assertEqual(
            subject.count("-"),
            1,
        )

        self.assertTrue(
            subject.startswith("["),
        )

        self.assertTrue(
            "]" in subject,
        )


# ============================================================
# Body Builder Tests
# ============================================================

class EmailBodyTests(TestCase):
    """
    Unit tests for _build_body().
    """

    def test_body_contains_alert_title(self):
        alert = AlertFactory()

        body = _build_body(alert)

        self.assertIn(
            "AI Ops Monitoring Alert",
            body,
        )

    def test_body_contains_alert_id(self):
        alert = AlertFactory()

        body = _build_body(alert)

        self.assertIn(
            str(alert.id),
            body,
        )

    def test_body_contains_service_name(self):
        alert = AlertFactory()

        body = _build_body(alert)

        self.assertIn(
            alert.service.name,
            body,
        )

    def test_body_contains_alert_type_display(self):
        alert = AlertFactory(
            alert_type=AlertType.DOWNTIME,
        )

        body = _build_body(alert)

        self.assertIn(
            "Downtime",
            body,
        )

    def test_body_contains_severity_display(self):
        alert = AlertFactory(
            severity=AlertSeverity.CRITICAL,
        )

        body = _build_body(alert)

        self.assertIn(
            "Critical",
            body,
        )

    def test_body_contains_status_display(self):
        alert = AlertFactory(
            status=AlertStatus.ACKNOWLEDGED,
        )

        body = _build_body(alert)

        self.assertIn(
            "Acknowledged",
            body,
        )

    def test_body_contains_message(self):
        alert = AlertFactory(
            message="Database connection failed.",
        )

        body = _build_body(alert)

        self.assertIn(
            "Database connection failed.",
            body,
        )

    def test_body_contains_trigger_count(self):
        alert = AlertFactory(
            trigger_count=5,
        )

        body = _build_body(alert)

        self.assertIn(
            "5",
            body,
        )

    def test_body_contains_created_at(self):
        alert = AlertFactory()

        body = _build_body(alert)

        self.assertIn(
            str(alert.created_at),
            body,
        )

    def test_body_contains_last_triggered_at(self):
        alert = AlertFactory()

        body = _build_body(alert)

        self.assertIn(
            str(alert.last_triggered_at),
            body,
        )

    def test_body_is_stripped(self):
        alert = AlertFactory()

        body = _build_body(alert)

        self.assertEqual(
            body,
            body.strip(),
        )

    def test_body_contains_all_expected_sections(self):
        alert = AlertFactory()

        body = _build_body(alert)

        expected_sections = [
            "Alert ID",
            "Service",
            "Alert Type",
            "Severity",
            "Status",
            "Message",
            "Trigger Count",
            "Created At",
            "Last Triggered",
        ]

        for section in expected_sections:
            with self.subTest(section=section):
                self.assertIn(
                    section,
                    body,
                )

    def test_body_supports_multiline_message(self):
        alert = AlertFactory(
            message=(
                "Database error\n"
                "Retry failed\n"
                "Escalated"
            ),
        )

        body = _build_body(alert)

        self.assertIn(
            "Database error",
            body,
        )

        self.assertIn(
            "Retry failed",
            body,
        )

        self.assertIn(
            "Escalated",
            body,
        )

    def test_body_handles_empty_message(self):
        alert = AlertFactory(
            message="",
        )

        body = _build_body(alert)

        self.assertIn(
            "Message:",
            body,
        )

    def test_body_handles_zero_trigger_count(self):
        alert = AlertFactory(
            trigger_count=0,
        )

        body = _build_body(alert)

        self.assertIn(
            "0",
            body,
        )




class SendAlertEmailSuccessTests(TestCase):
    """
    Unit tests covering successful email delivery.
    """

    @patch("alerts.services.email_service.logger")
    @patch("alerts.services.email_service.send_email")
    def test_returns_true_when_email_sent(
        self,
        mock_send_email,
        mock_logger,
    ):
        alert = AlertFactory()

        result = send_alert_email(alert)

        self.assertTrue(result)

        mock_send_email.assert_called_once()

    @patch("alerts.services.email_service.logger")
    @patch("alerts.services.email_service.send_email")
    def test_send_email_called_once(
        self,
        mock_send_email,
        mock_logger,
    ):
        alert = AlertFactory()

        send_alert_email(alert)

        mock_send_email.assert_called_once()

    @patch("alerts.services.email_service.logger")
    @patch("alerts.services.email_service.send_email")
    def test_send_email_receives_correct_subject(
        self,
        mock_send_email,
        mock_logger,
    ):
        alert = AlertFactory()

        expected_subject = _build_subject(alert)

        send_alert_email(alert)

        self.assertEqual(
            mock_send_email.call_args.kwargs["subject"],
            expected_subject,
        )

    @patch("alerts.services.email_service.logger")
    @patch("alerts.services.email_service.send_email")
    def test_send_email_receives_correct_body(
        self,
        mock_send_email,
        mock_logger,
    ):
        alert = AlertFactory()

        expected_body = _build_body(alert)

        send_alert_email(alert)

        self.assertEqual(
            mock_send_email.call_args.kwargs["message"],
            expected_body,
        )

    @patch("alerts.services.email_service.logger")
    @patch("alerts.services.email_service.send_email")
    def test_send_email_receives_recipient_list(
        self,
        mock_send_email,
        mock_logger,
    ):
        alert = AlertFactory()

        send_alert_email(alert)

        self.assertEqual(
            mock_send_email.call_args.kwargs["recipient_list"],
            settings.ALERT_EMAIL_RECIPIENTS,
        )

    @patch("alerts.services.email_service.logger")
    @patch("alerts.services.email_service.send_email")
    def test_logs_before_sending_email(
        self,
        mock_send_email,
        mock_logger,
    ):
        alert = AlertFactory()

        send_alert_email(alert)

        mock_logger.info.assert_any_call(
            "Preparing email notification for alert %s",
            alert.id,
        )

    @patch("alerts.services.email_service.logger")
    @patch("alerts.services.email_service.send_email")
    def test_logs_success_after_email_sent(
        self,
        mock_send_email,
        mock_logger,
    ):
        alert = AlertFactory()

        send_alert_email(alert)

        mock_logger.info.assert_any_call(
            "Email notification sent successfully for alert %s",
            alert.id,
        )

    @patch("alerts.services.email_service.logger")
    @patch("alerts.services.email_service.send_email")
    @patch("alerts.services.email_service._build_subject")
    @patch("alerts.services.email_service._build_body")
    def test_subject_and_body_builders_called_once(
        self,
        mock_build_body,
        mock_build_subject,
        mock_send_email,
        mock_logger,
    ):
        alert = AlertFactory()

        mock_build_subject.return_value = "Subject"

        mock_build_body.return_value = "Body"

        send_alert_email(alert)

        mock_build_subject.assert_called_once_with(
            alert,
        )

        mock_build_body.assert_called_once_with(
            alert,
        )

    @patch("alerts.services.email_service.logger")
    @patch("alerts.services.email_service.send_email")
    @patch("alerts.services.email_service._build_subject")
    @patch("alerts.services.email_service._build_body")
    def test_send_email_uses_builder_results(
        self,
        mock_build_body,
        mock_build_subject,
        mock_send_email,
        mock_logger,
    ):
        alert = AlertFactory()

        mock_build_subject.return_value = "My Subject"

        mock_build_body.return_value = "My Body"

        send_alert_email(alert)

        mock_send_email.assert_called_once_with(
            subject="My Subject",
            message="My Body",
            recipient_list=settings.ALERT_EMAIL_RECIPIENTS,
        )

    @patch("alerts.services.email_service.logger")
    @patch("alerts.services.email_service.send_email")
    def test_logger_info_called_twice(
        self,
        mock_send_email,
        mock_logger,
    ):
        alert = AlertFactory()

        send_alert_email(alert)

        self.assertEqual(
            mock_logger.info.call_count,
            2,
        )

    @patch("alerts.services.email_service.logger")
    @patch("alerts.services.email_service.send_email")
    def test_exception_logger_not_called_on_success(
        self,
        mock_send_email,
        mock_logger,
    ):
        alert = AlertFactory()

        send_alert_email(alert)

        mock_logger.exception.assert_not_called()

    @patch("alerts.services.email_service.logger")
    @patch("alerts.services.email_service.send_email")
    def test_email_service_accepts_all_alert_types(
        self,
        mock_send_email,
        mock_logger,
    ):
        for alert_type in AlertType.values:

            with self.subTest(alert_type=alert_type):

                alert = AlertFactory(
                    alert_type=alert_type,
                )

                result = send_alert_email(alert)

                self.assertTrue(result)

        self.assertEqual(
            mock_send_email.call_count,
            len(AlertType.values),
        )

    @patch("alerts.services.email_service.logger")
    @patch("alerts.services.email_service.send_email")
    def test_email_service_accepts_all_severities(
        self,
        mock_send_email,
        mock_logger,
    ):
        for severity in AlertSeverity.values:

            with self.subTest(severity=severity):

                alert = AlertFactory(
                    severity=severity,
                )

                result = send_alert_email(alert)

                self.assertTrue(result)

        self.assertEqual(
            mock_send_email.call_count,
            len(AlertSeverity.values),
        )




# ============================================================
# send_alert_email() Failure Tests
# ============================================================


class SendAlertEmailFailureTests(TestCase):
    """
    Unit tests covering failure scenarios.
    """

    @patch("alerts.services.email_service.logger")
    @patch("alerts.services.email_service.send_email")
    def test_exception_is_reraised(
        self,
        mock_send_email,
        mock_logger,
    ):
        alert = AlertFactory()

        mock_send_email.side_effect = RuntimeError(
            "SMTP unavailable"
        )

        with self.assertRaises(RuntimeError):
            send_alert_email(alert)

    @patch("alerts.services.email_service.logger")
    @patch("alerts.services.email_service.send_email")
    def test_logs_exception_when_send_fails(
        self,
        mock_send_email,
        mock_logger,
    ):
        alert = AlertFactory()

        mock_send_email.side_effect = Exception(
            "Mail server failed"
        )

        with self.assertRaises(Exception):
            send_alert_email(alert)

        mock_logger.exception.assert_called_once_with(
            "Failed to send email notification for alert %s",
            alert.id,
        )

    @patch("alerts.services.email_service.logger")
    @patch("alerts.services.email_service.send_email")
    def test_success_log_not_written_when_email_fails(
        self,
        mock_send_email,
        mock_logger,
    ):
        alert = AlertFactory()

        mock_send_email.side_effect = Exception()

        with self.assertRaises(Exception):
            send_alert_email(alert)

        success_call = (
            "Email notification sent successfully for alert %s",
            alert.id,
        )

        self.assertNotIn(
            success_call,
            mock_logger.info.call_args_list,
        )

    @patch("alerts.services.email_service.logger")
    @patch("alerts.services.email_service.send_email")
    def test_preparing_log_still_written_when_email_fails(
        self,
        mock_send_email,
        mock_logger,
    ):
        alert = AlertFactory()

        mock_send_email.side_effect = Exception()

        with self.assertRaises(Exception):
            send_alert_email(alert)

        mock_logger.info.assert_any_call(
            "Preparing email notification for alert %s",
            alert.id,
        )

    @patch("alerts.services.email_service.logger")
    @patch("alerts.services.email_service.send_email")
    def test_send_email_called_once_before_failure(
        self,
        mock_send_email,
        mock_logger,
    ):
        alert = AlertFactory()

        mock_send_email.side_effect = Exception()

        with self.assertRaises(Exception):
            send_alert_email(alert)

        mock_send_email.assert_called_once()

    @patch("alerts.services.email_service.logger")
    @patch("alerts.services.email_service.send_email")
    @patch("alerts.services.email_service._build_subject")
    @patch("alerts.services.email_service._build_body")
    def test_builders_called_even_when_send_fails(
        self,
        mock_build_body,
        mock_build_subject,
        mock_send_email,
        mock_logger,
    ):
        alert = AlertFactory()

        mock_build_subject.return_value = "Subject"
        mock_build_body.return_value = "Body"

        mock_send_email.side_effect = Exception()

        with self.assertRaises(Exception):
            send_alert_email(alert)

        mock_build_subject.assert_called_once_with(
            alert,
        )

        mock_build_body.assert_called_once_with(
            alert,
        )


# ============================================================
# Edge Case Tests
# ============================================================


class EmailServiceEdgeCaseTests(TestCase):
    """
    Miscellaneous edge cases.
    """

    @patch("alerts.services.email_service.send_email")
    @patch("alerts.services.email_service.logger")
    def test_handles_empty_message(
        self,
        mock_logger,
        mock_send_email,
    ):
        alert = AlertFactory(
            message="",
        )

        result = send_alert_email(alert)

        self.assertTrue(result)

    @patch("alerts.services.email_service.send_email")
    @patch("alerts.services.email_service.logger")
    def test_handles_zero_trigger_count(
        self,
        mock_logger,
        mock_send_email,
    ):
        alert = AlertFactory(
            trigger_count=0,
        )

        result = send_alert_email(alert)

        self.assertTrue(result)

    @patch("alerts.services.email_service.send_email")
    @patch("alerts.services.email_service.logger")
    def test_handles_none_last_triggered_at(
        self,
        mock_logger,
        mock_send_email,
    ):
        alert = AlertFactory()

        alert.last_triggered_at = None

        result = send_alert_email(alert)

        self.assertTrue(result)

    @patch("alerts.services.email_service.send_email")
    @patch("alerts.services.email_service.logger")
    def test_handles_long_message(
        self,
        mock_logger,
        mock_send_email,
    ):
        alert = AlertFactory(
            message="A" * 255,
        )

        result = send_alert_email(alert)

        self.assertTrue(result)

    @patch("alerts.services.email_service.send_email")
    @patch("alerts.services.email_service.logger")
    def test_handles_unicode_message(
        self,
        mock_logger,
        mock_send_email,
    ):
        alert = AlertFactory(
            message="🚨 Database failure — सर्वर डाउन",
        )

        result = send_alert_email(alert)

        self.assertTrue(result)

    @patch("alerts.services.email_service.send_email")
    @patch("alerts.services.email_service.logger")
    def test_handles_multiline_message(
        self,
        mock_logger,
        mock_send_email,
    ):
        alert = AlertFactory(
            message=(
                "Line 1\n"
                "Line 2\n"
                "Line 3"
            ),
        )

        result = send_alert_email(alert)

        self.assertTrue(result)