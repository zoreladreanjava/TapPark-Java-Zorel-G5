from django.urls import path

from . import views

urlpatterns = [
    # Admin: parking areas
    path("dashboard/admin/areas/", views.area_list, name="area_list"),
    path("dashboard/admin/areas/new/", views.area_create, name="area_create"),
    path("dashboard/admin/areas/<int:pk>/edit/", views.area_edit, name="area_edit"),
    path("dashboard/admin/areas/<int:pk>/delete/", views.area_delete, name="area_delete"),
    # Admin: all owners and vehicles (read-only) and all parking records
    path("dashboard/admin/vehicles/", views.admin_vehicle_list, name="admin_vehicle_list"),
    path("dashboard/admin/history/", views.admin_history, name="admin_history"),
    # Owner: My Vehicles, availability, own history
    path("dashboard/owner/vehicles/", views.my_vehicles, name="my_vehicles"),
    path("dashboard/owner/vehicles/details/", views.owner_details_edit, name="owner_details_edit"),
    path("dashboard/owner/vehicles/new/", views.vehicle_create, name="vehicle_create"),
    path("dashboard/owner/vehicles/<int:pk>/edit/", views.vehicle_edit, name="vehicle_edit"),
    path("dashboard/owner/vehicles/<int:pk>/delete/", views.vehicle_delete, name="vehicle_delete"),
    path("dashboard/owner/availability/", views.owner_availability, name="owner_availability"),
    path("dashboard/owner/history/", views.owner_history, name="owner_history"),
    # Guard: gate actions (the gate screen itself is /dashboard/guard/)
    path("dashboard/guard/check-in/<int:vehicle_pk>/", views.check_in, name="check_in"),
    path("dashboard/guard/check-out/<int:entry_pk>/", views.check_out, name="check_out"),
    # Guard (own entries) or admin (any entry): correct or undo an active entry
    path("entries/<int:pk>/edit/", views.entry_edit, name="entry_edit"),
    path("entries/<int:pk>/delete/", views.entry_delete, name="entry_delete"),
]
