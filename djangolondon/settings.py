import os
from pathlib import Path

from dj_lite import sqlite_config
from django.utils.csp import CSP

# Hide development server warning
# https://docs.djangoproject.com/en/stable/ref/django-admin/#envvar-DJANGO_RUNSERVER_HIDE_WARNING
os.environ["DJANGO_RUNSERVER_HIDE_WARNING"] = "true"

# 1. Django Core Settings

ALLOWED_HOSTS = [
    "127.0.0.1",
    "localhost",
    "beta.djangolondon.com",
    "djangolondon.com",
    "djangolondon.fly.dev",
]

BASE_DIR = Path(__file__).resolve().parent.parent

CSRF_TRUSTED_ORIGINS = [
    "http://localhost:8000",
    "https://beta.djangolondon.com",
    "https://djangolondon.com",
    "https://djangolondon.fly.dev",
]

DATABASES = {
    "default": {
        **sqlite_config(BASE_DIR),
        "NAME": os.environ.get("DATABASE_PATH", BASE_DIR / "local.sqlite3"),
        "ATOMIC_REQUESTS": True,
    },
}

DEBUG = os.environ.get("DEBUG", "") == "1"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

INSTALLED_APPS = [
    "djangolondon",
    "django_browser_reload",
    "django.contrib.sessions",
    "django.contrib.staticfiles",
]

MIDDLEWARE = [
    "django_browser_reload.middleware.BrowserReloadMiddleware",
    "django.middleware.csp.ContentSecurityPolicyMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
]

ROOT_URLCONF = "djangolondon.urls"

SECRET_KEY = "django-insecure-e9nx_t_p4i+ztp)56!c_mor^jhp5b)0v19=gahgy%=v9waboo%"

SECURE_CSP = {
    "script-src": [CSP.NONCE, CSP.STRICT_DYNAMIC],
    "object-src": [CSP.NONE],
    "base-uri": [CSP.NONE],
}

STORAGES = {
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"
    }
}

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.template.context_processors.csp",
            ]
        },
    },
]

USE_TZ = True

# django.contrib.staticfiles
STATIC_ROOT = BASE_DIR / "static_root"
STATIC_URL = "static/"
