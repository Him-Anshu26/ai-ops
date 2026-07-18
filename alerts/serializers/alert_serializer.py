from rest_framework import serializers

from alerts.models import (
    Alert,
    AlertStatus,
    AlertSeverity,
    AlertType,
)

import re





class AlertWriteSerializer(serializers.ModelSerializer):
    """
    Serializer used for:

    - manual alert creation (temporary)
    - testing alert workflows
    - validating incoming alert data

    NOTE:
    Later in production, alerts should ideally
    be created internally by the alert engine
    instead of external clients.
    """

    class Meta:
        model = Alert

        fields = [
            'service',
            'alert_type',
            'alert_key',
            'severity',
            'status',
            'message',
        ]

        # System-controlled fields
        # should never be writable by clients.
        read_only_fields = [
            'trigger_count',
            'last_triggered_at',
            'resolved_at',
        ]

        # Message is optional because
        # some alerts may only contain
        # title + severity.
        extra_kwargs = {
            'message': {
                'required': False,
                'allow_blank': True,
                'allow_null': True,
            }
        }

    def validate_severity(self, value):
        """
        Validate alert severity.

        Prevents invalid severity values
        from entering the system.
        """

        if value not in AlertSeverity.values:
            raise serializers.ValidationError(
                "Invalid severity."
            )

        return value


    def validate_status(self, value):
        """
        Validate alert status.

        Ensures only supported
        alert states are accepted.
        """

        if value not in AlertStatus.values:
            raise serializers.ValidationError(
                "Invalid status."
            )

        return value
    

    def validate_alert_type(self, value):
        """
        Ensure only supported alert types
        are accepted.
        """

        if value not in AlertType.values:
            raise serializers.ValidationError(
                "Invalid alert type."
            )

        return value
    

    def validate_alert_key(self, value):
        """
        Validate alert key format.

        Example:
        error:1
        latency:15
        """

        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Alert key cannot be empty."
            )

        pattern = r'^[a-z_]+:\d+$'

        if not re.match(pattern, value):
            raise serializers.ValidationError(
                "Alert key format must be '<type>:<id>'."
            )

        return value





class AlertReadSerializer(serializers.ModelSerializer):
    """
    Serializer used for:

    - dashboards
    - analytics
    - alert listings
    - WebSocket/event responses

    Optimized for read operations.
    """

    # Avoids extra frontend API calls
    # by returning service name directly.
    service_name = serializers.CharField(
        source='service.name',
        read_only=True,
    )

    class Meta:
        model = Alert

        fields = [
            'id',
            'service',
            'service_name',
            'alert_type',
            'message',
            'severity',
            'status',
            'trigger_count',
            'created_at',
            'last_triggered_at',
            'resolved_at',
            'resolution_note',
        ]

        # These fields are managed internally
        # by the backend system.
        read_only_fields = [
            'id',
            'service_name',
            'created_at',
            'last_triggered_at',
            'resolved_at',
        ]





class AlertResolveSerializer(serializers.ModelSerializer):
    """
    Serializer used specifically for:

    - resolving alerts
    - adding resolution notes

    Keeps alert resolution logic isolated
    from normal update operations.
    """

    class Meta:
        model = Alert

        fields = [
            'status',
            'resolution_note',
        ]

    def validate(self, attrs):
        status_value = attrs.get("status")
        note = attrs.get("resolution_note")

        if status_value == AlertStatus.RESOLVED:
            if note is None or not note.strip():
                raise serializers.ValidationError({
                    "resolution_note": "Resolution note is required."
                })

        return attrs