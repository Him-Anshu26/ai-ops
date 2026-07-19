from django.contrib import admin, messages

from .models import Alert, AlertStatus


@admin.action(description="Mark selected alerts as Open")
def mark_open(modeladmin, request, queryset):
    updated = queryset.update(
        status=AlertStatus.OPEN,
        resolved_at=None,
    )
    modeladmin.message_user(
        request,
        f"{updated} alert(s) marked as open.",
        messages.SUCCESS,
    )


@admin.action(description="Mark selected alerts as Acknowledged")
def mark_acknowledged(modeladmin, request, queryset):
    updated = queryset.update(status=AlertStatus.ACKNOWLEDGED)
    modeladmin.message_user(
        request,
        f"{updated} alert(s) acknowledged.",
        messages.INFO,
    )


@admin.action(description="Mark selected alerts as Resolved")
def mark_resolved(modeladmin, request, queryset):
    from django.utils import timezone

    updated = queryset.update(
        status=AlertStatus.RESOLVED,
        resolved_at=timezone.now(),
    )
    modeladmin.message_user(
        request,
        f"{updated} alert(s) resolved.",
        messages.SUCCESS,
    )


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "service",
        "alert_type",
        "severity",
        "status",
        "trigger_count",
        "last_triggered_at",
        "created_at",
    )

    list_select_related = (
        "service",
        "log",
    )

    list_filter = (
        "status",
        "severity",
        "alert_type",
        "service",
        "created_at",
    )

    search_fields = (
        "service__name",
        "message",
        "alert_key",
    )

    readonly_fields = (
        "created_at",
        "last_triggered_at",
    )

    ordering = ("-last_triggered_at",)

    date_hierarchy = "created_at"

    list_per_page = 50

    actions = (
        mark_open,
        mark_acknowledged,
        mark_resolved,
    )

    autocomplete_fields = (
        "service",
        "log",
    )

    fieldsets = (
        (
            "Alert Information",
            {
                "fields": (
                    "service",
                    "log",
                    "alert_type",
                    "message",
                    "alert_key",
                )
            },
        ),
        (
            "Status",
            {
                "fields": (
                    "severity",
                    "status",
                    "trigger_count",
                )
            },
        ),
        (
            "Resolution",
            {
                "fields": (
                    "resolved_at",
                    "resolution_note",
                )
            },
        ),
        (
            "Timestamps",
            {
                "fields": (
                    "created_at",
                    "last_triggered_at",
                )
            },
        ),
    )