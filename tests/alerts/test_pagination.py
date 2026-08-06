import pytest
from rest_framework.pagination import CursorPagination
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from alerts.pagination import AlertCursorPagination
from alerts.models import Alert
from tests.factories import AlertFactory


# ============================================================
# Helper View
# ============================================================

class DummyView:
    """
    Minimal DRF view for pagination tests.
    """
    pass


# ============================================================
# AlertCursorPagination Configuration Tests
# ============================================================

class TestAlertCursorPaginationConfiguration:
    """
    Unit tests for AlertCursorPagination configuration.
    """

    def setup_method(self):
        self.pagination = AlertCursorPagination()

    def test_default_page_size(self):
        assert self.pagination.page_size == 20

    def test_page_size_query_param(self):
        assert self.pagination.page_size_query_param == "page_size"

    def test_max_page_size(self):
        assert self.pagination.max_page_size == 100

    def test_default_ordering(self):
        assert self.pagination.ordering == "-created_at"

    def test_inherits_cursor_pagination(self):
        assert isinstance(self.pagination, CursorPagination)

    def test_pagination_instance_created(self):
        assert self.pagination is not None


# ============================================================
# AlertCursorPagination Functional Tests
# ============================================================

@pytest.mark.django_db
class TestAlertCursorPaginationFunctional:
    """
    Functional tests for AlertCursorPagination.
    """

    def setup_method(self):
        self.factory = APIRequestFactory()
        self.pagination = AlertCursorPagination()
        self.view = DummyView()

    def test_returns_first_page(self):
        AlertFactory.create_batch(25)

        request = Request(self.factory.get("/api/v1/alerts/"))
        queryset = Alert.objects.all()

        page = self.pagination.paginate_queryset(
            queryset,
            request,
            view=self.view,
        )

        assert len(page) == 20

    def test_respects_custom_page_size(self):
        AlertFactory.create_batch(25)

        request = Request(self.factory.get("/api/v1/alerts/?page_size=5"))
        queryset = Alert.objects.all()

        page = self.pagination.paginate_queryset(
            queryset,
            request,
            view=self.view,
        )

        assert len(page) == 5

    def test_caps_page_size_at_max(self):
        AlertFactory.create_batch(110)

        request = Request(self.factory.get("/api/v1/alerts/?page_size=500"))
        queryset = Alert.objects.all()

        page = self.pagination.paginate_queryset(
            queryset,
            request,
            view=self.view,
        )

        assert len(page) == 100

    def test_returns_all_results_when_less_than_page_size(self):
        AlertFactory.create_batch(8)

        request = Request(self.factory.get("/api/v1/alerts/"))
        queryset = Alert.objects.all()

        page = self.pagination.paginate_queryset(
            queryset,
            request,
            view=self.view,
        )

        assert len(page) == 8

    def test_results_ordered_by_created_at_desc(self):
        from django.utils import timezone
        from datetime import timedelta
        
        older = AlertFactory()
        newer = AlertFactory()
        
        older.created_at = timezone.now() - timedelta(days=1)
        older.save(update_fields=["created_at"])
        
        newer.created_at = timezone.now()
        newer.save(update_fields=["created_at"])

        request = Request(self.factory.get("/api/v1/alerts/"))
        queryset = Alert.objects.all()

        page = self.pagination.paginate_queryset(
            queryset,
            request,
            view=self.view,
        )

        assert page[0] == newer

    def test_next_link_generated(self):
        AlertFactory.create_batch(30)

        request = Request(self.factory.get("/api/v1/alerts/"))
        queryset = Alert.objects.all()

        self.pagination.paginate_queryset(
            queryset,
            request,
            view=self.view,
        )

        response = self.pagination.get_paginated_response([])
        assert response.data["next"] is not None