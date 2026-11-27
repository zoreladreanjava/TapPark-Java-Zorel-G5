"""
Django settings for the TapPark project.

Secrets and environment-specific values are read from the .env file
(see .env.example). Never put real credentials in this file.
"""

import os
from pathlib import Path

import dj_database_url
from django.contrib.messages import constants as message_constants
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Load variables from the .env file in the project root.
load_dotenv(BASE_DIR / ".env")


def get_env(name, default=None):
    """Read an environment variable, or stop with a clear error if it is missing."""
    value = os.getenv(name, default)
    if value is None or value == "":
        raise ImproperlyConfigured(f"Set the {name} variable in your .env file.")
    return value


SECRET_KEY = get_env("SECRET_KEY")

DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")

ALLOWED_HOSTS = [host.strip() for host in os.getenv("ALLOWED_HOSTS", "").split(",") if host.strip()]

# Security headers and cookies
X_FRAME_OPTIONS = "DENY"  # the site can't be shown inside another site's frame (clickjacking)
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
SESSION_COOKIE_HTTPONLY = True  # JavaScript can't read the login cookie
CSRF_COOKIE_HTTPONLY = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = True  # shared lab / guard-house computers
# Over HTTPS (when deployed), set COOKIES_SECURE=True in .env so cookies are only sent encrypted.
SESSION_COOKIE_SECURE = CSRF_COOKIE_SECURE = os.getenv("COOKIES_SECURE", "False").lower() in ("true", "1", "yes")


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "accounts",
    "parking",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Use our own Account model instead of Django's default User.
AUTH_USER_MODEL = "accounts.Account"


# Database: PostgreSQL on Supabase (Session pooler connection string in .env).

DATABASES = {
    "default": dj_database_url.parse(
        get_env("DATABASE_URL"),
        conn_max_age=600,
        ssl_require=True,
    )
}


# Tests: always keep the Supabase test database (see config/test_runner.py).
TEST_RUNNER = "config.test_runner.KeepDatabaseRunner"


# Login and logout
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "dashboard"
LOGOUT_REDIRECT_URL = "login"


# Password validation

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# Internationalization

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Manila"
USE_I18N = True
USE_TZ = True


# Static files (CSS, JavaScript, images that ship with the project)

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

# Media files (uploaded by users, e.g. profile photos)

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"


DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Make messages.error(...) use Bootstrap's red "alert-danger" style.
MESSAGE_TAGS = {message_constants.ERROR: "danger"}
