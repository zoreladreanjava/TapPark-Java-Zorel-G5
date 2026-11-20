from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models
from django.db.models.functions import Lower, Upper

# Campus ID numbers: letters, digits and dashes, e.g. 23-1234-567.
id_number_validator = RegexValidator(
    regex=r"^[A-Za-z0-9-]{4,20}$",
    message="Use 4 to 20 letters, digits or dashes, e.g. 23-1234-567.",
)

# Plates: groups of letters/digits separated by single spaces or dashes,
# e.g. ABC 1234, MC-1234, 1234-AB.
plate_number_validator = RegexValidator(
    regex=r"^[A-Z0-9]+([ -][A-Z0-9]+)*$",
    message="Use letters and digits separated by single spaces or dashes, e.g. ABC 1234 or MC-1234.",
)


class ParkingArea(models.Model):
    """A campus parking area (e.g. "Area A") and how many vehicles it holds."""

    name = models.CharField(max_length=50)
    capacity = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(1000)],
        help_text="Total number of parking slots in this area.",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="parking_areas_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "parking_area"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(Lower("name"), name="parking_area_name_ci_unique"),
            models.CheckConstraint(condition=models.Q(capacity__gte=1), name="parking_area_capacity_positive"),
        ]

    def __str__(self):
        return self.name


class VehicleOwner(models.Model):
    """Parking details of an OWNER account: their campus ID number and type."""

    class OwnerType(models.TextChoices):
        STUDENT = "STUDENT", "Student"
        FACULTY = "FACULTY", "Faculty"
        EMPLOYEE = "EMPLOYEE", "Employee"

    account = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="vehicle_owner",
    )
    id_number = models.CharField("campus ID number", max_length=20, unique=True, validators=[id_number_validator])
    owner_type = models.CharField(max_length=10, choices=OwnerType.choices, default=OwnerType.STUDENT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "vehicle_owner"
        ordering = ["account__last_name", "account__first_name"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(owner_type__in=["STUDENT", "FACULTY", "EMPLOYEE"]),
                name="vehicle_owner_type_valid",
            ),
        ]

    def __str__(self):
        return f"{self.account.get_full_name() or self.account.username} ({self.id_number})"


class Vehicle(models.Model):
    """A vehicle registered by its owner."""

    class VehicleType(models.TextChoices):
        CAR = "CAR", "Car"
        MOTORCYCLE = "MOTORCYCLE", "Motorcycle"

    owner = models.ForeignKey(VehicleOwner, on_delete=models.CASCADE, related_name="vehicles")
    plate_number = models.CharField(max_length=12, validators=[plate_number_validator])
    vehicle_type = models.CharField(max_length=10, choices=VehicleType.choices)
    description = models.CharField(max_length=60, blank=True, help_text="Optional, e.g. Red Honda Click.")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "vehicle"
        ordering = ["plate_number"]
        constraints = [
            models.UniqueConstraint(Upper("plate_number"), name="vehicle_plate_ci_unique"),
            models.CheckConstraint(
                condition=models.Q(vehicle_type__in=["CAR", "MOTORCYCLE"]),
                name="vehicle_type_valid",
            ),
        ]

    def __str__(self):
        return self.plate_number
