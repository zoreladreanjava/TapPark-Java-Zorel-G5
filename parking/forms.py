from django import forms
from django.utils import timezone

from accounts.forms import BootstrapFormMixin

from .models import EntryLog, ParkingArea, Vehicle, VehicleOwner


class ParkingAreaForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = ParkingArea
        fields = ("name", "capacity")
        labels = {"name": "Area name", "capacity": "Capacity (slots)"}
        help_texts = {"name": "For example: Area A, or Motorcycle Lot."}
        error_messages = {
            "name": {"required": "Enter the area name."},
            "capacity": {
                "required": "Enter the area's capacity.",
                "invalid": "Capacity must be a whole number.",
                "min_value": "Capacity must be at least 1.",
                "max_value": "Capacity can't be more than 1000.",
            },
        }

    def clean_name(self):
        name = " ".join(self.cleaned_data["name"].split())  # tidy extra spaces
        others = ParkingArea.objects.filter(name__iexact=name).exclude(pk=self.instance.pk)
        if others.exists():
            raise forms.ValidationError("A parking area with this name already exists.")
        return name

    def clean_capacity(self):
        capacity = self.cleaned_data["capacity"]
        if self.instance.pk:
            parked = self.instance.parked_count()
            if capacity < parked:
                raise forms.ValidationError(
                    f"Capacity can't be lower than the {parked} vehicle{'s' if parked != 1 else ''} parked here now."
                )
        return capacity


class VehicleOwnerForm(BootstrapFormMixin, forms.ModelForm):
    """The owner's campus ID number and owner type."""

    class Meta:
        model = VehicleOwner
        fields = ("id_number", "owner_type")
        labels = {"id_number": "Campus ID number", "owner_type": "I am a"}
        help_texts = {"id_number": "The number on your campus ID. Guards use it to find your vehicles at the gate."}
        error_messages = {
            "id_number": {
                "required": "Enter your campus ID number.",
                "unique": "This ID number is already registered to another owner.",
            },
        }

    def clean_id_number(self):
        return self.cleaned_data["id_number"].strip().upper()


class VehicleForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Vehicle
        fields = ("plate_number", "vehicle_type", "description")
        labels = {"description": "Description (optional)"}
        error_messages = {
            "plate_number": {"required": "Enter the plate number."},
            "vehicle_type": {"required": "Choose the vehicle type."},
        }

    def clean_plate_number(self):
        # Store plates in capitals with single spaces, so "abc  1234" becomes "ABC 1234".
        plate = " ".join(self.cleaned_data["plate_number"].upper().split())
        others = Vehicle.objects.filter(plate_number__iexact=plate).exclude(pk=self.instance.pk)
        if others.exists():
            raise forms.ValidationError("This plate number is already registered.")
        return plate


def area_has_room(area, ignore_entry=None):
    """True if the area has a free slot. `ignore_entry` is left out of the count (used when correcting)."""
    active = area.entries.filter(status=EntryLog.Status.ACTIVE)
    if ignore_entry is not None:
        active = active.exclude(pk=ignore_entry.pk)
    return active.count() < area.capacity


class CheckInForm(forms.Form):
    """Guard records a vehicle entering. The owner chooses the area."""

    area = forms.ModelChoiceField(
        queryset=ParkingArea.objects.all(),
        error_messages={"required": "Choose a parking area.", "invalid_choice": "Choose a valid parking area."},
    )

    def __init__(self, *args, vehicle, **kwargs):
        super().__init__(*args, **kwargs)
        self.vehicle = vehicle

    def clean(self):
        cleaned_data = super().clean()
        area = cleaned_data.get("area")
        if self.vehicle.active_entry():
            raise forms.ValidationError(f"{self.vehicle.plate_number} is already recorded inside. Check it out first.")
        if area and not area_has_room(area):
            raise forms.ValidationError(f"{area.name} is full. Ask the owner to choose another area.")
        return cleaned_data


class EntryCorrectionForm(BootstrapFormMixin, forms.ModelForm):
    """Correct the area or entry time of an entry that is still active."""

    class Meta:
        model = EntryLog
        fields = ("area", "entry_time")
        labels = {"area": "Parking area", "entry_time": "Entry time"}
        widgets = {
            "entry_time": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
        }
        error_messages = {
            "area": {"required": "Choose a parking area."},
            "entry_time": {"required": "Enter the entry time.", "invalid": "Enter a valid date and time."},
        }

    def clean_entry_time(self):
        entry_time = self.cleaned_data["entry_time"]
        if entry_time > timezone.now():
            raise forms.ValidationError("The entry time can't be in the future.")
        return entry_time

    def clean_area(self):
        area = self.cleaned_data["area"]
        if area.pk != self.instance.area_id and not area_has_room(area, ignore_entry=self.instance):
            raise forms.ValidationError(f"{area.name} is full. Choose another area.")
        return area
