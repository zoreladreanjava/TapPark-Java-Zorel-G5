"""Create test accounts and sample parking data.

Run:  python manage.py seed_demo

Safe to run more than once: existing records are left as they are.
The passwords are for testing only. Never reuse them for real accounts.
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import Account
from parking.models import EntryLog, ParkingArea, Vehicle, VehicleOwner

TEST_PASSWORD = "TapPark-Test-2026"

ACCOUNTS = [
    # username, role, first name, last name
    ("test_admin", Account.Role.ADMIN, "Ana", "Admin"),
    ("test_guard", Account.Role.GUARD, "Gilbert", "Santos"),
    ("test_owner", Account.Role.OWNER, "Juan", "Dela Cruz"),
    ("test_owner2", Account.Role.OWNER, "Maria", "Reyes"),
]

AREAS = [("Area A", 100), ("Area B", 80), ("Area C", 20)]

OWNERS = {
    # username: (campus ID number, owner type, [(plate, type, description)])
    "test_owner": ("23-1234-567", "STUDENT", [("ABC 1234", "CAR", "White Toyota Vios"),
                                              ("MC-1234", "MOTORCYCLE", "Red Honda Click")]),
    "test_owner2": ("19-0042-001", "FACULTY", [("XYZ 5678", "CAR", "Gray Mitsubishi Mirage")]),
}


class Command(BaseCommand):
    help = "Create test accounts (one per role) and sample parking areas, vehicles and one entry."

    @transaction.atomic
    def handle(self, *args, **options):
        users = {}
        for username, role, first, last in ACCOUNTS:
            user = Account.objects.filter(username=username).first()
            if user is None:
                user = Account.objects.create_user(
                    username, f"{username}@tappark.test", TEST_PASSWORD,
                    role=role, first_name=first, last_name=last,
                )
                self.stdout.write(f"Created {role} account {username}")
            users[username] = user

        for name, capacity in AREAS:
            ParkingArea.objects.get_or_create(
                name=name, defaults={"capacity": capacity, "created_by": users["test_admin"]}
            )

        for username, (id_number, owner_type, vehicles) in OWNERS.items():
            owner, _ = VehicleOwner.objects.get_or_create(
                account=users[username], defaults={"id_number": id_number, "owner_type": owner_type}
            )
            for plate, vehicle_type, description in vehicles:
                Vehicle.objects.get_or_create(
                    plate_number=plate,
                    defaults={"owner": owner, "vehicle_type": vehicle_type, "description": description},
                )

        # One vehicle already parked, so the dashboards show live data.
        car = Vehicle.objects.get(plate_number="XYZ 5678")
        if not EntryLog.objects.filter(vehicle=car).exists():
            EntryLog.objects.create(
                vehicle=car, area=ParkingArea.objects.get(name="Area B"), recorded_by=users["test_guard"]
            )

        self.stdout.write(self.style.SUCCESS(f"Done. Test password for all test accounts: {TEST_PASSWORD}"))
