from .base import *  # noqa: F403
from .base import env, env_list

DEBUG = env.bool("DEBUG", default=True)
SECRET_KEY = env.str("DJANGO_SECRET_KEY", default="django-insecure-marketmesh-development-only")
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", ["localhost", "127.0.0.1", "[::1]"])
