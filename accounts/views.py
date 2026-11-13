from django.contrib import messages
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect, render

from .forms import LoginForm, RegistrationForm


def home(request):
    """Public landing page."""
    return render(request, "home.html")


def register(request):
    """Public registration. Creates a vehicle OWNER account."""
    if request.user.is_authenticated:
        # Changed to redirect("dashboard") once dashboards exist (chunk 6).
        return redirect("home")

    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Account created. You can now log in.")
            return redirect("login")
    else:
        form = RegistrationForm()

    return render(request, "accounts/register.html", {"form": form})


class TapParkLoginView(LoginView):
    """Django's LoginView with our template and form.

    Logged-in users who open /login/ are sent to LOGIN_REDIRECT_URL.
    """

    template_name = "accounts/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True


class TapParkLogoutView(LogoutView):
    """Logs the user out (POST only, as Django 5 requires) and shows a message."""

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        messages.info(request, "You have been logged out.")
        return response
