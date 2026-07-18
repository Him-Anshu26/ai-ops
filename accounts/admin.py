from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

# Register your models here.
@admin.register(User)
class CustomUserAdmin(UserAdmin):
    model = User
    list_display = ('id', 'username', 'email', 'first_name', 'is_active', 'is_staff', 'is_superuser', 'is_verified', 'created_at', 'updated_at')
    search_fields = ('username', 'email')
    list_filter = ('is_active', 'is_staff', 'is_verified')

    ordering = ('id',)

    readonly_fields = ('created_at', 'updated_at')

    date_hierarchy = 'created_at'
    


    # UserAdmin.fieldsets already contains email, so we don't need to append it again. But if we want to customize the fieldsets, we can do it like this:
    # fieldsets = UserAdmin.fieldsets + (
    # (None, {'fields': ('email',)}),
    # )

    # fieldsets = UserAdmin.fieldsets + (
    # ('Extra Info', {'fields': ('avatar',)}),
    # )


    fieldsets = UserAdmin.fieldsets + (
        ('Custom Fields', {
            'fields': ('is_verified', 'created_at', 'updated_at')
        }),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {
            'fields': ('email', 'is_verified')
        }),
    )