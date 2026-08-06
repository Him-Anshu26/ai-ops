"""
Integration tests for the Alert Notification pipeline.
"""

import pytest
from unittest.mock import patch
from django.test import override_settings

from alerts.tasks import dispatch_alert_notifications_task
from tests.factories import AlertFactory


@pytest.mark.django_db
class TestAlertNotificationWorkflow:
    
    @patch("alerts.services.notification_service.send_alert_email")
    @patch("alerts.services.notification_service.send_slack_notification")
    @override_settings(EMAIL_NOTIFICATIONS_ENABLED=True, SLACK_NOTIFICATIONS_ENABLED=True)
    def test_notification_task_success(self, mock_slack, mock_email):
        """
        Verify that the background task cleanly dispatches to all enabled providers.
        """
        alert = AlertFactory()

        dispatch_alert_notifications_task(alert.id)

        assert mock_email.called
        assert mock_email.call_args[0][0] == alert
        
        assert mock_slack.called
        assert mock_slack.call_args[0][0] == alert

    @patch("alerts.services.notification_service.send_alert_email")
    @patch("alerts.services.notification_service.send_slack_notification")
    @override_settings(EMAIL_NOTIFICATIONS_ENABLED=False, SLACK_NOTIFICATIONS_ENABLED=False)
    def test_notification_task_disabled_in_settings(self, mock_slack, mock_email):
        """
        Verify that feature flags strictly prevent dispatching.
        """
        alert = AlertFactory()

        dispatch_alert_notifications_task(alert.id)

        assert not mock_email.called
        assert not mock_slack.called

    @patch("alerts.services.notification_service.send_alert_email")
    @patch("alerts.services.notification_service.send_slack_notification")
    @override_settings(EMAIL_NOTIFICATIONS_ENABLED=True, SLACK_NOTIFICATIONS_ENABLED=True)
    def test_notification_provider_isolation(self, mock_slack, mock_email):
        """
        Verify that a catastrophic failure in one notification provider (e.g. Email API is down)
        does not crash the task and allows subsequent providers (e.g. Slack) to still execute.
        """
        alert = AlertFactory()

        # Force the email provider to crash natively
        mock_email.side_effect = Exception("Critical Email API Failure")

        # The task should catch the exception internally and NOT crash
        dispatch_alert_notifications_task(alert.id)

        assert mock_email.called
        
        # Slack must still be executed despite the email crash
        assert mock_slack.called
        assert mock_slack.call_args[0][0] == alert

    @patch("alerts.services.notification_service.send_alert_email")
    @patch("alerts.services.notification_service.send_slack_notification")
    @override_settings(EMAIL_NOTIFICATIONS_ENABLED=True, SLACK_NOTIFICATIONS_ENABLED=True)
    def test_notification_task_deleted_alert(self, mock_slack, mock_email):
        """
        Verify that the task gracefully handles alerts that were deleted before the 
        background worker had a chance to pick them up from the queue.
        """
        # Pass an ID that definitely doesn't exist
        invalid_alert_id = 999999

        # The task should catch Alert.DoesNotExist internally and NOT crash
        dispatch_alert_notifications_task(invalid_alert_id)

        # No providers should be invoked
        assert not mock_email.called
        assert not mock_slack.called
