from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("register/", views.register, name="register"),
    path("login/", views.TapParkLoginView.as_view(), name="login"),
    path("logout/", views.TapParkLogoutView.as_view(), name="logout"),
    path("profile/", views.profile, name="profile"),
    path("profile/edit/", views.profile_edit, name="profile_edit"),
    path("profile/password/", views.TapParkPasswordChangeView.as_view(), name="password_change"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("dashboard/admin/", views.admin_dashboard, name="admin_dashboard"),
    path("dashboard/admin/staff/", views.staff_list, name="staff_list"),
    path("dashboard/admin/staff/new/", views.staff_create, name="staff_create"),
    path("dashboard/admin/staff/<int:pk>/toggle/", views.staff_toggle, name="staff_toggle"),
    path("dashboard/guard/", views.guard_dashboard, name="guard_dashboard"),
    path("dashboard/owner/", views.owner_dashboard, name="owner_dashboard"),
]
