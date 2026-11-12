from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User, UserProfile


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "email", "role", "is_active", "is_staff", "date_joined")
    list_filter = ("role", "is_active", "is_staff")
    search_fields = ("username", "email", "phone_number")

    fieldsets = BaseUserAdmin.fieldsets + (
        ("Marketplace info", {"fields": ("role", "phone_number")}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ("Marketplace info", {"fields": ("email", "role", "phone_number")}),
    )
    inlines = [UserProfileInline]

    def get_inline_instances(self, request, obj=None):
        # Add page par inline mat dikhao: signal profile pehle hi bana deta hai
        if obj is None:
            return []
        return super().get_inline_instances(request, obj)