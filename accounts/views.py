from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect, render

from .decorators import role_required
from .forms import LoginForm, RegistrationForm
from .models import Account


def home(request):
    """Public landing page."""
    return render(request, "home.html")


def register(request):
    """Public registration. Creates a vehicle OWNER account."""
    if request.user.is_authenticated:
        return redirect("dashboard")

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


# Dashboards

@login_required
def dashboard(request):
    """Send each user to the dashboard for their role."""
    if request.user.is_admin_role:
        return redirect("admin_dashboard")
    if request.user.is_guard_role:
        return redirect("guard_dashboard")
    return redirect("owner_dashboard")


@login_required
@role_required(Account.Role.ADMIN)
def admin_dashboard(request):
    accounts = Account.objects.all()
    context = {
        "owner_count": accounts.filter(role=Account.Role.OWNER).count(),
        "guard_count": accounts.filter(role=Account.Role.GUARD).count(),
        "admin_count": accounts.filter(role=Account.Role.ADMIN).count(),
        "inactive_count": accounts.filter(is_active=False).count(),
    }
    return render(request, "dashboards/admin.html", context)


@login_required
@role_required(Account.Role.GUARD)
def guard_dashboard(request):
    return render(request, "dashboards/guard.html")


@login_required
@role_required(Account.Role.OWNER)
def owner_dashboard(request):
    return render(request, "dashboards/owner.html")
