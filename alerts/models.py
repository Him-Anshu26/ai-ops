from django.db import models
from django.db.models import Q, F
from django.utils import timezone



# Create your models here.
class AlertType(models.TextChoices):
    ERROR = 'error', 'Error'
    DOWNTIME = 'downtime', 'Downtime'
    HIGH_LATENCY = 'high_latency', 'High Latency'


class AlertStatus(models.TextChoices):
    OPEN = 'open', 'Open'
    ACKNOWLEDGED = 'acknowledged', 'Acknowledged'
    RESOLVED = 'resolved', 'Resolved'


class AlertSeverity(models.TextChoices):
    LOW = 'low', 'Low'
    MEDIUM = 'medium', 'Medium'
    HIGH = 'high', 'High'
    CRITICAL = 'critical', 'Critical'




class Alert(models.Model):
    service = models.ForeignKey(
        'monitoring.Service',
        on_delete=models.CASCADE,
        related_name='alerts',
    )

    log = models.ForeignKey(
        'monitoring.Log',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='alerts',
    )


    alert_type = models.CharField(max_length=12, choices=AlertType.choices)

    # changed alert_message to message for cleaner + consistent naming
    message = models.CharField(max_length=255)

    alert_key = models.CharField(max_length=100) # error:service_id, latency:service_id - allows multiple different messages for same type (e.g. different error codes) but still only 1 active alert per type+service

    severity = models.CharField(
        max_length=8, 
        choices=AlertSeverity.choices,
        default=AlertSeverity.MEDIUM
    )


    status = models.CharField(
            max_length=15,
            choices=AlertStatus.choices,
            default=AlertStatus.OPEN
    ) 


    trigger_count = models.PositiveIntegerField(default=1)

    created_at = models.DateTimeField(auto_now_add=True)
    last_triggered_at = models.DateTimeField(default=timezone.now)
    resolved_at = models.DateTimeField(null=True, blank=True)   

    resolution_note = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-last_triggered_at']

        constraints = [
            # models.UniqueConstraint(
            #     fields=['service', 'alert_type'],
            #     condition=models.Q(status=AlertStatus.RESOLVED),
            #     name='unique_active_alert_per_service_type'
            # )

            # Only one ACTIVE alert per service + type + alert_key (allows multiple different messages)
            models.UniqueConstraint(
                fields=['service', 'alert_type', 'alert_key'],
                condition=~Q(status=AlertStatus.RESOLVED),
                name='unique_active_alert_per_service_type_alert_key'
            )
        ]

        indexes = [
            models.Index(
                fields=['service', 'status'], 
                name='idx_alert_service_status'
            ),

            models.Index(fields=['created_at'],
                name='idx_alert_created_at'
            ),

            # Filter by type WITHIN a service
            models.Index(
                fields=['service', 'alert_type'],
                name='idx_service_alert_type'
            ),

            # Filter high/critical alerts per service
            models.Index(
                fields=['service', 'severity'],
                name='idx_service_severity'
            ),

            # Most important: active alerts only
            models.Index(
                fields=['service'],
                condition=~Q(status=AlertStatus.RESOLVED),
                name='idx_active_alerts_per_service'
            ),

            models.Index(
                fields=['service', 'last_triggered_at'],
                condition=~Q(status=AlertStatus.RESOLVED),
                name='idx_active_ser_last_triggered'
            ),

            models.Index(
                fields=['status', 'last_triggered_at'],
                name='idx_status_last_triggered'
            ),

        ]

    def __str__(self):
        return f"{self.get_alert_type_display()} - {self.service.name} ({self.status})"    


    @property
    def is_active(self):
        return self.status != AlertStatus.RESOLVED

    def mark_resolved(self):
        type(self).objects.filter(pk=self.pk).update(
            status=AlertStatus.RESOLVED,
            resolved_at=timezone.now()
        )
        

    def increment(self, timestamp):
        type(self).objects.filter(pk=self.pk).update(
            trigger_count=F('trigger_count') + 1,
            last_triggered_at=timestamp
        )