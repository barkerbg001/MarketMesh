# Production WSGI server config (Linux/macOS). Usage from api/:
#   gunicorn -c gunicorn.conf.py
import os

wsgi_app = "config.wsgi:application"
bind = os.environ.get("GUNICORN_BIND", "0.0.0.0:8000")
# A single worker keeps Playwright sessions and SQLite writes serialized;
# threads let fast endpoints (health, admin) respond while a scrape runs.
workers = int(os.environ.get("GUNICORN_WORKERS", "1"))
threads = int(os.environ.get("GUNICORN_THREADS", "4"))
# Multi-retailer scrapes and agent tool loops can take well over a minute.
timeout = int(os.environ.get("GUNICORN_TIMEOUT", "180"))
accesslog = "-"
errorlog = "-"
