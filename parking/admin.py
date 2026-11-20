from django.contrib import admin

from .models import ParkingArea


@admin.register(ParkingArea)
class ParkingAreaAdmin(admin.ModelAdmin):
    list_display = ("name", "capacity", "created_by", "updated_at")
    search_fields = ("name",)
