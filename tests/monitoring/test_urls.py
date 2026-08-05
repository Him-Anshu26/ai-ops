from django.test import SimpleTestCase
from django.urls import (
    resolve,
    reverse,
)

from monitoring.views import (
    HealthCheckAPIView,
    LogViewSet,
)


# ============================================================
# Base URL Test Case
# ============================================================

class BaseURLTestCase(SimpleTestCase):
    """
    Shared helpers for URL tests.
    """

    @property
    def logs_list_url(self):
        return reverse("logs-list")

    @property
    def logs_detail_url(self):
        return reverse(
            "logs-detail",
            kwargs={
                "pk": 1,
            },
        )

    @property
    def health_url(self):
        return reverse(
            "health-check",
        )


# ============================================================
# Monitoring URL Tests
# ============================================================

class MonitoringURLTests(BaseURLTestCase):
    """
    Tests for monitoring.urls.
    """

    # ---------------------------------------------------------
    # Reverse: list endpoint
    # ---------------------------------------------------------

    def test_logs_list_reverse(self):
        self.assertEqual(
            self.logs_list_url,
            "/api/v1/monitoring/logs/",
        )

    # ---------------------------------------------------------
    # Reverse: detail endpoint
    # ---------------------------------------------------------

    def test_logs_detail_reverse(self):
        self.assertEqual(
            self.logs_detail_url,
            "/api/v1/monitoring/logs/1/",
        )

    # ---------------------------------------------------------
    # Resolve list endpoint
    # ---------------------------------------------------------

    def test_logs_list_resolves(self):
        match = resolve(
            "/api/v1/monitoring/logs/",
        )

        self.assertEqual(
            match.view_name,
            "logs-list",
        )

    # ---------------------------------------------------------
    # Resolve detail endpoint
    # ---------------------------------------------------------

    def test_logs_detail_resolves(self):
        match = resolve(
            "/api/v1/monitoring/logs/1/",
        )

        self.assertEqual(
            match.view_name,
            "logs-detail",
        )

    # ---------------------------------------------------------
    # List endpoint uses LogViewSet
    # ---------------------------------------------------------

    def test_logs_list_uses_log_viewset(self):
        match = resolve(
            "/api/v1/monitoring/logs/",
        )

        self.assertEqual(
            match.func.cls,
            LogViewSet,
        )

    # ---------------------------------------------------------
    # Detail endpoint uses LogViewSet
    # ---------------------------------------------------------

    def test_logs_detail_uses_log_viewset(self):
        match = resolve(
            "/api/v1/monitoring/logs/1/",
        )

        self.assertEqual(
            match.func.cls,
            LogViewSet,
        )

    # ---------------------------------------------------------
    # Router generated names
    # ---------------------------------------------------------

    def test_router_generated_names_exist(self):
        self.assertEqual(
            reverse("logs-list"),
            "/api/v1/monitoring/logs/",
        )

        self.assertEqual(
            reverse(
                "logs-detail",
                kwargs={
                    "pk": 99,
                },
            ),
            "/api/v1/monitoring/logs/99/",
        )


# ============================================================
# Project URL Tests
# ============================================================

class ProjectURLTests(BaseURLTestCase):
    """
    Tests for project-level URL configuration.
    """

    # ---------------------------------------------------------
    # Health endpoint reverse
    # ---------------------------------------------------------

    def test_health_endpoint_reverse(self):
        self.assertEqual(
            self.health_url,
            "/api/v1/health/",
        )

    # ---------------------------------------------------------
    # Health endpoint resolves correctly
    # ---------------------------------------------------------

    def test_health_endpoint_resolves(self):
        match = resolve(
            "/api/v1/health/",
        )

        self.assertEqual(
            match.view_name,
            "health-check",
        )

        self.assertEqual(
            match.func.view_class,
            HealthCheckAPIView,
        )

    # ---------------------------------------------------------
    # Monitoring prefix exists
    # ---------------------------------------------------------

    def test_monitoring_prefix_exists(self):
        match = resolve(
            "/api/v1/monitoring/logs/",
        )

        self.assertEqual(
            match.func.cls,
            LogViewSet,
        )

    # ---------------------------------------------------------
    # Detail route captures pk correctly
    # ---------------------------------------------------------

    def test_detail_route_captures_pk(self):
        match = resolve(
            "/api/v1/monitoring/logs/123/",
        )

        self.assertEqual(
            match.kwargs["pk"],
            "123",
        )

    # ---------------------------------------------------------
    # Health endpoint name exists
    # ---------------------------------------------------------

    def test_health_endpoint_name_exists(self):
        url = reverse(
            "health-check",
        )

        self.assertEqual(
            url,
            "/api/v1/health/",
        )

    # ---------------------------------------------------------
    # Reverse -> Resolve consistency
    # ---------------------------------------------------------

    def test_reverse_and_resolve_are_consistent(self):
        url = reverse(
            "logs-list",
        )

        match = resolve(url)

        self.assertEqual(
            match.view_name,
            "logs-list",
        )

        self.assertEqual(
            match.func.cls,
            LogViewSet,
        )

    # ---------------------------------------------------------
    # Detail reverse -> resolve consistency
    # ---------------------------------------------------------

    def test_detail_reverse_and_resolve_are_consistent(self):
        url = reverse(
            "logs-detail",
            kwargs={
                "pk": 25,
            },
        )

        match = resolve(url)

        self.assertEqual(
            match.view_name,
            "logs-detail",
        )

        self.assertEqual(
            match.func.cls,
            LogViewSet,
        )

        self.assertEqual(
            match.kwargs["pk"],
            "25",
        )

    # ---------------------------------------------------------
    # Health endpoint class
    # ---------------------------------------------------------

    def test_health_endpoint_uses_healthcheck_apiview(self):
        match = resolve(
            "/api/v1/health/",
        )

        self.assertIs(
            match.func.view_class,
            HealthCheckAPIView,
        )

    # ---------------------------------------------------------
    # URL names are unique
    # ---------------------------------------------------------

    def test_url_names_are_unique(self):
        self.assertNotEqual(
            reverse("logs-list"),
            reverse("health-check"),
        )