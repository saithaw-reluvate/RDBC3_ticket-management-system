"""
Single environment-driven settings module (Step 0 decision — no base/dev/prod
split). Values come from real environment variables; in development a `.env`
file at the repo root is loaded manually below so no extra dependency is
needed for that.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BASE_DIR.parent


def _load_dotenv(path: Path) -> None:
    """Populate os.environ from a simple KEY=VALUE .env file, without
    overriding variables already set in the real environment (e.g. on EC2)."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


_load_dotenv(REPO_ROOT / ".env")


def _env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_list(name: str, default: str = "") -> list[str]:
    raw = os.environ.get(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "insecure-dev-only-key")
DEBUG = _env_bool("DJANGO_DEBUG", False)
ALLOWED_HOSTS = _env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")

# Django's CSRF check compares the browser's Origin header against the
# request Host. Next.js's /api/* rewrite (docs/ARCHITECTURE.md Decision 3)
# proxies server-side to BACKEND_ORIGIN, so Django sees Host: localhost:8000
# while the browser's Origin stays the Next.js origin (localhost:3000) —
# an origin/host mismatch Django rejects by default on every unsafe admin
# request. CSRF_TRUSTED_ORIGINS is the standard fix for exactly this
# reverse-proxy shape.
CSRF_TRUSTED_ORIGINS = _env_list("DJANGO_CSRF_TRUSTED_ORIGINS", "http://localhost:3000")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "tickets",
]

# ---------------------------------------------------------------------------
# DRF (Step 2) — one exception handler for uniform, user-safe JSON errors;
# session auth only (no WWW-Authenticate header => DRF returns 403, not 401,
# for both anonymous and non-staff callers on admin routes).
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
    "EXCEPTION_HANDLER": "tickets.exceptions.custom_exception_handler",
    "DEFAULT_THROTTLE_RATES": {
        "ticket_create": "5/hour",
        "token_lookup": "120/hour",
        "resend_link": "3/hour",
    },
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}

# A Django CSRF failure (e.g. missing/invalid X-CSRFToken) otherwise renders
# an HTML page — keep every error response, including this one, JSON.
CSRF_FAILURE_VIEW = "tickets.exceptions.csrf_failure"

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
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "ticket_system"),
        "USER": os.environ.get("POSTGRES_USER", "ticket_system"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", ""),
        "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = REPO_ROOT / "backend" / "staticfiles"

# Attachments are never served from a public static path (Step 0 Decision 5).
# MEDIA_ROOT is only the on-disk location; a Django view enforcing the
# caller's token/session is what actually serves files, added in Step 2.
MEDIA_URL = "media/"
MEDIA_ROOT = REPO_ROOT / "backend" / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Email (Step 0 Decision 4) — one SMTP code path; only env vars change
# between Mailpit (dev) and AWS SES / Gmail (prod).
# ---------------------------------------------------------------------------
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.environ.get("EMAIL_HOST", "localhost")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "1025"))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = _env_bool("EMAIL_USE_TLS", False)
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "support@example.com")

# Used to build the tracking link embedded in outbound emails (Next.js is not
# reachable from the backend at request time, so this is a plain setting).
FRONTEND_BASE_URL = os.environ.get("FRONTEND_BASE_URL", "http://localhost:3000")

# ---------------------------------------------------------------------------
# Ticket access tokens and attachments — env-configurable per docs/BACKEND.md.
# ---------------------------------------------------------------------------
TICKET_TOKEN_TTL_DAYS = int(os.environ.get("TICKET_TOKEN_TTL_DAYS", "90"))
ATTACHMENT_MAX_BYTES = int(os.environ.get("ATTACHMENT_MAX_BYTES", str(5 * 1024 * 1024)))
ATTACHMENT_MAX_COUNT = int(os.environ.get("ATTACHMENT_MAX_COUNT", "5"))

# ---------------------------------------------------------------------------
# Logging — persistent files for tracking errors/exceptions during backend
# execution. logs/ is a Docker-mounted volume and gitignored.
# ---------------------------------------------------------------------------
LOGS_DIR = REPO_ROOT / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{asctime} {levelname} {name} {message}",
            "style": "{",
        },
    },
    "filters": {
        "redact_token_path": {
            "()": "tickets.logging_filters.RedactTokenPathFilter",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "application_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOGS_DIR / "application.log",
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 5,
            "formatter": "verbose",
            "level": "INFO",
        },
        "error_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOGS_DIR / "error.log",
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 5,
            "formatter": "verbose",
            "level": "ERROR",
        },
    },
    "root": {
        "handlers": ["console", "application_file", "error_file"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console", "application_file", "error_file"],
            "level": "INFO",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["console", "application_file", "error_file"],
            "level": "WARNING",
            "propagate": False,
            "filters": ["redact_token_path"],
        },
        "django.server": {
            "handlers": ["console", "application_file", "error_file"],
            "level": "INFO",
            "propagate": False,
            "filters": ["redact_token_path"],
        },
        "tickets": {
            "handlers": ["console", "application_file", "error_file"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

# Customer ticket pages carry the access token in the URL path — never leak
# it via the Referer header on outbound links (Step 0, cross-cutting).
SECURE_REFERRER_POLICY = "no-referrer"
