from django.shortcuts import render


def home(request):
    """Public landing page."""
    return render(request, "home.html")
