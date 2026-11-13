from django.contrib import messages
from django.shortcuts import redirect, render

from .forms import RegistrationForm


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
            # Changed to redirect("login") once the login page exists (chunk 5).
            return redirect("home")
    else:
        form = RegistrationForm()

    return render(request, "accounts/register.html", {"form": form})
