from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from accounts.decorators import role_required
from accounts.models import Account

from .forms import ParkingAreaForm, VehicleForm, VehicleOwnerForm
from .models import ParkingArea, Vehicle, VehicleOwner


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


# My Vehicles (owners manage only their own records)
# Vehicles are always looked up through request.user, so an owner who types
# another owner's vehicle ID in the URL gets 404.

def get_own_vehicle(request, pk):
    return get_object_or_404(Vehicle, pk=pk, owner__account=request.user)


@login_required
@role_required(Account.Role.OWNER)
def my_vehicles(request):
    owner = VehicleOwner.objects.filter(account=request.user).first()
    vehicles = owner.vehicles.all() if owner else []
    return render(request, "parking/my_vehicles.html", {"owner": owner, "vehicles": vehicles})


@login_required
@role_required(Account.Role.OWNER)
def owner_details_edit(request):
    """Create or update the owner's campus ID number and owner type."""
    owner = VehicleOwner.objects.filter(account=request.user).first()
    if request.method == "POST":
        form = VehicleOwnerForm(request.POST, instance=owner)
        if form.is_valid():
            details = form.save(commit=False)
            details.account = request.user
            details.save()
            messages.success(request, "Your owner details have been saved.")
            return redirect("my_vehicles")
    else:
        form = VehicleOwnerForm(instance=owner)
    return render(request, "parking/owner_details_form.html", {"form": form, "owner": owner})


@login_required
@role_required(Account.Role.OWNER)
def vehicle_create(request):
    owner = VehicleOwner.objects.filter(account=request.user).first()
    if owner is None:
        messages.error(request, "Add your campus ID number first, then register your vehicle.")
        return redirect("owner_details_edit")

    if request.method == "POST":
        form = VehicleForm(request.POST)
        if form.is_valid():
            vehicle = form.save(commit=False)
            vehicle.owner = owner
            vehicle.save()
            messages.success(request, f"Vehicle {vehicle.plate_number} registered.")
            return redirect("my_vehicles")
    else:
        form = VehicleForm()
    return render(request, "parking/vehicle_form.html", {"form": form, "is_new": True})


@login_required
@role_required(Account.Role.OWNER)
def vehicle_edit(request, pk):
    vehicle = get_own_vehicle(request, pk)
    if request.method == "POST":
        form = VehicleForm(request.POST, instance=vehicle)
        if form.is_valid():
            form.save()
            messages.success(request, f"Vehicle {vehicle.plate_number} updated.")
            return redirect("my_vehicles")
    else:
        form = VehicleForm(instance=vehicle)
    return render(request, "parking/vehicle_form.html", {"form": form, "vehicle": vehicle, "is_new": False})


@login_required
@role_required(Account.Role.OWNER)
def vehicle_delete(request, pk):
    """GET shows a confirmation page; POST removes the vehicle."""
    vehicle = get_own_vehicle(request, pk)
    if request.method == "POST":
        plate = vehicle.plate_number
        vehicle.delete()
        messages.success(request, f"Vehicle {plate} removed.")
        return redirect("my_vehicles")
    return render(request, "parking/vehicle_confirm_delete.html", {"vehicle": vehicle})


# Owners & vehicles overview (admins only, read-only)

@login_required
@role_required(Account.Role.ADMIN)
def admin_vehicle_list(request):
    vehicles = Vehicle.objects.select_related("owner__account")
    query = request.GET.get("q", "").strip()
    if query:
        vehicles = vehicles.filter(
            Q(plate_number__icontains=query)
            | Q(owner__id_number__icontains=query)
            | Q(owner__account__first_name__icontains=query)
            | Q(owner__account__last_name__icontains=query)
        )
    return render(request, "parking/admin_vehicle_list.html", {"vehicles": vehicles, "query": query})
