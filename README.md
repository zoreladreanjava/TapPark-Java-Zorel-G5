# TapPark

TapPark is a web-based Campus Parking Management System for Cebu Institute of Technology – University (CIT-U).
Vehicle owners tap their campus ID at the gate, guards verify them and record each vehicle's entry and exit, and
each parking area's available slots update live. Owners can check slot availability before entering, while
administrators manage parking areas, owners, vehicles, and staff accounts, and generate parking history and
utilization reports.

- **Project Development 1** built the **Account Feature**: registration, login and logout, role-based dashboards,
  user profiles, and staff account management.
- **Project Development 2** builds the core feature, **Vehicle Entry & Exit**, as a full vertical slice (see below).

## Core feature: Vehicle Entry & Exit

Guards record each vehicle that enters and leaves campus parking, and every area's free slots update from those
records. It is the main thing TapPark exists to do: replace "checking by eye" at the gate with a recorded entry and
exit, so owners can see where to park before they arrive.

**How it works**

1. **Admin** adds the parking areas and their capacity (Dashboard > Manage Parking Areas).
2. **Owner** adds their campus ID number and registers their vehicles (Dashboard > My Vehicles).
3. At the gate, the **guard** types the owner's campus ID number or plate on the gate screen (`/dashboard/guard/`).
   - If the vehicle is outside, the guard picks the area the owner chose and presses **Check in**. Full areas can't
     be chosen. This creates an `entry_log` record linked to the vehicle, the area, and the guard.
   - If the vehicle is inside, the guard presses **Check out**. This creates an `exit_log` record and closes the entry.
4. Free slots (capacity minus vehicles inside) update right away on every dashboard. They are computed from the
   records, not stored, so they can't drift out of sync.
5. A guard can **correct** (area or entry time) or **undo** an active entry they recorded. Admins can do this for any
   active entry.
6. **Owners** see Parking Availability and their own My Parking History; **admins** see all parking history with a
   search and an Inside / Exited filter.

**Data model** (`parking` app, PostgreSQL on Supabase)

| Table | Key fields | Relationships |
|---|---|---|
| `parking_area` | name (unique), capacity | `created_by` → `account` |
| `vehicle_owner` | campus ID number (unique), owner type | one-to-one → `account` |
| `vehicle` | plate number (unique), type, description | `owner` → `vehicle_owner` |
| `entry_log` | entry time, status (Inside / Exited) | `vehicle` → `vehicle`, `area` → `parking_area`, `recorded_by` → `account` |
| `exit_log` | exit time | one-to-one `entry` → `entry_log`, `recorded_by` → `account` |

Database rules: only one active entry per vehicle, capacity of at least 1, case-insensitive unique area names and
plates, and valid status, type, and owner-type values.

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

7. (Optional) Create the test accounts and sample data (3 areas, 3 vehicles, 1 parked car):

   ```powershell
   python manage.py seed_demo
   ```

   This creates `test_admin`, `test_guard`, `test_owner` and `test_owner2`, all with the test-only password
   `TapPark-Test-2026`. Running it again doesn't create duplicates.

8. Start the server and open http://127.0.0.1:8000/:

   ```powershell
   python manage.py runserver
   ```

   If port 8000 is already in use (for example by XAMPP), run `python manage.py runserver 8080` and open
   http://127.0.0.1:8080/ instead.

9. Supabase security: after `migrate` creates new tables, enable Row Level Security on them in the Supabase SQL
   Editor. Django isn't affected, because it connects as the table owner:

   ```sql
   do $$
   declare r record;
   begin
     for r in select tablename from pg_tables where schemaname = 'public' loop
       execute format('alter table public.%I enable row level security', r.tablename);
     end loop;
   end $$;
   ```

## Roles

| Role | How the account is created | What they can do |
|---|---|---|
| Admin | `python manage.py createsuperuser` (the role is set to Admin automatically) | Overview with live free slots and account counts; manage parking areas; view all owners and vehicles; view all parking history and correct or undo any active entry; Manage Staff |
| Guard | Created by an admin under Dashboard > Manage Staff > New guard account | Gate screen: find a vehicle by campus ID number or plate, check in, check out, see who is parked, correct or undo their own active entries |
| Owner | Public registration form at `/register/` | Parking Availability; My Vehicles (add, edit, remove their own); My Parking History (their own records only) |

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

## Core Feature checklist (Vehicle Entry & Exit)

- [x] Models and migrations for `parking_area`, `vehicle_owner`, `vehicle`, `entry_log`, `exit_log` on Supabase
- [x] Create: guards check vehicles in and out; admins add areas; owners register vehicles
- [x] Read: gate screen, Parking Availability, My Parking History, admin Parking History with search and filter
- [x] Update: correct an active entry's area or time; edit areas and vehicles
- [x] Delete: undo an entry recorded by mistake; remove areas and vehicles that have no parking records
- [x] Validation with clear messages: required fields, plate and ID number formats, duplicates, full areas,
      vehicle already inside, entry time in the future, capacity below vehicles parked
- [x] Records linked to the user who created them (`recorded_by`, `created_by`, owner's own vehicles)
- [x] Role-based access: each page checks the role; owners only see and change their own vehicles and history,
      guards only correct or undo their own entries
- [x] Automated tests in `parking/tests.py`
- [x] Implementation report: `docs/TapPark-Java-Zorel-G5-PD2.pdf`

## Running the tests

```powershell
python manage.py test accounts parking --keepdb
```

Django runs the tests in a separate `test_postgres` database on Supabase, so your real accounts are not touched.
Use `--keepdb`: without it, Django tries to delete the test database at the end, and Supabase's connection pooler
can block that with the error "database test_postgres is being accessed by other users". `--keepdb` keeps the
empty test database and reuses it next time.
