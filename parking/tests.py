from django.test import TestCase
from django.urls import reverse

from accounts.models import Account

from .models import ParkingArea

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
