from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase

from tests.factories import (
    UserFactory,
    ServiceFactory,
    AlertFactory,
)

from alerts.models import (
    AlertStatus,
    AlertType,
    AlertSeverity,
)


class AlertViewSetTests(APITestCase):
    """
    Tests for AlertViewSet.

    Covers:
    - Authentication
    - Create
    - List
    - Retrieve
    - Resolve workflow
    - Filtering
    - Permissions
    - HTTP restrictions
    """


    def setUp(self):

        self.user = UserFactory()

        self.client.force_authenticate(
            user=self.user
        )

        self.service = ServiceFactory(
            created_by=self.user
        )


    # ---------------------------------------------------------
    # Authentication
    # ---------------------------------------------------------

    def test_unauthenticated_user_cannot_access_alerts(self):

        self.client.force_authenticate(
            user=None
        )

        response = self.client.get(
            reverse("alerts-list")
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )


    # ---------------------------------------------------------
    # Create
    # ---------------------------------------------------------

    def test_create_alert_successfully(self):

        payload = {
            "service": self.service.id,
            "alert_type": AlertType.ERROR,
            "alert_key": "error:500",
            "severity": AlertSeverity.HIGH,
            "status": AlertStatus.OPEN,
            "message": "Server failed",
        }


        response = self.client.post(
            reverse("alerts-list"),
            payload,
            format="json",
        )


        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )


        self.assertEqual(
            response.data["message"],
            "Server failed",
        )


    def test_create_alert_invalid_data(self):

        payload = {
            "service": self.service.id,
            "alert_type": "invalid",
            "alert_key": "wrong",
        }


        response = self.client.post(
            reverse("alerts-list"),
            payload,
            format="json",
        )


        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )


    # ---------------------------------------------------------
    # List
    # ---------------------------------------------------------

    def test_list_alerts(self):

        AlertFactory(
            service=self.service
        )

        AlertFactory(
            service=self.service
        )


        response = self.client.get(
            reverse("alerts-list")
        )


        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )


        self.assertIn(
            "results",
            response.data,
        )


        self.assertEqual(
            len(response.data["results"]),
            2,
        )


    def test_list_only_returns_active_alerts_by_default(self):

        AlertFactory(
            service=self.service,
            status=AlertStatus.OPEN,
        )


        AlertFactory(
            service=self.service,
            status=AlertStatus.RESOLVED,
        )


        response = self.client.get(
            reverse("alerts-list")
        )


        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )


        self.assertEqual(
            len(response.data["results"]),
            1,
        )


    def test_can_filter_by_status(self):

        AlertFactory(
            service=self.service,
            status=AlertStatus.RESOLVED,
        )


        response = self.client.get(
            reverse("alerts-list"),
            {
                "status": AlertStatus.RESOLVED
            }
        )


        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )


        self.assertEqual(
            len(response.data["results"]),
            1,
        )


    # ---------------------------------------------------------
    # Retrieve
    # ---------------------------------------------------------

    def test_retrieve_alert(self):

        alert = AlertFactory(
            service=self.service
        )


        response = self.client.get(
            reverse(
                "alerts-detail",
                kwargs={
                    "pk": alert.id
                }
            )
        )


        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )


        self.assertEqual(
            response.data["id"],
            alert.id,
        )


    # ---------------------------------------------------------
    # Resolve
    # ---------------------------------------------------------

    def test_resolve_alert_successfully(self):

        alert = AlertFactory(
            service=self.service,
            status=AlertStatus.OPEN,
        )


        response = self.client.post(
            reverse(
                "alerts-resolve",
                kwargs={
                    "pk": alert.id
                }
            ),
            {
                "status": AlertStatus.RESOLVED,
                "resolution_note": "Fixed issue",
            },
            format="json",
        )


        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )


        alert.refresh_from_db()


        self.assertEqual(
            alert.status,
            AlertStatus.RESOLVED,
        )


        self.assertIsNotNone(
            alert.resolved_at,
        )


    def test_resolve_alert_requires_note(self):

        alert = AlertFactory(
            service=self.service
        )


        response = self.client.post(
            reverse(
                "alerts-resolve",
                kwargs={
                    "pk": alert.id
                }
            ),
            {
                "status": AlertStatus.RESOLVED,
                "resolution_note": "",
            },
            format="json",
        )


        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )


    # ---------------------------------------------------------
    # HTTP Restrictions
    # ---------------------------------------------------------

    def test_update_method_not_allowed(self):

        alert = AlertFactory(
            service=self.service
        )


        response = self.client.put(
            reverse(
                "alerts-detail",
                kwargs={
                    "pk": alert.id
                }
            ),
            {},
            format="json",
        )


        self.assertEqual(
            response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )


    def test_delete_method_not_allowed(self):

        alert = AlertFactory(
            service=self.service
        )


        response = self.client.delete(
            reverse(
                "alerts-detail",
                kwargs={
                    "pk": alert.id
                }
            )
        )


        self.assertEqual(
            response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )