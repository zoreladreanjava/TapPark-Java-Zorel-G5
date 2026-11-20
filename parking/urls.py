from django.urls import path

from . import views

urlpatterns = [
    path("dashboard/admin/areas/", views.area_list, name="area_list"),
    path("dashboard/admin/areas/new/", views.area_create, name="area_create"),
    path("dashboard/admin/areas/<int:pk>/edit/", views.area_edit, name="area_edit"),
    path("dashboard/admin/areas/<int:pk>/delete/", views.area_delete, name="area_delete"),
]
