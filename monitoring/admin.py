from django.contrib import messages
from django.utils.safestring import mark_safe
import json

from django.contrib import admin
from .models import Service, Log


@admin.action(description='Mark selected services as active')
def make_active(modeladmin, request, queryset):
    updated = queryset.update(status='active')
    modeladmin.message_user(request, f"{updated} service(s) marked as active.",
    messages.SUCCESS
    )


@admin.action(description='Mark selected services as down')
def make_down(modeladmin, request, queryset):
    updated = queryset.update(status='down')
    modeladmin.message_user(request, f"{updated} service(s) marked as down.",
    messages.WARNING
    )


@admin.action(description='Mark selected services as maintenance')
def make_maintenance(modeladmin, request, queryset):
    updated = queryset.update(status='maintenance')
    modeladmin.message_user(request, f"{updated} service(s) marked as maintenance.",
    messages.INFO
    )


# Register your models here.
@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'slug', 'status', 'created_by', 'is_deleted', 'created_at')

    list_select_related = ('created_by',)
    list_filter = ('status', 'is_deleted', 'created_by')
    search_fields = ('name', 'description', 'created_by__username')
    readonly_fields = ('created_at', 'updated_at', 'slug',)

    ordering = ('-created_at',)

    actions = [make_active, make_down, make_maintenance]

    exclude = ('created_by',)

    date_hierarchy = 'created_at'

    list_per_page = 20


    def save_model(self, request, obj, form, change):
        if not change:  # Only set created_by on creation
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


 
    

@admin.register(Log)
class LogAdmin(admin.ModelAdmin):
    list_display = ('service','short_message', 'status', 'severity','status_code','response_time_ms',  'created_at')
    list_select_related = ('service',)
    list_filter = ('status', 'service', 'severity', 'created_at')
    search_fields = ('service__name',)
    readonly_fields = ('created_at','service', 'status', 'severity','status_code','response_time_ms', 'formatted_metadata', 'message')

    list_per_page = 50

    date_hierarchy = 'created_at'

    ordering = ('-created_at',)


    def has_change_permission(self, request, obj=None):
        return False
    

    def has_delete_permission(self, request, obj=None):
        return False
    

    def formatted_metadata(self, obj):
        if not obj.metadata:
            return "-"
        formatted = json.dumps(obj.metadata, indent=2)
        return mark_safe(f"<pre>{formatted}</pre>")

    formatted_metadata.short_description = "Metadata"




    def has_add_permission(self, request):
        return False
    


    def short_message(self, obj):
        return (obj.message[:40] + '...') if len(obj.message) > 40 else obj.message

    short_message.short_description = "Message"