from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models
from django.db.models import Count, F, Q
from django.db.models.functions import Lower, Upper
from django.utils import timezone

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


class ParkingAreaQuerySet(models.QuerySet):
    def with_counts(self):
        """Add `parked` (vehicles inside now) to each area.

        Free slots are computed (capacity - parked) instead of stored, so the
        count can never drift out of sync with the entry records.
        """
        return self.annotate(parked=Count("entries", filter=Q(entries__status="ACTIVE"))).annotate(
            free=F("capacity") - F("parked")
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

    objects = ParkingAreaQuerySet.as_manager()

    class Meta:
        db_table = "parking_area"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(Lower("name"), name="parking_area_name_ci_unique"),
            models.CheckConstraint(condition=models.Q(capacity__gte=1), name="parking_area_capacity_positive"),
        ]

    def __str__(self):
        return self.name

    def parked_count(self):
        return self.entries.filter(status=EntryLog.Status.ACTIVE).count()

    def free_slots(self):
        return max(self.capacity - self.parked_count(), 0)


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

    def active_entry(self):
        """The entry for this vehicle's current stay, or None if it is outside."""
        return self.entries.filter(status=EntryLog.Status.ACTIVE).select_related("area").first()


class EntryLog(models.Model):
    """A vehicle entering a parking area, recorded by a guard at the gate."""

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Inside"
        CLOSED = "CLOSED", "Exited"

    vehicle = models.ForeignKey(Vehicle, on_delete=models.PROTECT, related_name="entries")
    area = models.ForeignKey(ParkingArea, on_delete=models.PROTECT, related_name="entries")
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="entries_recorded"
    )
    entry_time = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)

    class Meta:
        db_table = "entry_log"
        ordering = ["-entry_time"]
        constraints = [
            # A vehicle can only be inside once at a time.
            models.UniqueConstraint(
                fields=["vehicle"], condition=Q(status="ACTIVE"), name="entry_log_one_active_per_vehicle"
            ),
            models.CheckConstraint(condition=Q(status__in=["ACTIVE", "CLOSED"]), name="entry_log_status_valid"),
        ]

    def __str__(self):
        return f"{self.vehicle} in {self.area} at {self.entry_time:%Y-%m-%d %H:%M}"

    @property
    def is_active(self):
        return self.status == self.Status.ACTIVE

    def can_be_changed_by(self, user):
        """Guards may correct or undo their own active entries; admins may change any active entry."""
        if not self.is_active:
            return False
        return user.is_admin_role or (user.is_guard_role and self.recorded_by_id == user.pk)


class RecordCorrection(models.Model):
    """An audit record of every Correct or Undo on an entry (fixes PD2 ISS-01).

    The entry link is kept even after an Undo deletes the entry (SET_NULL), and the
    plate, areas and times are copied, so the history stays readable.
    """

    class Action(models.TextChoices):
        CORRECT = "CORRECT", "Corrected"
        UNDO = "UNDO", "Undone"

    entry = models.ForeignKey(
        EntryLog, on_delete=models.SET_NULL, null=True, blank=True, related_name="corrections"
    )
    action = models.CharField(max_length=10, choices=Action.choices)
    plate_number = models.CharField(max_length=12)
    old_area = models.ForeignKey(ParkingArea, on_delete=models.PROTECT, related_name="+")
    new_area = models.ForeignKey(ParkingArea, on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    old_entry_time = models.DateTimeField()
    new_entry_time = models.DateTimeField(null=True, blank=True)
    reason = models.CharField(max_length=200)
    corrected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="corrections_made"
    )
    corrected_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "record_correction"
        ordering = ["-corrected_at"]
        constraints = [
            models.CheckConstraint(condition=Q(action__in=["CORRECT", "UNDO"]), name="record_correction_action_valid"),
        ]

    def __str__(self):
        return f"{self.get_action_display()} {self.plate_number} by {self.corrected_by}"


class ExitLog(models.Model):
    """A vehicle leaving. It closes exactly one entry."""

    entry = models.OneToOneField(EntryLog, on_delete=models.CASCADE, related_name="exit")
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="exits_recorded"
    )
    exit_time = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "exit_log"
        ordering = ["-exit_time"]

    def __str__(self):
        return f"{self.entry.vehicle} left at {self.exit_time:%Y-%m-%d %H:%M}"
