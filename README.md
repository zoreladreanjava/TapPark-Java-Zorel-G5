# TapPark

TapPark is a web-based Campus Parking Management System for Cebu Institute of Technology – University (CIT-U).
Vehicle owners tap their campus ID at the gate, guards verify them and record each vehicle's entry and exit, and
each parking area's available slots update live. Owners can check slot availability before entering, while
administrators manage parking areas, owners, vehicles, and staff accounts, and generate parking history and
utilization reports.

This phase (Project Development 1) builds the **Account Feature**: registration, login and logout, role-based
dashboards, user profiles, and staff account management.

## Tech stack

- Python 3.12+ and Django 5.2 LTS (Django templates for the frontend)
- PostgreSQL hosted on Supabase (`psycopg`, `dj-database-url`)
- `python-dotenv` for environment settings, `Pillow` for profile photos
- Bootstrap 5 (CDN)

## Setup on Windows

You need Python 3.12 or newer, Git, and a Supabase project. Run these in PowerShell.

1. Clone the repository and open the folder:

   ```powershell
   git clone https://github.com/zoreladreanjava/TapPark-Java-Zorel-G5.git
   cd TapPark-Java-Zorel-G5
   ```

2. Create and activate a virtual environment:

   ```powershell
   python -m venv venv
   venv\Scripts\activate
   ```

   If PowerShell says running scripts is disabled, run
   `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once and try again.

3. Install the packages:

   ```powershell
   pip install -r requirements.txt
   ```

4. Create your `.env` file from the example:

   ```powershell
   copy .env.example .env
   ```

   Open `.env` and fill in:

   - `SECRET_KEY`: a long random string. To make one:
     `python -c "import secrets; print(secrets.token_urlsafe(50))"`
   - `DATABASE_URL`: in Supabase, click **Connect** and copy the **Session pooler** connection string
     (the host ends in `pooler.supabase.com`). Replace `[YOUR-PASSWORD]` with your database password.
     Do not use the Direct connection string. It only works on IPv6 networks.

   `.env` is listed in `.gitignore`, so it is never committed.

5. Create the database tables:

   ```powershell
   python manage.py migrate
   ```

6. Create the first administrator account:

   ```powershell
   python manage.py createsuperuser
   ```

7. Start the server and open http://127.0.0.1:8000/:

   ```powershell
   python manage.py runserver
   ```

## Roles

| Role | How the account is created | What they can do in this phase |
|---|---|---|
| Admin | `python manage.py createsuperuser` (the role is set to Admin automatically) | Admin dashboard with account counts, Manage Staff (create guards, activate or deactivate staff) |
| Guard | Created by an admin under Dashboard > Manage Staff > New guard account | Guard dashboard (check-in, check-out, search, and correction are coming in later phases) |
| Owner | Public registration form at `/register/` | Owner dashboard (parking availability, vehicles, and history are coming in later phases) |

Registration always creates an Owner. Nobody can choose their own role.

## Account Feature checklist

- [x] Custom `Account` user model (`account` table) with roles Admin, Guard, and Owner, enforced by a database check
- [x] Email stored in lowercase and unique regardless of letter case
- [x] Registration with field-level validation (required fields, email format, duplicate username, duplicate email,
      password match, Django's password rules); passwords are hashed
- [x] Login with clear error messages, including for deactivated accounts
- [x] Logout (POST) that ends the session
- [x] Role-based dashboards; opening another role's dashboard shows a 403 "Access denied" page
- [x] Logged-out users are sent to the login page and returned afterwards (`?next=`)
- [x] Profile page with photo or initials, editable name, email, contact number, and photo (max 2 MB)
- [x] Password change that keeps the user logged in
- [x] Admin staff management: list with search and role filter, create guard accounts, activate or deactivate staff
      (an admin cannot deactivate themselves)
- [x] Automated tests in `accounts/tests.py`

## Running the tests

```powershell
python manage.py test accounts --keepdb
```

Django runs the tests in a separate `test_postgres` database on Supabase, so your real accounts are not touched.
Use `--keepdb`: without it, Django tries to delete the test database at the end, and Supabase's connection pooler
can block that with the error "database test_postgres is being accessed by other users". `--keepdb` keeps the
empty test database and reuses it next time.
