from unittest.mock import patch
import pytest
from django.test import override_settings

from alerts.models import (
    AlertSeverity,
    AlertType,
)
from alerts.services.notification_service import (
    dispatch_alert_notifications,
)
from tests.factories import AlertFactory


# ============================================================
# Email Notification Tests
# ============================================================


@pytest.mark.django_db
class TestNotificationEmail:
    """
    Tests covering the email notification workflow.
    """

    @override_settings(
        EMAIL_NOTIFICATIONS_ENABLED=True,
        SLACK_NOTIFICATIONS_ENABLED=False,
    )
    @patch("alerts.services.notification_service.logger")
    @patch("alerts.services.notification_service.send_alert_email")
    def test_email_sent_when_enabled(
        self,
        mock_send_email,
        mock_logger,
    ):
        alert = AlertFactory()
        dispatch_alert_notifications(alert)
        mock_send_email.assert_called_once_with(alert)

    @override_settings(
        EMAIL_NOTIFICATIONS_ENABLED=False,
        SLACK_NOTIFICATIONS_ENABLED=False,
    )
    @patch("alerts.services.notification_service.logger")
    @patch("alerts.services.notification_service.send_alert_email")
    def test_email_not_sent_when_disabled(
        self,
        mock_send_email,
        mock_logger,
    ):
        alert = AlertFactory()
        dispatch_alert_notifications(alert)
        mock_send_email.assert_not_called()

    @override_settings(
        EMAIL_NOTIFICATIONS_ENABLED=True,
        SLACK_NOTIFICATIONS_ENABLED=False,
    )
    @patch("alerts.services.notification_service.logger")
    @patch("alerts.services.notification_service.send_alert_email")
    def test_email_dispatch_log_written(
        self,
        mock_send_email,
        mock_logger,
    ):
        alert = AlertFactory()
        dispatch_alert_notifications(alert)
        mock_logger.info.assert_any_call(
            "Dispatching email notification for alert %s",
            alert.id,
        )

    @override_settings(
        EMAIL_NOTIFICATIONS_ENABLED=True,
        SLACK_NOTIFICATIONS_ENABLED=False,
    )
    @patch("alerts.services.notification_service.logger")
    @patch("alerts.services.notification_service.send_alert_email")
    def test_email_success_log_written(
        self,
        mock_send_email,
        mock_logger,
    ):
        alert = AlertFactory()
        dispatch_alert_notifications(alert)
        mock_logger.info.assert_any_call(
            "Email notification dispatched for alert %s",
            alert.id,
        )

    @override_settings(
        EMAIL_NOTIFICATIONS_ENABLED=False,
        SLACK_NOTIFICATIONS_ENABLED=False,
    )
    @patch("alerts.services.notification_service.logger")
    @patch("alerts.services.notification_service.send_alert_email")
    def test_disabled_email_log_written(
        self,
        mock_send_email,
        mock_logger,
    ):
        alert = AlertFactory()
        dispatch_alert_notifications(alert)
        mock_logger.info.assert_any_call("Email notifications are disabled.")

    @override_settings(
        EMAIL_NOTIFICATIONS_ENABLED=True,
        SLACK_NOTIFICATIONS_ENABLED=False,
    )
    @patch("alerts.services.notification_service.logger")
    @patch("alerts.services.notification_service.send_alert_email")
    def test_email_service_called_once(
        self,
        mock_send_email,
        mock_logger,
    ):
        alert = AlertFactory()
        dispatch_alert_notifications(alert)
        assert mock_send_email.call_count == 1

    @override_settings(
        EMAIL_NOTIFICATIONS_ENABLED=True,
        SLACK_NOTIFICATIONS_ENABLED=False,
    )
    @patch("alerts.services.notification_service.logger")
    @patch("alerts.services.notification_service.send_alert_email")
    def test_email_receives_same_alert_instance(
        self,
        mock_send_email,
        mock_logger,
    ):
        alert = AlertFactory()
        dispatch_alert_notifications(alert)
        sent_alert = mock_send_email.call_args.args[0]
        assert sent_alert is alert


# ============================================================
# Slack Notification Tests
# ============================================================


@pytest.mark.django_db
class TestNotificationSlack:
    """
    Tests covering the Slack notification workflow.
    """

    @override_settings(
        EMAIL_NOTIFICATIONS_ENABLED=False,
        SLACK_NOTIFICATIONS_ENABLED=True,
    )
    @patch("alerts.services.notification_service.logger")
    @patch("alerts.services.notification_service.send_slack_notification")
    def test_slack_sent_when_enabled(
        self,
        mock_send_slack,
        mock_logger,
    ):
        alert = AlertFactory()
        dispatch_alert_notifications(alert)
        mock_send_slack.assert_called_once_with(alert)

    @override_settings(
        EMAIL_NOTIFICATIONS_ENABLED=False,
        SLACK_NOTIFICATIONS_ENABLED=False,
    )
    @patch("alerts.services.notification_service.logger")
    @patch("alerts.services.notification_service.send_slack_notification")
    def test_slack_not_sent_when_disabled(
        self,
        mock_send_slack,
        mock_logger,
    ):
        alert = AlertFactory()
        dispatch_alert_notifications(alert)
        mock_send_slack.assert_not_called()

    @override_settings(
        EMAIL_NOTIFICATIONS_ENABLED=False,
        SLACK_NOTIFICATIONS_ENABLED=True,
    )
    @patch("alerts.services.notification_service.logger")
    @patch("alerts.services.notification_service.send_slack_notification")
    def test_slack_dispatch_log_written(
        self,
        mock_send_slack,
        mock_logger,
    ):
        alert = AlertFactory()
        dispatch_alert_notifications(alert)
        mock_logger.info.assert_any_call(
            "Dispatching Slack notification for alert %s",
            alert.id,
        )

    @override_settings(
        EMAIL_NOTIFICATIONS_ENABLED=False,
        SLACK_NOTIFICATIONS_ENABLED=True,
    )
    @patch("alerts.services.notification_service.logger")
    @patch("alerts.services.notification_service.send_slack_notification")
    def test_slack_success_log_written(
        self,
        mock_send_slack,
        mock_logger,
    ):
        alert = AlertFactory()
        dispatch_alert_notifications(alert)
        mock_logger.info.assert_any_call(
            "Slack notification dispatched for alert %s",
            alert.id,
        )

    @override_settings(
        EMAIL_NOTIFICATIONS_ENABLED=False,
        SLACK_NOTIFICATIONS_ENABLED=False,
    )
    @patch("alerts.services.notification_service.logger")
    @patch("alerts.services.notification_service.send_slack_notification")
    def test_disabled_slack_log_written(
        self,
        mock_send_slack,
        mock_logger,
    ):
        alert = AlertFactory()
        dispatch_alert_notifications(alert)
        mock_logger.info.assert_any_call("Slack notifications are disabled.")

    @override_settings(
        EMAIL_NOTIFICATIONS_ENABLED=False,
        SLACK_NOTIFICATIONS_ENABLED=True,
    )
    @patch("alerts.services.notification_service.logger")
    @patch("alerts.services.notification_service.send_slack_notification")
    def test_slack_service_called_once(
        self,
        mock_send_slack,
        mock_logger,
    ):
        alert = AlertFactory()
        dispatch_alert_notifications(alert)
        assert mock_send_slack.call_count == 1

    @override_settings(
        EMAIL_NOTIFICATIONS_ENABLED=False,
        SLACK_NOTIFICATIONS_ENABLED=True,
    )
    @patch("alerts.services.notification_service.logger")
    @patch("alerts.services.notification_service.send_slack_notification")
    def test_slack_receives_same_alert_instance(
        self,
        mock_send_slack,
        mock_logger,
    ):
        alert = AlertFactory()
        dispatch_alert_notifications(alert)
        sent_alert = mock_send_slack.call_args.args[0]
        assert sent_alert is alert


# ============================================================
# Email Failure
# ============================================================


@pytest.mark.django_db
class TestNotificationEmailFailure:
    """
    Email failures should never stop notification dispatch.
    """

    @override_settings(
        EMAIL_NOTIFICATIONS_ENABLED=True,
        SLACK_NOTIFICATIONS_ENABLED=False,
    )
    @patch("alerts.services.notification_service.logger")
    @patch("alerts.services.notification_service.send_alert_email")
    def test_email_failure_logged(
        self,
        mock_send_email,
        mock_logger,
    ):
        alert = AlertFactory()
        mock_send_email.side_effect = Exception("SMTP failure")

        dispatch_alert_notifications(alert)

        mock_logger.exception.assert_called_once_with(
            "Failed to send email notification for alert %s",
            alert.id,
        )

    @override_settings(
        EMAIL_NOTIFICATIONS_ENABLED=True,
        SLACK_NOTIFICATIONS_ENABLED=False,
    )
    @patch("alerts.services.notification_service.logger")
    @patch("alerts.services.notification_service.send_alert_email")
    def test_email_failure_does_not_raise(
        self,
        mock_send_email,
        mock_logger,
    ):
        alert = AlertFactory()
        mock_send_email.side_effect = RuntimeError()

        dispatch_alert_notifications(alert)

    @override_settings(
        EMAIL_NOTIFICATIONS_ENABLED=True,
        SLACK_NOTIFICATIONS_ENABLED=False,
    )
    @patch("alerts.services.notification_service.logger")
    @patch("alerts.services.notification_service.send_alert_email")
    def test_finish_log_written_after_email_failure(
        self,
        mock_send_email,
        mock_logger,
    ):
        alert = AlertFactory()
        mock_send_email.side_effect = Exception()

        dispatch_alert_notifications(alert)

        mock_logger.info.assert_any_call(
            "Finished notification dispatch for alert %s",
            alert.id,
        )


# ============================================================
# Slack Failure
# ============================================================


@pytest.mark.django_db
class TestNotificationSlackFailure:
    """
    Slack failures should never stop execution.
    """

    @override_settings(
        EMAIL_NOTIFICATIONS_ENABLED=False,
        SLACK_NOTIFICATIONS_ENABLED=True,
    )
    @patch("alerts.services.notification_service.logger")
    @patch("alerts.services.notification_service.send_slack_notification")
    def test_slack_failure_logged(
        self,
        mock_send_slack,
        mock_logger,
    ):
        alert = AlertFactory()
        mock_send_slack.side_effect = Exception()

        dispatch_alert_notifications(alert)

        mock_logger.exception.assert_called_once_with(
            "Failed to send Slack notification for alert %s",
            alert.id,
        )

    @override_settings(
        EMAIL_NOTIFICATIONS_ENABLED=False,
        SLACK_NOTIFICATIONS_ENABLED=True,
    )
    @patch("alerts.services.notification_service.logger")
    @patch("alerts.services.notification_service.send_slack_notification")
    def test_slack_failure_does_not_raise(
        self,
        mock_send_slack,
        mock_logger,
    ):
        alert = AlertFactory()
        mock_send_slack.side_effect = RuntimeError()

        dispatch_alert_notifications(alert)

    @override_settings(
        EMAIL_NOTIFICATIONS_ENABLED=False,
        SLACK_NOTIFICATIONS_ENABLED=True,
    )
    @patch("alerts.services.notification_service.logger")
    @patch("alerts.services.notification_service.send_slack_notification")
    def test_finish_log_written_after_slack_failure(
        self,
        mock_send_slack,
        mock_logger,
    ):
        alert = AlertFactory()
        mock_send_slack.side_effect = Exception()

        dispatch_alert_notifications(alert)

        mock_logger.info.assert_any_call(
            "Finished notification dispatch for alert %s",
            alert.id,
        )


# ============================================================
# Both Providers Fail
# ============================================================


@pytest.mark.django_db
class TestNotificationBothProvidersFailure:
    """
    Both providers fail independently.
    """

    @override_settings(
        EMAIL_NOTIFICATIONS_ENABLED=True,
        SLACK_NOTIFICATIONS_ENABLED=True,
    )
    @patch("alerts.services.notification_service.logger")
    @patch("alerts.services.notification_service.send_slack_notification")
    @patch("alerts.services.notification_service.send_alert_email")
    def test_both_failures_logged(
        self,
        mock_send_email,
        mock_send_slack,
        mock_logger,
    ):
        alert = AlertFactory()
        mock_send_email.side_effect = Exception()
        mock_send_slack.side_effect = Exception()

        dispatch_alert_notifications(alert)

        assert mock_logger.exception.call_count == 2

    @override_settings(
        EMAIL_NOTIFICATIONS_ENABLED=True,
        SLACK_NOTIFICATIONS_ENABLED=True,
    )
    @patch("alerts.services.notification_service.logger")
    @patch("alerts.services.notification_service.send_slack_notification")
    @patch("alerts.services.notification_service.send_alert_email")
    def test_dispatch_finishes_when_both_fail(
        self,
        mock_send_email,
        mock_send_slack,
        mock_logger,
    ):
        alert = AlertFactory()
        mock_send_email.side_effect = Exception()
        mock_send_slack.side_effect = Exception()

        dispatch_alert_notifications(alert)

        mock_logger.info.assert_any_call(
            "Finished notification dispatch for alert %s",
            alert.id,
        )


# ============================================================
# Edge Cases
# ============================================================


@pytest.mark.django_db
class TestNotificationServiceEdgeCase:
    """
    Miscellaneous edge cases.
    """

    @override_settings(
        EMAIL_NOTIFICATIONS_ENABLED=True,
        SLACK_NOTIFICATIONS_ENABLED=True,
    )
    @patch("alerts.services.notification_service.send_slack_notification")
    @patch("alerts.services.notification_service.send_alert_email")
    @pytest.mark.parametrize("alert_type", AlertType.values)
    def test_dispatch_accepts_all_alert_types(
        self,
        mock_send_email,
        mock_send_slack,
        alert_type,
    ):
        alert = AlertFactory(alert_type=alert_type)
        dispatch_alert_notifications(alert)

        mock_send_email.assert_called_once()
        mock_send_slack.assert_called_once()

    @override_settings(
        EMAIL_NOTIFICATIONS_ENABLED=True,
        SLACK_NOTIFICATIONS_ENABLED=True,
    )
    @patch("alerts.services.notification_service.send_slack_notification")
    @patch("alerts.services.notification_service.send_alert_email")
    @pytest.mark.parametrize("severity", AlertSeverity.values)
    def test_dispatch_accepts_all_severities(
        self,
        mock_send_email,
        mock_send_slack,
        severity,
    ):
        alert = AlertFactory(severity=severity)
        dispatch_alert_notifications(alert)

        mock_send_email.assert_called_once()
        mock_send_slack.assert_called_once()

    @override_settings(
        EMAIL_NOTIFICATIONS_ENABLED=True,
        SLACK_NOTIFICATIONS_ENABLED=True,
    )
    @patch("alerts.services.notification_service.send_slack_notification")
    @patch("alerts.services.notification_service.send_alert_email")
    def test_dispatch_handles_empty_message(
        self,
        mock_send_email,
        mock_send_slack,
    ):
        alert = AlertFactory(message="")
        dispatch_alert_notifications(alert)

        mock_send_email.assert_called_once()
        mock_send_slack.assert_called_once()

    @override_settings(
        EMAIL_NOTIFICATIONS_ENABLED=True,
        SLACK_NOTIFICATIONS_ENABLED=True,
    )
    @patch("alerts.services.notification_service.send_slack_notification")
    @patch("alerts.services.notification_service.send_alert_email")
    def test_dispatch_handles_unicode_message(
        self,
        mock_send_email,
        mock_send_slack,
    ):
        alert = AlertFactory(message="🚨 Database down — सर्वर")
        dispatch_alert_notifications(alert)

        mock_send_email.assert_called_once()
        mock_send_slack.assert_called_once()