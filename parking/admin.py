from django.contrib import admin

from .models import EntryLog, ExitLog, ParkingArea, Vehicle, VehicleOwner


@admin.register(ParkingArea)
class ParkingAreaAdmin(admin.ModelAdmin):
    list_display = ("name", "capacity", "created_by", "updated_at")
    search_fields = ("name",)


@admin.register(VehicleOwner)
class VehicleOwnerAdmin(admin.ModelAdmin):
    list_display = ("account", "id_number", "owner_type")
    search_fields = ("id_number", "account__username", "account__last_name")


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ("plate_number", "vehicle_type", "owner")
    list_filter = ("vehicle_type",)
    search_fields = ("plate_number",)


@admin.register(EntryLog)
class EntryLogAdmin(admin.ModelAdmin):
    list_display = ("vehicle", "area", "entry_time", "status", "recorded_by")
    list_filter = ("status", "area")


@admin.register(ExitLog)
class ExitLogAdmin(admin.ModelAdmin):
    list_display = ("entry", "exit_time", "recorded_by")
