from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models.functions import Lower


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
