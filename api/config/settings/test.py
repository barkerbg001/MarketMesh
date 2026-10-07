from .base import *  # noqa: F403

DEBUG = False
SECRET_KEY = "django-insecure-marketmesh-test-only"
ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

CORS_ALLOWED_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]
OPEN_ROUTER_API_KEY = None
OPEN_ROUTER_MODEL = ""
PLAYWRIGHT_HEADLESS = True
SEARCH_HISTORY_ENABLED = True

# A fixed, test-only Fernet key; never written to disk.
ENCRYPTION_KEY = "u0kAZf0b0lB8m2X5K3sQyv9c1oWJqJ6vR0eHq2bQGjE="
ENCRYPTION_KEY_AUTOCREATE = False
CHAT_RUN_INLINE = True

# Error-path tests intentionally trigger logged exceptions; keep output clean.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"null": {"class": "logging.NullHandler"}},
    "root": {"handlers": ["null"], "level": "CRITICAL"},
}
