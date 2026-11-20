from django import forms

from accounts.forms import BootstrapFormMixin

from .models import ParkingArea, Vehicle, VehicleOwner


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
