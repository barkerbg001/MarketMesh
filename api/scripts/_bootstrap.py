"""Configure Django so debug scripts can import project modules.

Usage from the ``api`` directory: ``python scripts/<script>.py``.
"""

import os
import sys
from pathlib import Path

API_DIR = Path(__file__).resolve().parent.parent
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

import django  # noqa: E402

django.setup()
