from django import forms

from accounts.forms import BootstrapFormMixin

from .models import ParkingArea


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
