"""Tests for the TapPark Account Feature.

Run them with:  python manage.py test accounts
Django creates a separate, empty test database, so real accounts are never touched.
"""

import io
import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from .models import Account

PASSWORD = "Str0ngPass!23"
NEW_PASSWORD = "N3wSecret!word9"


def make_account(username, role=Account.Role.OWNER, **extra):
    """Create an account with the shared test password."""
    extra.setdefault("first_name", username.title())
    extra.setdefault("last_name", "Tester")
    return Account.objects.create_user(
        username=username, email=f"{username}@cit.edu", password=PASSWORD, role=role, **extra
    )


class RegistrationTests(TestCase):
    url = reverse("register")

    def valid_data(self, **changes):
        data = {
            "first_name": "Juan",
            "last_name": "Dela Cruz",
            "username": "juan",
            "email": "juan@cit.edu",
            "contact_number": "",
            "password1": PASSWORD,
            "password2": PASSWORD,
        }
        data.update(changes)
        return data

    def test_registration_success_creates_owner_and_redirects_to_login(self):
        response = self.client.post(self.url, self.valid_data(), follow=True)
        self.assertRedirects(response, reverse("login"))
        self.assertContains(response, "Account created. You can now log in.")
        account = Account.objects.get(username="juan")
        self.assertEqual(account.role, Account.Role.OWNER)

    def test_role_in_form_data_is_ignored(self):
        self.client.post(self.url, self.valid_data(role="ADMIN"))
        self.assertEqual(Account.objects.get(username="juan").role, Account.Role.OWNER)

    def test_password_is_hashed(self):
        self.client.post(self.url, self.valid_data())
        account = Account.objects.get(username="juan")
        self.assertNotEqual(account.password, PASSWORD)
        self.assertTrue(account.password.startswith("pbkdf2_sha256$"))
        self.assertTrue(account.check_password(PASSWORD))

    def test_email_is_stored_in_lowercase(self):
        self.client.post(self.url, self.valid_data(email="Juan@CIT.edu"))
        self.assertEqual(Account.objects.get(username="juan").email, "juan@cit.edu")

    def test_missing_required_field(self):
        response = self.client.post(self.url, self.valid_data(first_name=""))
        self.assertContains(response, "Enter your first name.")
        self.assertFalse(Account.objects.filter(username="juan").exists())

    def test_bad_email_format(self):
        response = self.client.post(self.url, self.valid_data(email="not-an-email"))
        self.assertContains(response, "Enter a valid email address.")
        self.assertFalse(Account.objects.exists())

    def test_duplicate_username(self):
        make_account("juan")
        response = self.client.post(self.url, self.valid_data(email="other@cit.edu"))
        self.assertContains(response, "A user with that username already exists.")
        self.assertEqual(Account.objects.count(), 1)

    def test_duplicate_email_in_different_letter_case(self):
        make_account("maria")  # email maria@cit.edu
        response = self.client.post(self.url, self.valid_data(email="MARIA@Cit.Edu"))
        self.assertContains(response, "An account with this email already exists.")
        self.assertEqual(Account.objects.count(), 1)

    def test_password_mismatch(self):
        response = self.client.post(self.url, self.valid_data(password2="Different!Pass9"))
        self.assertContains(response, "The two password fields didn")
        self.assertFalse(Account.objects.exists())

    def test_weak_password_rejected(self):
        response = self.client.post(self.url, self.valid_data(password1="12345678", password2="12345678"))
        self.assertContains(response, "This password is entirely numeric.")
        self.assertFalse(Account.objects.exists())

    def test_logged_in_user_is_redirected_to_dashboard(self):
        self.client.force_login(make_account("owner1"))
        response = self.client.get(self.url)
        self.assertRedirects(response, reverse("dashboard"), fetch_redirect_response=False)


class LoginLogoutTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = make_account("owner1")

    def test_login_success_goes_to_dashboard(self):
        response = self.client.post(reverse("login"), {"username": "owner1", "password": PASSWORD})
        self.assertRedirects(response, reverse("dashboard"), fetch_redirect_response=False)
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.owner.pk)

    def test_login_failure_shows_clear_message(self):
        response = self.client.post(reverse("login"), {"username": "owner1", "password": "wrong"})
        self.assertContains(response, "Invalid username or password.")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_inactive_account_cannot_log_in(self):
        self.owner.is_active = False
        self.owner.save()
        response = self.client.post(reverse("login"), {"username": "owner1", "password": PASSWORD})
        self.assertContains(response, "This account has been deactivated.")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_logout_ends_session(self):
        self.client.force_login(self.owner)
        response = self.client.post(reverse("logout"), follow=True)
        self.assertRedirects(response, reverse("login"))
        self.assertContains(response, "You have been logged out.")
        self.assertNotIn("_auth_user_id", self.client.session)
        # A protected page now sends us back to login.
        response = self.client.get(reverse("owner_dashboard"))
        self.assertEqual(response.status_code, 302)

    def test_logout_with_get_is_not_allowed(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse("logout"))
        self.assertEqual(response.status_code, 405)
        self.assertIn("_auth_user_id", self.client.session)


class LoginRequiredTests(TestCase):
    def test_protected_pages_redirect_to_login_with_next(self):
        names = [
            "dashboard", "admin_dashboard", "guard_dashboard", "owner_dashboard",
            "profile", "profile_edit", "password_change", "staff_list", "staff_create",
        ]
        for name in names:
            with self.subTest(page=name):
                url = reverse(name)
                response = self.client.get(url)
                self.assertRedirects(response, f"{reverse('login')}?next={url}", fetch_redirect_response=False)


class RoleDashboardTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.accounts = {
            Account.Role.ADMIN: make_account("admin1", Account.Role.ADMIN),
            Account.Role.GUARD: make_account("guard1", Account.Role.GUARD),
            Account.Role.OWNER: make_account("owner1", Account.Role.OWNER),
        }
        cls.dashboards = {
            Account.Role.ADMIN: "admin_dashboard",
            Account.Role.GUARD: "guard_dashboard",
            Account.Role.OWNER: "owner_dashboard",
        }

    def test_dashboard_redirects_each_role_to_its_own_dashboard(self):
        for role, account in self.accounts.items():
            with self.subTest(role=role):
                self.client.force_login(account)
                response = self.client.get(reverse("dashboard"))
                self.assertRedirects(response, reverse(self.dashboards[role]))

    def test_each_role_reaches_own_dashboard_and_gets_403_on_others(self):
        for role, account in self.accounts.items():
            self.client.force_login(account)
            for other_role, name in self.dashboards.items():
                with self.subTest(user=role, dashboard=name):
                    response = self.client.get(reverse(name))
                    if role == other_role:
                        self.assertEqual(response.status_code, 200)
                    else:
                        self.assertEqual(response.status_code, 403)
                        self.assertContains(response, "Access denied", status_code=403)


# Uploaded photos go to a temporary folder instead of the real media/ folder.
TEMP_MEDIA = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class ProfileTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = make_account("owner1", first_name="Juan", last_name="Cruz")
        cls.other = make_account("maria", first_name="Maria", last_name="Santos")

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA, ignore_errors=True)

    def setUp(self):
        self.client.force_login(self.owner)

    def edit_data(self, **changes):
        data = {"first_name": "Juan", "last_name": "Cruz", "email": "owner1@cit.edu", "contact_number": ""}
        data.update(changes)
        return data

    def test_profile_page_shows_own_details(self):
        response = self.client.get(reverse("profile"))
        self.assertContains(response, "owner1@cit.edu")
        self.assertContains(response, "Owner")
        self.assertNotContains(response, "maria@cit.edu")

    def test_edit_changes_only_the_logged_in_user(self):
        response = self.client.post(
            reverse("profile_edit"),
            self.edit_data(first_name="Juanito", contact_number="+639171234567"),
        )
        self.assertRedirects(response, reverse("profile"), fetch_redirect_response=False)
        self.owner.refresh_from_db()
        self.other.refresh_from_db()
        self.assertEqual(self.owner.first_name, "Juanito")
        self.assertEqual(self.owner.contact_number, "+639171234567")
        self.assertEqual(self.other.first_name, "Maria")

    def test_role_and_username_cannot_be_changed(self):
        self.client.post(reverse("profile_edit"), self.edit_data(role="ADMIN", username="hacker"))
        self.owner.refresh_from_db()
        self.assertEqual(self.owner.role, Account.Role.OWNER)
        self.assertEqual(self.owner.username, "owner1")

    def test_email_used_by_another_account_is_rejected(self):
        response = self.client.post(reverse("profile_edit"), self.edit_data(email="MARIA@cit.edu"))
        self.assertContains(response, "An account with this email already exists.")
        self.owner.refresh_from_db()
        self.assertEqual(self.owner.email, "owner1@cit.edu")

    def test_keeping_own_email_in_different_case_is_allowed(self):
        response = self.client.post(reverse("profile_edit"), self.edit_data(email="OWNER1@cit.edu"))
        self.assertEqual(response.status_code, 302)

    def test_invalid_contact_number_is_rejected(self):
        response = self.client.post(reverse("profile_edit"), self.edit_data(contact_number="09-12"))
        self.assertContains(response, "Enter 7 to 15 digits")

    def test_photo_upload_and_validation(self):
        buffer = io.BytesIO()
        Image.new("RGB", (20, 20), "red").save(buffer, "PNG")
        png = buffer.getvalue()

        photo = SimpleUploadedFile("me.png", png, content_type="image/png")
        self.client.post(reverse("profile_edit"), self.edit_data(profile_photo=photo))
        self.owner.refresh_from_db()
        self.assertTrue(self.owner.profile_photo)

        fake = SimpleUploadedFile("fake.png", b"not an image", content_type="image/png")
        response = self.client.post(reverse("profile_edit"), self.edit_data(profile_photo=fake))
        self.assertContains(response, "Upload a valid image.")

        too_big = SimpleUploadedFile("big.png", png + b"\0" * (2 * 1024 * 1024), content_type="image/png")
        response = self.client.post(reverse("profile_edit"), self.edit_data(profile_photo=too_big))
        self.assertContains(response, "The photo must be 2 MB or smaller.")

        self.client.post(reverse("profile_edit"), self.edit_data(remove_photo="on"))
        self.owner.refresh_from_db()
        self.assertFalse(self.owner.profile_photo)

    def test_password_change_keeps_user_logged_in(self):
        self.client.login(username="owner1", password=PASSWORD)
        response = self.client.post(
            reverse("password_change"),
            {"old_password": PASSWORD, "new_password1": NEW_PASSWORD, "new_password2": NEW_PASSWORD},
            follow=True,
        )
        self.assertContains(response, "Your password has been changed.")
        self.assertTrue(response.context["user"].is_authenticated)
        self.owner.refresh_from_db()
        self.assertTrue(self.owner.check_password(NEW_PASSWORD))

    def test_password_change_with_wrong_old_password(self):
        response = self.client.post(
            reverse("password_change"),
            {"old_password": "wrong", "new_password1": NEW_PASSWORD, "new_password2": NEW_PASSWORD},
        )
        self.assertContains(response, "Your old password was entered incorrectly.")


class StaffManagementTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = make_account("admin1", Account.Role.ADMIN)
        cls.guard = make_account("guard1", Account.Role.GUARD, first_name="Ben", last_name="Reyes")
        cls.owner = make_account("owner1", Account.Role.OWNER)

    def guard_data(self, **changes):
        data = {
            "first_name": "Dan",
            "last_name": "Gate",
            "username": "guard2",
            "email": "guard2@cit.edu",
            "password1": PASSWORD,
            "password2": PASSWORD,
        }
        data.update(changes)
        return data

    def test_guard_and_owner_get_403_on_staff_pages(self):
        toggle_url = reverse("staff_toggle", args=[self.guard.pk])
        for account in (self.guard, self.owner):
            self.client.force_login(account)
            with self.subTest(user=account.username):
                self.assertEqual(self.client.get(reverse("staff_list")).status_code, 403)
                self.assertEqual(self.client.get(reverse("staff_create")).status_code, 403)
                self.assertEqual(self.client.post(reverse("staff_create"), self.guard_data()).status_code, 403)
                self.assertEqual(self.client.post(toggle_url).status_code, 403)
        self.assertFalse(Account.objects.filter(username="guard2").exists())
        self.guard.refresh_from_db()
        self.assertTrue(self.guard.is_active)

    def test_staff_list_shows_staff_only_with_search_and_filter(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("staff_list"))
        self.assertContains(response, "guard1@cit.edu")
        self.assertContains(response, "admin1@cit.edu")
        self.assertNotContains(response, "owner1@cit.edu")

        response = self.client.get(reverse("staff_list"), {"q": "reyes"})
        self.assertContains(response, "guard1@cit.edu")
        self.assertNotContains(response, "admin1@cit.edu")

        response = self.client.get(reverse("staff_list"), {"role": "ADMIN"})
        self.assertContains(response, "admin1@cit.edu")
        self.assertNotContains(response, "guard1@cit.edu")

    def test_admin_creates_guard(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse("staff_create"), self.guard_data(role="ADMIN"))
        self.assertRedirects(response, reverse("staff_list"), fetch_redirect_response=False)
        guard = Account.objects.get(username="guard2")
        self.assertEqual(guard.role, Account.Role.GUARD)
        self.assertTrue(guard.check_password(PASSWORD))

    def test_create_guard_uses_registration_validation(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("staff_create"),
            self.guard_data(username="guard1", email="OWNER1@cit.edu", password2="Different!Pass9"),
        )
        self.assertContains(response, "A user with that username already exists.")
        self.assertContains(response, "An account with this email already exists.")
        self.assertContains(response, "The two password fields didn")

    def test_toggle_deactivates_and_activates(self):
        self.client.force_login(self.admin)
        url = reverse("staff_toggle", args=[self.guard.pk])

        self.client.post(url)
        self.guard.refresh_from_db()
        self.assertFalse(self.guard.is_active)

        self.client.post(url)
        self.guard.refresh_from_db()
        self.assertTrue(self.guard.is_active)

    def test_toggle_is_post_only(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("staff_toggle", args=[self.guard.pk]))
        self.assertEqual(response.status_code, 405)

    def test_admin_cannot_deactivate_self(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse("staff_toggle", args=[self.admin.pk]), follow=True)
        self.assertContains(response, "deactivate your own account")
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)

    def test_owner_accounts_cannot_be_toggled_here(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse("staff_toggle", args=[self.owner.pk]))
        self.assertEqual(response.status_code, 404)
