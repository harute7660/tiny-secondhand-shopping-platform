"""Isolated settings used until the project root wires in the community app."""

from config import settings as base_settings

for setting_name in dir(base_settings):
    if setting_name.isupper():
        globals()[setting_name] = getattr(base_settings, setting_name)

INSTALLED_APPS = list(base_settings.INSTALLED_APPS)
if not any(app == "community" or app.startswith("community.") for app in INSTALLED_APPS):
    INSTALLED_APPS.append("community.apps.CommunityConfig")

ROOT_URLCONF = "community.test_urls"
ENABLE_ADMIN = True
ALLOWED_HOSTS = ["testserver"]
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "community-tests",
        "TIMEOUT": 300,
    }
}
