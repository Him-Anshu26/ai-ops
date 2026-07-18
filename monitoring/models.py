from django.db import IntegrityError, models, transaction
from django.conf import settings
from django.utils.text import slugify
from django.core.validators import MinValueValidator, MaxValueValidator


class Status(models.TextChoices):
    ACTIVE = 'active', 'Active'
    DOWN = 'down', 'Down'
    MAINTENANCE = 'maintenance', 'Maintenance'

# Create your models here.
class Service(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, blank=True)
    description = models.TextField(blank=True)


    status = models.CharField(
        max_length=11, 
        choices=Status.choices, 
        default=Status.ACTIVE
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.PROTECT, 
        related_name='services'
    )

    is_deleted = models.BooleanField(default=False)

    last_checked_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    class Meta:
        ordering = ['-created_at']

        constraints = [
                models.UniqueConstraint(
                    fields=['name', 'created_by'],
                    condition=models.Q(is_deleted=False),
                    name='unique_active_service_name_per_user'
                ),
                models.UniqueConstraint(
                    fields=['slug', 'created_by'],
                    condition=models.Q(is_deleted=False),
                    name='unique_active_service_slug_per_user'
                ),
        ]

        indexes = [
            models.Index(
                fields=['created_by','status','is_deleted'],
                name='idx_user_status_deleted'
            ),

            models.Index(fields=['created_at'], name='idx_service_created_at'),
        ]


    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name) or "service"

            for i in range(50):
                self.slug = f"{base_slug}-{i}" if i else base_slug

                try:
                    with transaction.atomic():
                        super().save(*args, **kwargs)
                    return
                except IntegrityError:
                    continue

            raise ValueError("Could not generate unique slug")

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.created_by.username})"
    



class LogStatus(models.TextChoices):
    SUCCESS = 'success', 'Success'
    WARNING = 'warning', 'Warning'
    ERROR = 'error', 'Error'


class Log(models.Model):
    service = models.ForeignKey(
        'monitoring.Service',
        on_delete=models.CASCADE,
        related_name='logs'
    )

    message = models.TextField()

    status = models.CharField(
        max_length=7,
        choices=LogStatus.choices,
        default=LogStatus.SUCCESS
    )

    severity = models.CharField(
        max_length=10,
        choices=[
            ('low', 'Low'),
            ('medium', 'Medium'),
            ('high', 'High'),
        ],
        default='low'
    )

    status_code = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[
            MinValueValidator(100),
            MaxValueValidator(599)
        ]
    )


    response_time_ms = models.PositiveIntegerField(null=True, blank=True)

    metadata = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(
                fields=['service', 'status'],
                name='idx_service_status'
                ),

            models.Index(
                fields=['created_at'],
                name='idx_created_at'
                ),

            models.Index(fields=['status']),

            models.Index(
                    fields=['status'],
                    condition=models.Q(status='error'),
                    name='idx_error_logs'
                ),

            models.Index(
                    fields=['service', 'created_at'],
                    name='idx_service_created',
                )
        ]

    def __str__(self):
        return f"{self.service.name} - {self.status}"