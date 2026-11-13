# TapPark

TapPark is a web-based Campus Parking Management System for Cebu Institute of Technology – University (CIT-U).
Vehicle owners tap their campus ID at the gate, guards verify them and record each vehicle's entry and exit, and
each parking area's available slots update live. Owners can check slot availability before entering, while
administrators manage parking areas, owners, vehicles, and staff accounts, and generate parking history and
utilization reports.

## Tech stack

- Python 3.12+ and Django 5.2 LTS (Django templates for the frontend)
- PostgreSQL hosted on Supabase (`psycopg`, `dj-database-url`)
- `python-dotenv` for environment settings, `Pillow` for profile photos
- Bootstrap 5 (CDN)
