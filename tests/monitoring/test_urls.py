from django.urls import resolve, reverse
import pytest

from monitoring.views import (
    HealthCheckAPIView,
    LogViewSet,
)

# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def logs_list_url():
    return reverse("logs-list")

@pytest.fixture
def logs_detail_url():
    return reverse("logs-detail", kwargs={"pk": 1})

@pytest.fixture
def health_url():
    return reverse("health-check")


# ============================================================
# Monitoring URL Tests
# ============================================================

class TestMonitoringURLs:
    """
    Tests for monitoring.urls.
    """

    # ---------------------------------------------------------
    # Reverse: list endpoint
    # ---------------------------------------------------------

    def test_logs_list_reverse(self, logs_list_url):
        assert logs_list_url == "/api/v1/monitoring/logs/"

    # ---------------------------------------------------------
    # Reverse: detail endpoint
    # ---------------------------------------------------------

    def test_logs_detail_reverse(self, logs_detail_url):
        assert logs_detail_url == "/api/v1/monitoring/logs/1/"

    # ---------------------------------------------------------
    # Resolve list endpoint
    # ---------------------------------------------------------

    def test_logs_list_resolves(self):
        match = resolve("/api/v1/monitoring/logs/")
        assert match.view_name == "logs-list"

    # ---------------------------------------------------------
    # Resolve detail endpoint
    # ---------------------------------------------------------

    def test_logs_detail_resolves(self):
        match = resolve("/api/v1/monitoring/logs/1/")
        assert match.view_name == "logs-detail"

    # ---------------------------------------------------------
    # List endpoint uses LogViewSet
    # ---------------------------------------------------------

    def test_logs_list_uses_log_viewset(self):
        match = resolve("/api/v1/monitoring/logs/")
        assert match.func.cls == LogViewSet

    # ---------------------------------------------------------
    # Detail endpoint uses LogViewSet
    # ---------------------------------------------------------

    def test_logs_detail_uses_log_viewset(self):
        match = resolve("/api/v1/monitoring/logs/1/")
        assert match.func.cls == LogViewSet

    # ---------------------------------------------------------
    # Router generated names
    # ---------------------------------------------------------

    def test_router_generated_names_exist(self):
        assert reverse("logs-list") == "/api/v1/monitoring/logs/"
        assert reverse("logs-detail", kwargs={"pk": 99}) == "/api/v1/monitoring/logs/99/"


# ============================================================
# Project URL Tests
# ============================================================

class TestProjectURLs:
    """
    Tests for project-level URL configuration.
    """

    # ---------------------------------------------------------
    # Health endpoint reverse
    # ---------------------------------------------------------

    def test_health_endpoint_reverse(self, health_url):
        assert health_url == "/api/v1/health/"

    # ---------------------------------------------------------
    # Health endpoint resolves correctly
    # ---------------------------------------------------------

    def test_health_endpoint_resolves(self):
        match = resolve("/api/v1/health/")
        assert match.view_name == "health-check"
        assert match.func.view_class == HealthCheckAPIView

    # ---------------------------------------------------------
    # Monitoring prefix exists
    # ---------------------------------------------------------

    def test_monitoring_prefix_exists(self):
        match = resolve("/api/v1/monitoring/logs/")
        assert match.func.cls == LogViewSet

    # ---------------------------------------------------------
    # Detail route captures pk correctly
    # ---------------------------------------------------------

    def test_detail_route_captures_pk(self):
        match = resolve("/api/v1/monitoring/logs/123/")
        assert match.kwargs["pk"] == "123"

    # ---------------------------------------------------------
    # Health endpoint name exists
    # ---------------------------------------------------------

    def test_health_endpoint_name_exists(self):
        url = reverse("health-check")
        assert url == "/api/v1/health/"

    # ---------------------------------------------------------
    # Reverse -> Resolve consistency
    # ---------------------------------------------------------

    def test_reverse_and_resolve_are_consistent(self):
        url = reverse("logs-list")
        match = resolve(url)

        assert match.view_name == "logs-list"
        assert match.func.cls == LogViewSet

    # ---------------------------------------------------------
    # Detail reverse -> resolve consistency
    # ---------------------------------------------------------

    def test_detail_reverse_and_resolve_are_consistent(self):
        url = reverse("logs-detail", kwargs={"pk": 25})
        match = resolve(url)

        assert match.view_name == "logs-detail"
        assert match.func.cls == LogViewSet
        assert match.kwargs["pk"] == "25"

    # ---------------------------------------------------------
    # Health endpoint class
    # ---------------------------------------------------------

    def test_health_endpoint_uses_healthcheck_apiview(self):
        match = resolve("/api/v1/health/")
        assert match.func.view_class is HealthCheckAPIView

    # ---------------------------------------------------------
    # URL names are unique
    # ---------------------------------------------------------

    def test_url_names_are_unique(self):
        assert reverse("logs-list") != reverse("health-check")