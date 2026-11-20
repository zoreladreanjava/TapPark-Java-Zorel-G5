from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from accounts.decorators import role_required
from accounts.models import Account

from .forms import ParkingAreaForm
from .models import ParkingArea


# Parking areas (admins only)

@login_required
@role_required(Account.Role.ADMIN)
def area_list(request):
    areas = ParkingArea.objects.select_related("created_by")
    return render(request, "parking/area_list.html", {"areas": areas})


@login_required
@role_required(Account.Role.ADMIN)
def area_create(request):
    if request.method == "POST":
        form = ParkingAreaForm(request.POST)
        if form.is_valid():
            area = form.save(commit=False)
            area.created_by = request.user
            area.save()
            messages.success(request, f"Parking area \"{area.name}\" added.")
            return redirect("area_list")
    else:
        form = ParkingAreaForm()
    return render(request, "parking/area_form.html", {"form": form, "is_new": True})


@login_required
@role_required(Account.Role.ADMIN)
def area_edit(request, pk):
    area = get_object_or_404(ParkingArea, pk=pk)
    if request.method == "POST":
        form = ParkingAreaForm(request.POST, instance=area)
        if form.is_valid():
            form.save()
            messages.success(request, f"Parking area \"{area.name}\" updated.")
            return redirect("area_list")
    else:
        form = ParkingAreaForm(instance=area)
    return render(request, "parking/area_form.html", {"form": form, "area": area, "is_new": False})


@login_required
@role_required(Account.Role.ADMIN)
def area_delete(request, pk):
    """GET shows a confirmation page; POST deletes the area."""
    area = get_object_or_404(ParkingArea, pk=pk)
    if request.method == "POST":
        name = area.name
        area.delete()
        messages.success(request, f"Parking area \"{name}\" removed.")
        return redirect("area_list")
    return render(request, "parking/area_confirm_delete.html", {"area": area})
