import os
import tempfile
from datetime import timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from django.views.defaults import server_error

from accounts.models import Account

from .models import EntryLog, ExitLog, ParkingArea, RecordCorrection, Vehicle, VehicleOwner

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


class EntryExitTests(TestCase):
    def setUp(self):
        self.admin = make_user("admin1", Account.Role.ADMIN)
        self.guard = make_user("guard1", Account.Role.GUARD)
        self.guard2 = make_user("guard2", Account.Role.GUARD)
        self.owner = make_user("owner1", Account.Role.OWNER)
        self.other = make_user("owner2", Account.Role.OWNER)
        self.area_a = ParkingArea.objects.create(name="Area A", capacity=2, created_by=self.admin)
        self.area_b = ParkingArea.objects.create(name="Area B", capacity=1, created_by=self.admin)
        details = VehicleOwner.objects.create(account=self.owner, id_number="23-1111-111")
        other_details = VehicleOwner.objects.create(account=self.other, id_number="23-2222-222")
        self.car = Vehicle.objects.create(owner=details, plate_number="ABC 1234", vehicle_type="CAR")
        self.other_car = Vehicle.objects.create(owner=other_details, plate_number="XYZ 999", vehicle_type="CAR")

    def check_in(self, vehicle, area, user=None):
        self.client.force_login(user or self.guard)
        return self.client.post(reverse("check_in", args=[vehicle.pk]), {"area": area.pk}, follow=True)

    def test_guard_finds_vehicle_by_id_number_or_plate(self):
        self.client.force_login(self.guard)
        self.assertContains(self.client.get(reverse("guard_dashboard"), {"q": "23-1111-111"}), "ABC 1234")
        self.assertContains(self.client.get(reverse("guard_dashboard"), {"q": "abc 1234"}), "ABC 1234")
        self.assertContains(self.client.get(reverse("guard_dashboard"), {"q": "nobody"}), "No registered vehicle matches")

    def test_check_in_creates_entry_linked_to_guard_and_uses_a_slot(self):
        response = self.check_in(self.car, self.area_a)
        entry = EntryLog.objects.get(vehicle=self.car)
        self.assertEqual(entry.recorded_by, self.guard)
        self.assertEqual(entry.status, EntryLog.Status.ACTIVE)
        self.assertContains(response, "Entry recorded: ABC 1234 parked in Area A.")
        self.assertEqual(self.area_a.free_slots(), 1)

    def test_check_in_rules(self):
        self.client.force_login(self.guard)
        response = self.client.post(reverse("check_in", args=[self.car.pk]), {"area": ""}, follow=True)
        self.assertContains(response, "Choose a parking area.")
        self.check_in(self.car, self.area_b)
        response = self.check_in(self.car, self.area_a)
        self.assertContains(response, "ABC 1234 is already recorded inside. Check it out first.")
        response = self.check_in(self.other_car, self.area_b)
        self.assertContains(response, "Area B is full. Ask the owner to choose another area.")
        self.assertEqual(EntryLog.objects.count(), 1)

    def test_check_out_closes_entry_and_frees_slot(self):
        self.check_in(self.car, self.area_b)
        entry = EntryLog.objects.get(vehicle=self.car)
        response = self.client.post(reverse("check_out", args=[entry.pk]), follow=True)
        entry.refresh_from_db()
        self.assertEqual(entry.status, EntryLog.Status.CLOSED)
        self.assertEqual(entry.exit.recorded_by, self.guard)
        self.assertContains(response, "Exit recorded: ABC 1234 left Area B.")
        self.assertEqual(self.area_b.free_slots(), 1)
        # Checking out again (double click) is refused with a message, and no second exit is saved.
        response = self.client.post(reverse("check_out", args=[entry.pk]), follow=True)
        self.assertContains(response, "ABC 1234 was already checked out.")
        self.assertEqual(ExitLog.objects.filter(entry=entry).count(), 1)
        # An entry ID that doesn't exist gives the 404 page, not a crash.
        self.assertEqual(self.client.post(reverse("check_out", args=[999999])).status_code, 404)

    def test_check_in_and_out_are_post_only_and_guard_only(self):
        self.client.force_login(self.guard)
        self.assertEqual(self.client.get(reverse("check_in", args=[self.car.pk])).status_code, 405)
        for user in (self.owner, self.admin):
            self.client.force_login(user)
            response = self.client.post(reverse("check_in", args=[self.car.pk]), {"area": self.area_a.pk})
            self.assertEqual(response.status_code, 403)
        self.assertFalse(EntryLog.objects.exists())

    def test_guard_corrects_own_entry(self):
        self.check_in(self.car, self.area_a)
        entry = EntryLog.objects.get(vehicle=self.car)
        new_time = (entry.entry_time - timedelta(minutes=30)).astimezone().strftime("%Y-%m-%dT%H:%M")
        response = self.client.post(reverse("entry_edit", args=[entry.pk]),
                                    {"area": self.area_b.pk, "entry_time": new_time, "reason": "Wrong area"}, follow=True)
        entry.refresh_from_db()
        self.assertEqual(entry.area, self.area_b)
        self.assertContains(response, "Entry for ABC 1234 corrected.")
        # ISS-01: the change is logged with the old and new values.
        log = RecordCorrection.objects.get(entry=entry)
        self.assertEqual((log.action, log.old_area, log.new_area, log.reason, log.corrected_by),
                         (RecordCorrection.Action.CORRECT, self.area_a, self.area_b, "Wrong area", self.guard))

    def test_correction_rules(self):
        self.check_in(self.other_car, self.area_b)  # Area B is now full
        self.check_in(self.car, self.area_a)
        entry = EntryLog.objects.get(vehicle=self.car)
        future = (timezone.now() + timedelta(days=1)).astimezone().strftime("%Y-%m-%dT%H:%M")
        response = self.client.post(reverse("entry_edit", args=[entry.pk]),
                                    {"area": self.area_a.pk, "entry_time": future, "reason": "x"})
        self.assertFormError(response.context["form"], "entry_time", "The entry time can't be in the future.")
        now = timezone.now().astimezone().strftime("%Y-%m-%dT%H:%M")
        response = self.client.post(reverse("entry_edit", args=[entry.pk]),
                                    {"area": self.area_b.pk, "entry_time": now, "reason": "x"})
        self.assertFormError(response.context["form"], "area", "Area B is full. Choose another area.")
        response = self.client.post(reverse("entry_edit", args=[entry.pk]), {"area": self.area_a.pk, "entry_time": now})
        self.assertFormError(response.context["form"], "reason", "Enter the reason for this correction.")
        same = entry.entry_time.astimezone().strftime("%Y-%m-%dT%H:%M")
        response = self.client.post(reverse("entry_edit", args=[entry.pk]),
                                    {"area": self.area_a.pk, "entry_time": same, "reason": "x"})
        self.assertFormError(response.context["form"], None,
                             "Nothing was changed. Change the area or the entry time, or press Cancel.")
        self.assertFalse(RecordCorrection.objects.exists())

    def test_guard_cannot_change_another_guards_entry_but_admin_can(self):
        self.check_in(self.car, self.area_a, user=self.guard2)
        entry = EntryLog.objects.get(vehicle=self.car)
        self.client.force_login(self.guard)
        self.assertEqual(self.client.get(reverse("entry_edit", args=[entry.pk])).status_code, 403)
        self.assertEqual(self.client.post(reverse("entry_delete", args=[entry.pk]), {"reason": "x"}).status_code, 403)
        self.client.force_login(self.admin)
        # Undo needs a reason.
        response = self.client.post(reverse("entry_delete", args=[entry.pk]), {"reason": ""})
        self.assertFormError(response.context["form"], "reason", "Enter the reason for undoing this entry.")
        self.assertTrue(EntryLog.objects.exists())
        response = self.client.post(reverse("entry_delete", args=[entry.pk]), {"reason": "Tapped twice"}, follow=True)
        self.assertContains(response, "Entry for ABC 1234 undone.")
        self.assertFalse(EntryLog.objects.exists())
        # ISS-01: the undo stays in the correction log after the entry is gone.
        log = RecordCorrection.objects.get()
        self.assertEqual((log.action, log.plate_number, log.entry, log.reason, log.corrected_by),
                         (RecordCorrection.Action.UNDO, "ABC 1234", None, "Tapped twice", self.admin))
        self.assertContains(self.client.get(reverse("admin_history")), "Tapped twice")

    def test_closed_entries_cannot_be_changed(self):
        self.check_in(self.car, self.area_a)
        entry = EntryLog.objects.get(vehicle=self.car)
        self.client.post(reverse("check_out", args=[entry.pk]))
        self.assertEqual(self.client.get(reverse("entry_edit", args=[entry.pk])).status_code, 403)

    def test_owner_sees_availability_and_only_own_history(self):
        self.check_in(self.car, self.area_a)
        self.check_in(self.other_car, self.area_b)
        self.client.force_login(self.owner)
        response = self.client.get(reverse("owner_availability"))
        self.assertEqual(response.context["total_free"], 1)
        history = self.client.get(reverse("owner_history"))
        self.assertContains(history, "ABC 1234")
        self.assertNotContains(history, "XYZ 999")
        self.assertContains(self.client.get(reverse("owner_dashboard")), "is parked in")

    def test_admin_history_lists_and_filters_all_records(self):
        self.check_in(self.car, self.area_a)
        self.check_in(self.other_car, self.area_b)
        entry = EntryLog.objects.get(vehicle=self.car)
        self.client.post(reverse("check_out", args=[entry.pk]))
        self.client.force_login(self.admin)
        response = self.client.get(reverse("admin_history"))
        self.assertContains(response, "ABC 1234")
        self.assertContains(response, "XYZ 999")
        inside = self.client.get(reverse("admin_history"), {"status": "ACTIVE"})
        self.assertNotContains(inside, "ABC 1234")
        self.assertContains(inside, "XYZ 999")

    def test_area_and_vehicle_removal_and_capacity_rules(self):
        self.check_in(self.car, self.area_a)
        self.check_in(self.other_car, self.area_a)
        self.client.force_login(self.admin)
        response = self.client.post(reverse("area_edit", args=[self.area_a.pk]), {"name": "Area A", "capacity": 1})
        self.assertFormError(response.context["form"], "capacity", "Capacity can't be lower than the 2 vehicles parked here now.")
        self.assertContains(self.client.get(reverse("area_delete", args=[self.area_a.pk])),
                            "Area A can&#x27;t be removed while vehicles are parked in it.")
        self.client.post(reverse("area_delete", args=[self.area_a.pk]))
        self.assertTrue(ParkingArea.objects.filter(pk=self.area_a.pk).exists())
        self.client.force_login(self.owner)
        self.client.post(reverse("vehicle_delete", args=[self.car.pk]))
        self.assertTrue(Vehicle.objects.filter(pk=self.car.pk).exists())

    def test_role_access_to_core_feature_pages(self):
        pages = {
            "owner_availability": [self.owner],
            "owner_history": [self.owner],
            "admin_history": [self.admin],
        }
        for name, allowed in pages.items():
            for user in (self.admin, self.guard, self.owner):
                with self.subTest(page=name, user=user.username):
                    self.client.force_login(user)
                    expected = 200 if user in allowed else 403
                    self.assertEqual(self.client.get(reverse(name)).status_code, expected)


# A 1x1 GIF, small enough to upload in tests.
TINY_GIF = (b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,"
            b"\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;")


class PD2IssueFixTests(TestCase):
    """Checks for the fixes of the issues reported in the PD2 report."""

    def setUp(self):
        self.owner = make_user("owner1", Account.Role.OWNER)

    def test_iss02_availability_pages_refresh_themselves(self):
        self.client.force_login(self.owner)
        for name in ("owner_availability", "owner_dashboard"):
            with self.subTest(page=name):
                response = self.client.get(reverse(name))
                self.assertContains(response, '<meta http-equiv="refresh" content="30">', html=False)
                self.assertContains(response, "Last updated")

    def test_iss03_old_profile_photo_file_is_deleted(self):
        with tempfile.TemporaryDirectory() as media, override_settings(MEDIA_ROOT=media):
            self.client.force_login(self.owner)
            data = {"first_name": "Owner1", "last_name": "Test", "email": "owner1@example.com", "contact_number": ""}

            def upload(name):
                photo = SimpleUploadedFile(name, TINY_GIF, content_type="image/gif")
                self.client.post(reverse("profile_edit"), {**data, "profile_photo": photo})
                self.owner.refresh_from_db()
                return self.owner.profile_photo.path

            first = upload("first.gif")
            self.assertTrue(os.path.exists(first))
            second = upload("second.gif")
            self.assertTrue(os.path.exists(second))
            self.assertFalse(os.path.exists(first))  # replaced photo removed from disk

            self.client.post(reverse("profile_edit"), {**data, "remove_photo": "on"})
            self.assertFalse(os.path.exists(second))  # removed photo deleted from disk


class HardeningTests(TestCase):
    """PD3: the system handles bad URLs, missing tokens, logged-out users and odd input safely."""

    def setUp(self):
        self.admin = make_user("admin1", Account.Role.ADMIN)
        self.guard = make_user("guard1", Account.Role.GUARD)
        self.owner = make_user("owner1", Account.Role.OWNER)
        self.area = ParkingArea.objects.create(name="Area A", capacity=5, created_by=self.admin)
        details = VehicleOwner.objects.create(account=self.owner, id_number="23-1111-111")
        self.car = Vehicle.objects.create(owner=details, plate_number="ABC 1234", vehicle_type="CAR")

    def test_unknown_page_shows_custom_404(self):
        response = self.client.get("/this-page-does-not-exist/")
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "Page not found", status_code=404)
        self.assertNotContains(response, "Traceback", status_code=404)

    def test_unknown_record_ids_give_404_not_crash(self):
        self.client.force_login(self.admin)
        for name in ("area_edit", "area_delete", "entry_edit", "entry_delete"):
            with self.subTest(url=name):
                self.assertEqual(self.client.get(reverse(name, args=[999999])).status_code, 404)
        self.client.force_login(self.guard)
        response = self.client.post(reverse("check_in", args=[999999]), {"area": self.area.pk})
        self.assertEqual(response.status_code, 404)

    def test_custom_500_page(self):
        request = RequestFactory().get("/")
        response = server_error(request)
        self.assertEqual(response.status_code, 500)
        self.assertIn(b"Something went wrong", response.content)

    def test_post_without_csrf_token_is_rejected(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.guard)
        response = client.post(reverse("check_in", args=[self.car.pk]), {"area": self.area.pk})
        self.assertEqual(response.status_code, 403)
        self.assertContains(response, "This form has expired", status_code=403)
        self.assertFalse(EntryLog.objects.exists())

    def test_logged_out_users_cannot_change_data(self):
        response = self.client.post(reverse("check_in", args=[self.car.pk]), {"area": self.area.pk})
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('check_in', args=[self.car.pk])}")
        self.assertFalse(EntryLog.objects.exists())

    def test_invalid_area_value_is_a_form_error_not_a_crash(self):
        self.client.force_login(self.guard)
        response = self.client.post(reverse("check_in", args=[self.car.pk]), {"area": "not-a-number"}, follow=True)
        self.assertContains(response, "Choose a valid parking area.")
        self.assertFalse(EntryLog.objects.exists())

    def test_very_long_search_is_handled(self):
        self.client.force_login(self.guard)
        response = self.client.get(reverse("guard_dashboard"), {"q": "A" * 5000})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["query"]), 50)

    def test_get_never_changes_data(self):
        self.client.force_login(self.admin)
        self.client.get(reverse("area_delete", args=[self.area.pk]))  # only shows the confirmation page
        self.assertTrue(ParkingArea.objects.filter(pk=self.area.pk).exists())
        self.client.force_login(self.owner)
        self.client.get(reverse("vehicle_delete", args=[self.car.pk]))
        self.assertTrue(Vehicle.objects.filter(pk=self.car.pk).exists())

    def test_area_in_correction_log_cannot_be_removed(self):
        # An undone entry leaves only a correction record that points at the area.
        entry = EntryLog.objects.create(vehicle=self.car, area=self.area, recorded_by=self.guard)
        self.client.force_login(self.guard)
        self.client.post(reverse("entry_delete", args=[entry.pk]), {"reason": "Test"})
        self.client.force_login(self.admin)
        response = self.client.post(reverse("area_delete", args=[self.area.pk]), follow=True)
        self.assertContains(response, "can&#x27;t be removed")
        self.assertTrue(ParkingArea.objects.filter(pk=self.area.pk).exists())
