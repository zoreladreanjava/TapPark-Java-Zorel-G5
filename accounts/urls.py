from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("register/", views.register, name="register"),
    path("login/", views.TapParkLoginView.as_view(), name="login"),
    path("logout/", views.TapParkLogoutView.as_view(), name="logout"),
]
