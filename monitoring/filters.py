import django_filters

from monitoring.models import Log


class LogFilter(django_filters.FilterSet):

    # Exact filters
    service = django_filters.NumberFilter(field_name='service_id')

    status = django_filters.CharFilter(
        field_name='status',
        lookup_expr='iexact'
    )

    status_code = django_filters.NumberFilter(
        field_name='status_code'
    )

    # Time range filters
    created_after = django_filters.DateTimeFilter(
        field_name='created_at',
        lookup_expr='gte'
    )

    created_before = django_filters.DateTimeFilter(
        field_name='created_at',
        lookup_expr='lte'
    )

    # Response time range
    min_response_time = django_filters.NumberFilter(
        field_name='response_time_ms',
        lookup_expr='gte'
    )

    max_response_time = django_filters.NumberFilter(
        field_name='response_time_ms',
        lookup_expr='lte'
    )

    # Message search
    message = django_filters.CharFilter(
        field_name='message',
        lookup_expr='icontains'
    )


                #  ⚠️ One Potential Bottleneck

                # This becomes:
                # LIKE '%text%'
                # B-tree index cannot help much.

                # But:
                # for NOW → completely acceptable.

                # Production systems still allow text search.

                # Later you can:
                # add PostgreSQL full-text search
                # use Elasticsearch
                # use trigram indexes

                # NOT NOW.
                # Leave it.

    class Meta:
        model = Log

        fields = [
            'service',
            'status',
            'status_code',
            'created_after',
            'created_before',
            'min_response_time',
            'max_response_time',
            'message'
        ]