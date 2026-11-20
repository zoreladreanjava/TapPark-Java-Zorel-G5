from django.test import TestCase
from django.urls import reverse

from accounts.models import Account

from .models import ParkingArea, Vehicle, VehicleOwner

PASSWORD = "Parking-Slot-42"


def make_user(username, role):
    return Account.objects.create_user(
        username, f"{username}@example.com", PASSWORD, role=role, first_name=username.title(), last_name="Test"
    )


class ParkingAreaTests(TestCase):
    def setUp(self):
        self.admin = make_user("admin1", Account.Role.ADMIN)
        self.guard = make_user("guard1", Account.Role.GUARD)
        self.owner = make_user("owner1", Account.Role.OWNER)
        self.area = ParkingArea.objects.create(name="Area A", capacity=100, created_by=self.admin)

    def test_admin_creates_area_linked_to_admin(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse("area_create"), {"name": "  Area   B ", "capacity": 80}, follow=True)
        area = ParkingArea.objects.get(name="Area B")
        self.assertEqual(area.created_by, self.admin)
        self.assertContains(response, "Parking area &quot;Area B&quot; added.")

    def test_area_validation_errors(self):
        self.client.force_login(self.admin)
        cases = [
            ({"name": "", "capacity": ""}, "name", "Enter the area name."),
            ({"name": "area a", "capacity": 10}, "name", "A parking area with this name already exists."),
            ({"name": "Area Z", "capacity": 0}, "capacity", "Capacity must be at least 1."),
            ({"name": "Area Z", "capacity": "ten"}, "capacity", "Capacity must be a whole number."),
        ]
        for data, field, message in cases:
            with self.subTest(data=data):
                response = self.client.post(reverse("area_create"), data)
                self.assertFormError(response.context["form"], field, message)
        self.assertEqual(ParkingArea.objects.count(), 1)

    def test_admin_edits_area(self):
        self.client.force_login(self.admin)
        self.client.post(reverse("area_edit", args=[self.area.pk]), {"name": "Area A", "capacity": 120})
        self.area.refresh_from_db()
        self.assertEqual(self.area.capacity, 120)

    def test_admin_deletes_area_with_post_only(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("area_delete", args=[self.area.pk]))
        self.assertContains(response, "Remove Area A?")
        self.assertTrue(ParkingArea.objects.filter(pk=self.area.pk).exists())
        self.client.post(reverse("area_delete", args=[self.area.pk]))
        self.assertFalse(ParkingArea.objects.filter(pk=self.area.pk).exists())

    def test_guard_and_owner_get_403_on_area_pages(self):
        urls = [
            reverse("area_list"),
            reverse("area_create"),
            reverse("area_edit", args=[self.area.pk]),
            reverse("area_delete", args=[self.area.pk]),
        ]
        for user in (self.guard, self.owner):
            self.client.force_login(user)
            for url in urls:
                with self.subTest(user=user.username, url=url):
                    self.assertEqual(self.client.get(url).status_code, 403)

    def test_logged_out_redirects_to_login(self):
        response = self.client.get(reverse("area_list"))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('area_list')}")


class MyVehiclesTests(TestCase):
    def setUp(self):
        self.owner = make_user("owner1", Account.Role.OWNER)
        self.other = make_user("owner2", Account.Role.OWNER)
        self.admin = make_user("admin1", Account.Role.ADMIN)
        self.guard = make_user("guard1", Account.Role.GUARD)
        self.other_details = VehicleOwner.objects.create(account=self.other, id_number="23-0000-002")
        self.other_vehicle = Vehicle.objects.create(owner=self.other_details, plate_number="XYZ 999", vehicle_type="CAR")

    def add_details(self):
        return VehicleOwner.objects.create(account=self.owner, id_number="23-0000-001")

    def test_owner_must_add_id_number_before_vehicle(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse("vehicle_create"))
        self.assertRedirects(response, reverse("owner_details_edit"))

    def test_owner_saves_details_linked_to_own_account(self):
        self.client.force_login(self.owner)
        self.client.post(reverse("owner_details_edit"), {"id_number": " 23-1234-567 ", "owner_type": "STUDENT"})
        details = VehicleOwner.objects.get(account=self.owner)
        self.assertEqual(details.id_number, "23-1234-567")

    def test_details_validation(self):
        self.client.force_login(self.owner)
        cases = [
            ({"id_number": "", "owner_type": "STUDENT"}, "Enter your campus ID number."),
            ({"id_number": "23-0000-002", "owner_type": "STUDENT"}, "This ID number is already registered to another owner."),
            ({"id_number": "12 34!", "owner_type": "STUDENT"}, "Use 4 to 20 letters, digits or dashes, e.g. 23-1234-567."),
        ]
        for data, message in cases:
            with self.subTest(data=data):
                response = self.client.post(reverse("owner_details_edit"), data)
                self.assertFormError(response.context["form"], "id_number", message)

    def test_owner_registers_vehicle_with_normalized_plate(self):
        details = self.add_details()
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("vehicle_create"), {"plate_number": "abc  1234", "vehicle_type": "CAR"}, follow=True
        )
        vehicle = Vehicle.objects.get(owner=details)
        self.assertEqual(vehicle.plate_number, "ABC 1234")
        self.assertContains(response, "Vehicle ABC 1234 registered.")

    def test_vehicle_validation(self):
        self.add_details()
        self.client.force_login(self.owner)
        cases = [
            ({"plate_number": "", "vehicle_type": "CAR"}, "plate_number", "Enter the plate number."),
            ({"plate_number": "xyz 999", "vehicle_type": "CAR"}, "plate_number", "This plate number is already registered."),
            ({"plate_number": "AB--12", "vehicle_type": "CAR"}, "plate_number",
             "Use letters and digits separated by single spaces or dashes, e.g. ABC 1234 or MC-1234."),
            ({"plate_number": "MC-1234", "vehicle_type": ""}, "vehicle_type", "Choose the vehicle type."),
        ]
        for data, field, message in cases:
            with self.subTest(data=data):
                response = self.client.post(reverse("vehicle_create"), data)
                self.assertFormError(response.context["form"], field, message)

    def test_owner_edits_and_removes_own_vehicle(self):
        details = self.add_details()
        vehicle = Vehicle.objects.create(owner=details, plate_number="MC-1234", vehicle_type="MOTORCYCLE")
        self.client.force_login(self.owner)
        self.client.post(reverse("vehicle_edit", args=[vehicle.pk]),
                         {"plate_number": "MC-1234", "vehicle_type": "MOTORCYCLE", "description": "Red scooter"})
        vehicle.refresh_from_db()
        self.assertEqual(vehicle.description, "Red scooter")
        self.client.post(reverse("vehicle_delete", args=[vehicle.pk]))
        self.assertFalse(Vehicle.objects.filter(pk=vehicle.pk).exists())

    def test_owner_cannot_see_or_change_another_owners_vehicle(self):
        self.add_details()
        self.client.force_login(self.owner)
        for name in ("vehicle_edit", "vehicle_delete"):
            with self.subTest(url=name):
                self.assertEqual(self.client.get(reverse(name, args=[self.other_vehicle.pk])).status_code, 404)
                self.assertEqual(self.client.post(reverse(name, args=[self.other_vehicle.pk])).status_code, 404)
        self.assertNotContains(self.client.get(reverse("my_vehicles")), "XYZ 999")
        self.assertTrue(Vehicle.objects.filter(pk=self.other_vehicle.pk).exists())

    def test_admin_sees_all_vehicles_and_can_search(self):
        self.client.force_login(self.admin)
        self.assertContains(self.client.get(reverse("admin_vehicle_list")), "XYZ 999")
        self.assertContains(self.client.get(reverse("admin_vehicle_list"), {"q": "23-0000-002"}), "XYZ 999")
        self.assertNotContains(self.client.get(reverse("admin_vehicle_list"), {"q": "nomatch"}), "XYZ 999")

    def test_role_access(self):
        self.client.force_login(self.guard)
        for name in ("my_vehicles", "vehicle_create", "owner_details_edit", "admin_vehicle_list"):
            with self.subTest(url=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 403)
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(reverse("admin_vehicle_list")).status_code, 403)
