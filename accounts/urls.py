from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("register/", views.register, name="register"),
    path("login/", views.TapParkLoginView.as_view(), name="login"),
    path("logout/", views.TapParkLogoutView.as_view(), name="logout"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("dashboard/admin/", views.admin_dashboard, name="admin_dashboard"),
    path("dashboard/guard/", views.guard_dashboard, name="guard_dashboard"),
    path("dashboard/owner/", views.owner_dashboard, name="owner_dashboard"),
]
