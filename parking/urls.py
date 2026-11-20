from django.urls import path

from . import views

urlpatterns = [
    # Admin: parking areas
    path("dashboard/admin/areas/", views.area_list, name="area_list"),
    path("dashboard/admin/areas/new/", views.area_create, name="area_create"),
    path("dashboard/admin/areas/<int:pk>/edit/", views.area_edit, name="area_edit"),
    path("dashboard/admin/areas/<int:pk>/delete/", views.area_delete, name="area_delete"),
    # Admin: all owners and vehicles (read-only)
    path("dashboard/admin/vehicles/", views.admin_vehicle_list, name="admin_vehicle_list"),
    # Owner: My Vehicles
    path("dashboard/owner/vehicles/", views.my_vehicles, name="my_vehicles"),
    path("dashboard/owner/vehicles/details/", views.owner_details_edit, name="owner_details_edit"),
    path("dashboard/owner/vehicles/new/", views.vehicle_create, name="vehicle_create"),
    path("dashboard/owner/vehicles/<int:pk>/edit/", views.vehicle_edit, name="vehicle_edit"),
    path("dashboard/owner/vehicles/<int:pk>/delete/", views.vehicle_delete, name="vehicle_delete"),
]
