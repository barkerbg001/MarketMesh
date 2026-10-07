import json
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env")


def env_list(name: str, default: list[str]) -> list[str]:
    """Read a list from either a JSON array or a comma-separated string.

    JSON arrays are accepted so `.env` files written for the previous
    FastAPI/pydantic-settings configuration keep working.
    """
    raw = env.str(name, default="").strip()
    if not raw:
        return list(default)
    if raw.startswith("["):
        parsed = json.loads(raw)
        if not isinstance(parsed, list):
            raise ValueError(f"{name} must be a JSON array or comma-separated string")
        return [str(item).strip() for item in parsed if str(item).strip()]
    return [item.strip() for item in raw.split(",") if item.strip()]


APP_NAME = env.str("APP_NAME", default="MarketMesh API")

SECRET_KEY = env.str("DJANGO_SECRET_KEY", default="")
DEBUG = env.bool("DEBUG", default=False)
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", [])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "drf_spectacular",
    "core",
    "retailers",
    "agents",
    "catalog",
    "history",
    "workspace",
    "research",
    "cart",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
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

SQLITE_PATH = Path(env.str("SQLITE_PATH", default=str(BASE_DIR / "db.sqlite3")))
if not SQLITE_PATH.is_absolute():
    SQLITE_PATH = BASE_DIR / SQLITE_PATH

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": SQLITE_PATH,
        "OPTIONS": {
            "timeout": 20,
            "transaction_mode": "IMMEDIATE",
            "init_command": (
                "PRAGMA journal_mode=WAL;"
                "PRAGMA synchronous=NORMAL;"
                "PRAGMA foreign_keys=ON;"
            ),
        },
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = env.str("TIME_ZONE", default="Africa/Johannesburg")
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Paths keep the FastAPI-era shape (no trailing slash).
APPEND_SLASH = False

# The public API is intentionally unauthenticated (as it was under FastAPI).
# No authentication classes means DRF never enforces session CSRF on API
# requests, even when an admin session cookie is present on localhost.
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "DEFAULT_SCHEMA_CLASS": "core.schema.AutoSchema",
    "EXCEPTION_HANDLER": "core.exceptions.api_exception_handler",
    "UNAUTHENTICATED_USER": None,
    # Export endpoints use ?format=csv|json|markdown for the file type, not renderer selection.
    "URL_FORMAT_OVERRIDE": None,
}

SPECTACULAR_SETTINGS = {
    "TITLE": APP_NAME,
    "DESCRIPTION": "Market research chat with AI agents, live product search, and a research shortlist.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

CORS_ALLOWED_ORIGINS = env_list(
    "CORS_ORIGINS",
    ["http://localhost:5173", "http://127.0.0.1:5173"],
)
CORS_ALLOW_CREDENTIALS = True
CORS_URLS_REGEX = r"^/api/.*$"
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS", [])

# Optional server-wide fallback key. A key saved on the Settings page takes precedence.
OPEN_ROUTER_API_KEY = env.str("OPEN_ROUTER_API_KEY", default="") or None
# Optional fallback model. There is deliberately no built-in default: choose one in Settings.
OPEN_ROUTER_MODEL = env.str("OPEN_ROUTER_MODEL", default="")
OPEN_ROUTER_REFERER = env.str("OPEN_ROUTER_REFERER", default="http://localhost:5173")
PLAYWRIGHT_HEADLESS = env.bool("PLAYWRIGHT_HEADLESS", default=False)

# Fernet key used to encrypt API keys saved through the Settings page. It must live
# outside the database: either this variable or the key file below.
ENCRYPTION_KEY = env.str("MARKETMESH_ENCRYPTION_KEY", default="")
ENCRYPTION_KEY_FILE = Path(
    env.str("MARKETMESH_ENCRYPTION_KEY_FILE", default=str(BASE_DIR / ".secrets" / "encryption.key"))
)
# Development creates the key file on first use; production requires it to exist.
ENCRYPTION_KEY_AUTOCREATE = env.bool("MARKETMESH_ENCRYPTION_KEY_AUTOCREATE", default=True)

# Run chat turns in a background thread and stream events. Tests run them inline.
CHAT_RUN_INLINE = False

# Record each API search/scrape (query, outcome, returned products) in SQLite.
SEARCH_HISTORY_ENABLED = env.bool("SEARCH_HISTORY_ENABLED", default=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "console": {"format": "[{asctime}] {levelname} {name}: {message}", "style": "{"},
    },
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "console"}},
    "root": {"handlers": ["console"], "level": env.str("LOG_LEVEL", default="INFO")},
    # Replaces Django's default "django" logger, which would otherwise print every
    # request warning a second time via its own DEBUG-only console handler.
    "loggers": {"django": {"handlers": ["console"], "level": "INFO", "propagate": False}},
}
