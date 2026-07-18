from rest_framework.pagination import CursorPagination





class AlertCursorPagination(CursorPagination):
    """
    Cursor-based pagination for alerts API.

    Why cursor pagination?

    Alerts are append-heavy time-series data.

    Cursor pagination scales much better than:
    - PageNumberPagination
    - LimitOffsetPagination

    because it avoids large OFFSET scans.

    Optimized for:
    - large datasets
    - real-time monitoring systems
    - operational dashboards
    """

    # Default number of alerts per page
    page_size = 20

    # Allow client-controlled page size
    # Example:
    # ?page_size=50
    page_size_query_param = 'page_size'

    # Prevent extremely large payloads
    max_page_size = 100

    # Newest alerts first
    #
    # Critical for:
    # - monitoring systems
    # - incident dashboards
    # - efficient cursor performance
    ordering = '-created_at'