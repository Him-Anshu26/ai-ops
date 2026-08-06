import uuid

from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import IsAuthenticated

from alerts.models import (
    Alert,
    AlertStatus,
    AlertSeverity,
    AlertType,
)

from alerts.views import AlertViewSet

from alerts.filters import AlertFilter
from alerts.pagination import AlertCursorPagination

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



# ============================================================
# Base Test Class
# ============================================================

class BaseAlertViewTestCase(APITestCase):
    """
    Shared setup for Alert API tests.
    """

    def setUp(self):

        self.user = UserFactory()

        self.service = ServiceFactory(
            created_by=self.user
        )

        self.client.force_authenticate(
            user=self.user
        )


    def create_alert(
        self,
        message="Test Alert",
        status=AlertStatus.OPEN,
        severity=AlertSeverity.HIGH,
        alert_type=AlertType.ERROR,
        alert_key=None,
    ):

        if alert_key is None:
            alert_key = f"error:{uuid.uuid4().hex}"

        return AlertFactory(
            service=self.service,
            message=message,
            status=status,
            severity=severity,
            alert_type=alert_type,
            alert_key=alert_key,
        )



# ============================================================
# Authentication Tests
# ============================================================

class AlertAuthenticationTests(BaseAlertViewTestCase):


    def test_list_requires_authentication(self):

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


    def test_retrieve_requires_authentication(self):

        alert = self.create_alert()


        self.client.force_authenticate(
            user=None
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
            status.HTTP_401_UNAUTHORIZED,
        )



# ============================================================
# Create API Tests
# ============================================================

class AlertCreateAPIViewTests(BaseAlertViewTestCase):


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


        self.assertEqual(
            Alert.objects.count(),
            1,
        )



    def test_create_alert_missing_required_fields(self):

        response = self.client.post(
            reverse("alerts-list"),
            {},
            format="json",
        )


        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )



    def test_create_alert_invalid_alert_type(self):

        payload = {
            "service": self.service.id,
            "alert_type": "wrong",
            "alert_key": "error:500",
            "severity": AlertSeverity.HIGH,
            "status": AlertStatus.OPEN,
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



    def test_create_alert_invalid_alert_key_format(self):

        payload = {
            "service": self.service.id,
            "alert_type": AlertType.ERROR,
            "alert_key": "wrong-format",
            "severity": AlertSeverity.HIGH,
            "status": AlertStatus.OPEN,
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



    def test_create_uses_write_serializer(self):

        view = AlertViewSet()

        view.action = "create"


        serializer = view.get_serializer_class()


        self.assertIs(
            serializer,
            AlertWriteSerializer,
        )



# ============================================================
# List API Tests
# ============================================================

class AlertListAPIViewTests(BaseAlertViewTestCase):


    def test_list_returns_alerts(self):

        self.create_alert(
            message="Alert 1",
            alert_key="error:1",
        )

        self.create_alert(
            message="Alert 2",
            alert_key="error:2",
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
            2,
        )



    def test_list_returns_only_active_alerts_by_default(self):

        self.create_alert(
            status=AlertStatus.OPEN
        )


        self.create_alert(
            status=AlertStatus.RESOLVED
        )


        response = self.client.get(
            reverse("alerts-list")
        )


        self.assertEqual(
            len(response.data["results"]),
            1,
        )



    def test_list_can_filter_resolved_alerts(self):

        self.create_alert(
            status=AlertStatus.RESOLVED
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



    def test_list_contains_pagination_keys(self):

        self.create_alert()


        response = self.client.get(
            reverse("alerts-list")
        )


        self.assertIn(
            "results",
            response.data,
        )


        self.assertIn(
            "next",
            response.data,
        )


        self.assertIn(
            "previous",
            response.data,
        )



    def test_list_uses_read_serializer(self):

        alert = self.create_alert()


        response = self.client.get(
            reverse("alerts-list")
        )


        serializer = AlertReadSerializer(
            alert
        )


        self.assertEqual(
            set(response.data["results"][0].keys()),
            set(serializer.data.keys()),
        )



# ============================================================
# Retrieve API Tests
# ============================================================

class AlertRetrieveAPIViewTests(BaseAlertViewTestCase):


    def test_retrieve_existing_alert(self):

        alert = self.create_alert()


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



    def test_retrieve_non_existing_alert_returns_404(self):

        response = self.client.get(
            reverse(
                "alerts-detail",
                kwargs={
                    "pk": 999999
                }
            )
        )


        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )



    def test_retrieve_uses_read_serializer(self):

        alert = self.create_alert()


        response = self.client.get(
            reverse(
                "alerts-detail",
                kwargs={
                    "pk": alert.id
                }
            )
        )


        serializer = AlertReadSerializer(
            alert
        )


        self.assertEqual(
            set(response.data.keys()),
            set(serializer.data.keys()),
        )



# ============================================================
# Resolve Workflow Tests
# ============================================================

class AlertResolveAPIViewTests(BaseAlertViewTestCase):


    def test_resolve_alert_successfully(self):

        alert = self.create_alert()


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
            alert.resolved_at
        )



    def test_resolve_requires_resolution_note(self):

        alert = self.create_alert()


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



    def test_resolve_uses_resolve_serializer(self):

        view = AlertViewSet()

        view.action = "resolve"


        serializer = view.get_serializer_class()


        self.assertIs(
            serializer,
            AlertResolveSerializer,
        )



# ============================================================
# HTTP Method Restrictions
# ============================================================

class AlertHTTPRestrictionTests(BaseAlertViewTestCase):


    def test_put_not_allowed(self):

        alert = self.create_alert()


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



    def test_patch_not_allowed(self):

        alert = self.create_alert()


        response = self.client.patch(
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



    def test_delete_not_allowed(self):

        alert = self.create_alert()


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



# ============================================================
# ViewSet Internal Tests
# ============================================================

class AlertViewSetInternalTests(BaseAlertViewTestCase):


    def test_get_serializer_returns_read_serializer_by_default(self):

        view = AlertViewSet()

        view.action = "list"


        serializer = view.get_serializer_class()


        self.assertIs(
            serializer,
            AlertReadSerializer,
        )



    def test_queryset_exists(self):

        self.assertIsNotNone(
            AlertViewSet.queryset
        )



    def test_queryset_default_ordering(self):

        first = self.create_alert(
            message="old"
        )

        second = self.create_alert(
            message="new"
        )


        view = AlertViewSet()

        view.request = type(
            "Request",
            (),
            {
                "query_params": {}
            }
        )()


        queryset = list(
            view.get_queryset()
        )


        self.assertEqual(
            queryset[0].id,
            second.id,
        )



    def test_http_methods_are_restricted(self):

        self.assertEqual(
            AlertViewSet.http_method_names,
            [
                "get",
                "post",
            ],
        )



    def test_permission_classes(self):

        self.assertEqual(
            AlertViewSet.permission_classes,
            [
                IsAuthenticated
            ],
        )



    def test_filter_configuration(self):

        self.assertIs(
            AlertViewSet.filterset_class,
            AlertFilter,
        )



    def test_pagination_configuration(self):

        self.assertIs(
            AlertViewSet.pagination_class,
            AlertCursorPagination,
        )



# ============================================================
# Configuration Tests
# ============================================================

class AlertConfigurationTests(TestCase):


    def test_filter_backends(self):

        self.assertIn(
            DjangoFilterBackend,
            AlertViewSet.filter_backends,
        )


        self.assertIn(
            OrderingFilter,
            AlertViewSet.filter_backends,
        )



    def test_ordering_fields(self):

        self.assertEqual(
            AlertViewSet.ordering_fields,
            [
                "created_at",
                "severity",
                "trigger_count",
                "last_triggered_at",
            ],
        )


    def test_viewset_does_not_have_update(self):

        self.assertFalse(
            hasattr(
                AlertViewSet,
                "update",
            )
        )


    def test_viewset_does_not_have_destroy(self):

        self.assertFalse(
            hasattr(
                AlertViewSet,
                "destroy",
            )
        )