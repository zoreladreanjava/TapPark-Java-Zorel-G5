from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.decorators import role_required
from accounts.models import Account

from .forms import CheckInForm, EntryCorrectionForm, ParkingAreaForm, VehicleForm, VehicleOwnerForm
from .models import EntryLog, ExitLog, ParkingArea, Vehicle, VehicleOwner


# Parking areas (admins only)

@login_required
@role_required(Account.Role.ADMIN)
def area_list(request):
    areas = ParkingArea.objects.with_counts().select_related("created_by")
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

    # Parking records must be kept, so an area that has any can't be removed.
    blocked_reason = None
    if area.parked_count():
        blocked_reason = f"{area.name} can't be removed while vehicles are parked in it."
    elif area.entries.exists():
        blocked_reason = f"{area.name} has parking history, which must be kept. Lower its capacity instead."

    if blocked_reason:
        if request.method == "POST":
            messages.error(request, blocked_reason)
            return redirect("area_list")
        return render(request, "parking/area_confirm_delete.html", {"area": area, "blocked_reason": blocked_reason})

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

    blocked_reason = None
    if vehicle.active_entry():
        blocked_reason = f"{vehicle.plate_number} can't be removed while it is recorded inside a parking area."
    elif vehicle.entries.exists():
        blocked_reason = f"{vehicle.plate_number} has parking history, which must be kept, so it can't be removed."

    if blocked_reason:
        if request.method == "POST":
            messages.error(request, blocked_reason)
            return redirect("my_vehicles")
        return render(request, "parking/vehicle_confirm_delete.html", {"vehicle": vehicle, "blocked_reason": blocked_reason})

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


# Vehicle entry and exit (the core feature)

def parking_summary():
    """Campus-wide numbers for the dashboards."""
    areas = list(ParkingArea.objects.with_counts())
    capacity = sum(area.capacity for area in areas)
    parked = sum(area.parked for area in areas)
    today = timezone.localdate()
    return {
        "areas": sorted(areas, key=lambda area: area.free, reverse=True),
        "total_capacity": capacity,
        "total_parked": parked,
        "total_free": max(capacity - parked, 0),
        "entries_today": EntryLog.objects.filter(entry_time__date=today).count(),
    }


def find_vehicles(query):
    """Vehicles matching a campus ID number (exact) or a plate number (exact or partial)."""
    plate = " ".join(query.upper().split())
    matches = Q(owner__id_number__iexact=query) | Q(plate_number__iexact=plate)
    if len(plate) >= 3:
        matches |= Q(plate_number__icontains=plate)
    vehicles = Vehicle.objects.filter(matches).select_related("owner__account")[:20]
    return [(vehicle, vehicle.active_entry()) for vehicle in vehicles]


def gate_context(request):
    """Everything the guard's gate screen shows."""
    query = request.GET.get("q", "").strip()
    context = parking_summary()
    context.update({
        "query": query,
        "results": find_vehicles(query) if query else None,
        "parked_now": EntryLog.objects.filter(status=EntryLog.Status.ACTIVE)
        .select_related("vehicle__owner__account", "area", "recorded_by")[:50],
    })
    return context


def back_to_gate(query=""):
    url = reverse("guard_dashboard")
    return redirect(f"{url}?{urlencode({'q': query})}" if query else url)


@login_required
@role_required(Account.Role.GUARD)
@require_POST
def check_in(request, vehicle_pk):
    """Guard records a vehicle entering the area the owner chose."""
    vehicle = get_object_or_404(Vehicle, pk=vehicle_pk)
    query = request.POST.get("q", "")
    form = CheckInForm(request.POST, vehicle=vehicle)
    if not form.is_valid():
        for errors in form.errors.values():
            for error in errors:
                messages.error(request, error)
        return back_to_gate(query)

    area = form.cleaned_data["area"]
    try:
        with transaction.atomic():
            EntryLog.objects.create(vehicle=vehicle, area=area, recorded_by=request.user)
    except IntegrityError:
        # The database allows only one active entry per vehicle.
        messages.error(request, f"{vehicle.plate_number} is already recorded inside.")
        return back_to_gate(query)
    messages.success(request, f"Entry recorded: {vehicle.plate_number} parked in {area.name}.")
    return back_to_gate()


@login_required
@role_required(Account.Role.GUARD)
@require_POST
def check_out(request, entry_pk):
    """Guard records a vehicle leaving. This closes its active entry."""
    entry = get_object_or_404(EntryLog, pk=entry_pk, status=EntryLog.Status.ACTIVE)
    with transaction.atomic():
        ExitLog.objects.create(entry=entry, recorded_by=request.user)
        entry.status = EntryLog.Status.CLOSED
        entry.save(update_fields=["status"])
    messages.success(request, f"Exit recorded: {entry.vehicle.plate_number} left {entry.area.name}.")
    return back_to_gate()


def get_changeable_entry(request, pk):
    """An entry the user may correct or undo, or 403."""
    entry = get_object_or_404(EntryLog.objects.select_related("vehicle", "area"), pk=pk)
    if not entry.can_be_changed_by(request.user):
        raise PermissionDenied
    return entry


def after_entry_change(request):
    return redirect("admin_history" if request.user.is_admin_role else "guard_dashboard")


@login_required
@role_required(Account.Role.GUARD, Account.Role.ADMIN)
def entry_edit(request, pk):
    """Correct the area or entry time of an active entry."""
    entry = get_changeable_entry(request, pk)
    if request.method == "POST":
        form = EntryCorrectionForm(request.POST, instance=entry)
        if form.is_valid():
            form.save()
            messages.success(request, f"Entry for {entry.vehicle.plate_number} corrected.")
            return after_entry_change(request)
    else:
        form = EntryCorrectionForm(instance=entry)
    return render(request, "parking/entry_form.html", {"form": form, "entry": entry})


@login_required
@role_required(Account.Role.GUARD, Account.Role.ADMIN)
def entry_delete(request, pk):
    """Undo an entry recorded by mistake. GET asks to confirm; POST deletes it."""
    entry = get_changeable_entry(request, pk)
    if request.method == "POST":
        plate = entry.vehicle.plate_number
        entry.delete()
        messages.success(request, f"Entry for {plate} undone. The slot is free again.")
        return after_entry_change(request)
    return render(request, "parking/entry_confirm_delete.html", {"entry": entry})


@login_required
@role_required(Account.Role.OWNER)
def owner_availability(request):
    return render(request, "parking/availability.html", parking_summary())


@login_required
@role_required(Account.Role.OWNER)
def owner_history(request):
    """The owner's own parking records only."""
    entries = (
        EntryLog.objects.filter(vehicle__owner__account=request.user)
        .select_related("vehicle", "area", "exit")
    )
    return render(request, "parking/owner_history.html", {"entries": entries})


@login_required
@role_required(Account.Role.ADMIN)
def admin_history(request):
    """All parking records, with a search and an Inside / Exited filter."""
    entries = EntryLog.objects.select_related(
        "vehicle__owner__account", "area", "recorded_by", "exit__recorded_by"
    )
    query = request.GET.get("q", "").strip()
    if query:
        entries = entries.filter(
            Q(vehicle__plate_number__icontains=query)
            | Q(vehicle__owner__id_number__icontains=query)
            | Q(vehicle__owner__account__last_name__icontains=query)
        )
    status = request.GET.get("status", "")
    if status in EntryLog.Status.values:
        entries = entries.filter(status=status)
    else:
        status = ""
    context = {
        "entries": entries[:200],
        "query": query,
        "status": status,
        "status_choices": EntryLog.Status.choices,
    }
    return render(request, "parking/admin_history.html", context)
