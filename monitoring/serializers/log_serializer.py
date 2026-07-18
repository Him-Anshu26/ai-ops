from rest_framework import serializers
from monitoring.models import Log, LogStatus


class LogWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Log
        fields = ['service', 'status', 'status_code', 'response_time_ms', 'message']

        extra_kwargs = {
            'message': {
                'required': False,
                'allow_blank': True,
                'allow_null': True
            }
        }


    # Field-level validation
    def validate_response_time_ms(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError("Response time cannot be negative.")
        return value

    def validate_status_code(self, value):
        if value is not None and not (100 <= value <= 599):
            raise serializers.ValidationError("Status code must be between 100 and 599.")
        return value


    def validate(self, data):
        status = data.get('status')
        status_code = data.get('status_code')

        if not status:
            raise serializers.ValidationError("Status is required.")

        if status not in [choice[0] for choice in LogStatus.choices]:
            raise serializers.ValidationError("Invalid status.")

        if status == LogStatus.ERROR:
            if status_code is not None and status_code < 400:
                raise serializers.ValidationError(
                    "If status='error', status_code must be >= 400 (if provided)."
                )
        

        # fallback message (important)
        if not data.get('message'):
            data['message'] = f"{status} log"

        return data
    




class LogReadSerializer(serializers.ModelSerializer):
    service_name = serializers.CharField(source='service.name', read_only=True) 


    class Meta:
        model = Log
        fields = ['id', 'service','service_name', 'status', 'status_code', 'response_time_ms', 'message', 'created_at']
        read_only_fields = fields


