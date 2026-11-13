from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView, PasswordChangeView
from django.shortcuts import redirect, render
from django.urls import reverse_lazy

from .decorators import role_required
from .forms import LoginForm, ProfileForm, RegistrationForm, TapParkPasswordChangeForm
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


# Profile
# These views never take a user ID from the URL. They always use request.user,
# so a user can only see and change their own profile.

@login_required
def profile(request):
    return render(request, "accounts/profile.html")


@login_required
def profile_edit(request):
    # Edit a fresh copy of the account. If the form has errors, request.user
    # (shown in the navbar) keeps its saved values instead of the bad input.
    account = Account.objects.get(pk=request.user.pk)

    if request.method == "POST":
        form = ProfileForm(request.POST, request.FILES, instance=account)
        if form.is_valid():
            form.save()
            messages.success(request, "Your profile has been updated.")
            return redirect("profile")
    else:
        form = ProfileForm(instance=account)

    return render(request, "accounts/profile_edit.html", {"form": form})


class TapParkPasswordChangeView(PasswordChangeView):
    """Django's PasswordChangeView. It keeps the user logged in after the change."""

    template_name = "accounts/password_change.html"
    form_class = TapParkPasswordChangeForm
    success_url = reverse_lazy("profile")

    def form_valid(self, form):
        messages.success(self.request, "Your password has been changed.")
        return super().form_valid(form)
