import os

SECRET_KEY = "fake-key"
INSTALLED_APPS = ["tests"]
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("PGDATABASE", "migration_checker"),
        "USER": None,
        "PASSWORD": None,
        "HOST": None,
        "PORT": None,
    }
}
