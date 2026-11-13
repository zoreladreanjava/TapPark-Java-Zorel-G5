from django.contrib.auth.models import AbstractUser, UserManager
from django.core.validators import RegexValidator
from django.db import models
from django.db.models.functions import Lower

contact_number_validator = RegexValidator(
    regex=r"^\+?\d{7,15}$",
    message="Enter 7 to 15 digits, optionally starting with +.",
)


class AccountManager(UserManager):
    """User manager that stores emails in lowercase and makes superusers ADMINs."""

    def create_user(self, username, email=None, password=None, **extra_fields):
        email = (email or "").strip().lower()
        return super().create_user(username, email, password, **extra_fields)

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        email = (email or "").strip().lower()
        extra_fields.setdefault("role", Account.Role.ADMIN)
        return super().create_superuser(username, email, password, **extra_fields)


class Account(AbstractUser):
    """A TapPark user: an administrator, a guard, or a vehicle owner."""

    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Admin"
        GUARD = "GUARD", "Guard"
        OWNER = "OWNER", "Owner"

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.OWNER)
    contact_number = models.CharField(
        max_length=15, blank=True, validators=[contact_number_validator]
    )
    profile_photo = models.ImageField(upload_to="profile_photos/", blank=True, null=True)

    objects = AccountManager()

    # createsuperuser will also ask for these fields.
    REQUIRED_FIELDS = ["email", "first_name", "last_name"]

    class Meta:
        db_table = "account"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(role__in=["ADMIN", "GUARD", "OWNER"]),
                name="account_role_valid",
            ),
            models.UniqueConstraint(Lower("email"), name="account_email_ci_unique"),
        ]

    def save(self, *args, **kwargs):
        # Always store email in lowercase so "Juan@CIT.edu" and "juan@cit.edu" match.
        if self.email:
            self.email = self.email.strip().lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"

    @property
    def is_admin_role(self):
        return self.role == self.Role.ADMIN

    @property
    def is_guard_role(self):
        return self.role == self.Role.GUARD

    @property
    def is_owner_role(self):
        return self.role == self.Role.OWNER
