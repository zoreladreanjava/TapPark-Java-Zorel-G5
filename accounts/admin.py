from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Account


@admin.register(Account)
class AccountAdmin(UserAdmin):
    list_display = ("username", "email", "first_name", "last_name", "role", "is_active")
    list_filter = ("role", "is_active", "is_staff")
    search_fields = ("username", "email", "first_name", "last_name")

    # Add TapPark fields to the edit page and the "add user" page.
    fieldsets = UserAdmin.fieldsets + (
        ("TapPark", {"fields": ("role", "contact_number", "profile_photo")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("TapPark", {"fields": ("email", "first_name", "last_name", "role", "contact_number")}),
    )
