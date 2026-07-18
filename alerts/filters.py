import django_filters

from alerts.models import Alert





class AlertFilter(django_filters.FilterSet):
    """
    Production-grade filtering for alerts API.

    Designed for:
    - incident management
    - monitoring dashboards
    - operational debugging
    - alert analytics
    """

    # Filter alerts by related service ID
    service = django_filters.NumberFilter(
        field_name='service_id'
    )

    # Filter by alert status
    # Example:
    # ?status=open
    status = django_filters.CharFilter(
        field_name='status',
        lookup_expr='iexact',
    )

    # Filter by alert type
    # Example:
    # ?alert_type=service_down
    alert_type = django_filters.CharFilter(
        field_name='alert_type',
        lookup_expr='iexact',
    )

    # Filter by severity
    # Example:
    # ?severity=critical
    severity = django_filters.CharFilter(
        field_name='severity',
        lookup_expr='iexact',
    )

    # Filter alerts created after timestamp
    created_after = django_filters.DateTimeFilter(
        field_name='created_at',
        lookup_expr='gte',
    )

    # Filter alerts created before timestamp
    created_before = django_filters.DateTimeFilter(
        field_name='created_at',
        lookup_expr='lte',
    )

    # Filter alerts triggered after timestamp
    last_triggered_after = django_filters.DateTimeFilter(
        field_name='last_triggered_at',
        lookup_expr='gte',
    )

    # Filter alerts triggered before timestamp
    last_triggered_before = django_filters.DateTimeFilter(
        field_name='last_triggered_at',
        lookup_expr='lte',
    )

    # Filter alerts by minimum trigger count
    min_trigger_count = django_filters.NumberFilter(
        field_name='trigger_count',
        lookup_expr='gte',
    )

    # Filter alerts by maximum trigger count
    max_trigger_count = django_filters.NumberFilter(
        field_name='trigger_count',
        lookup_expr='lte',
    )

    # Search alerts by message text
    #
    # WARNING:
    # This becomes:
    # LIKE '%text%'
    #
    # B-tree indexes are not efficient for this.
    #
    # Acceptable for now.
    #
    # Future optimization options:
    # - PostgreSQL full-text search
    # - trigram indexes
    # - Elasticsearch
    message = django_filters.CharFilter(
        field_name='message',
        lookup_expr='icontains',
    )

    class Meta:
        model = Alert

        fields = [
            'service',
            'status',
            'alert_type',
            'severity',
            'created_after',
            'created_before',
            'last_triggered_after',
            'last_triggered_before',
            'min_trigger_count',
            'max_trigger_count',
            'message',
        ]