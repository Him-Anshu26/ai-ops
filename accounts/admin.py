from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

# Register your models here.
@admin.register(User)
class CustomUserAdmin(UserAdmin):
    model = User
    list_display = ('id', 'email', 'first_name', 'is_active', 'is_staff', 'is_superuser', 'is_verified', 'created_at', 'updated_at')
    search_fields = ('email', 'first_name')
    list_filter = ('is_active', 'is_staff', 'is_verified')

    ordering = ('id',)

    readonly_fields = ('created_at', 'updated_at')

    filter_horizontal = (
            "groups",
            "user_permissions",
        )

    date_hierarchy = 'created_at'
    


    # UserAdmin.fieldsets already contains email, so we don't need to append it again. But if we want to customize the fieldsets, we can do it like this:
    # fieldsets = UserAdmin.fieldsets + (
    # (None, {'fields': ('email',)}),
    # )

    # fieldsets = UserAdmin.fieldsets + (
    # ('Extra Info', {'fields': ('avatar',)}),
    # )


    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("first_name",)}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (
            "Important dates",
            {
                "fields": (
                    "last_login",
                    "created_at",
                    "updated_at",
                )
            },
        ),
        (
            "Verification",
            {
                "fields": (
                    "is_verified",
                )
            },
        ),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "first_name",
                    "password1",
                    "password2",
                    "is_verified",
                ),
            },
        ),
    )
