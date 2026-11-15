"""
Production settings (Vercel + Neon).
Existing config/settings.py ko import karke sirf override karta hai.

Use:  DJANGO_SETTINGS_MODULE=config.settings_prod
Zaroori env: DATABASE_URL (Neon POOLED url). Optional: FRONTEND_ORIGIN, ALLOWED_HOSTS,
CSRF_TRUSTED_ORIGINS, PAYMENT_MOCK_ENABLED.
"""
from urllib.parse import parse_qs, unquote, urlparse

from decouple import Csv, config

from .settings import *  # noqa: F401,F403

DEBUG = False

# ---------- hosts / CSRF ----------
ALLOWED_HOSTS = config("ALLOWED_HOSTS", default=".vercel.app", cast=Csv())
# Django admin login ke liye (https origin zaroori)
CSRF_TRUSTED_ORIGINS = config("CSRF_TRUSTED_ORIGINS", default="https://*.vercel.app", cast=Csv())

# ---------- frontend (Render) ----------
# Pehli deploy par default chalega; frontend deploy hone ke baad asli URL set karo (trailing slash nahi)
FRONTEND_ORIGIN = config("FRONTEND_ORIGIN", default="http://localhost:5173").rstrip("/")
FRONTEND_URL = FRONTEND_ORIGIN  # password reset link isi par jaata hai
CORS_ALLOWED_ORIGINS = [FRONTEND_ORIGIN]


# ---------- database (Neon) ----------
def _apply_database_url(url):
    parsed = urlparse(url)
    sslmode = parse_qs(parsed.query).get("sslmode", ["require"])[0]
    # update(): settings.py ke baaki keys (jaise ATOMIC_REQUESTS) bache rehte hain
    DATABASES["default"].update(  # noqa: F405
        {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": parsed.path.lstrip("/"),
            "USER": unquote(parsed.username or ""),
            "PASSWORD": unquote(parsed.password or ""),
            "HOST": parsed.hostname,
            "PORT": parsed.port or 5432,
            "OPTIONS": {"sslmode": sslmode},
            # Pooled (PgBouncer transaction mode): connection reuse nahi, server-side cursors band
            "CONN_MAX_AGE": 0,
            "DISABLE_SERVER_SIDE_CURSORS": True,
        }
    )


_apply_database_url(config("DATABASE_URL"))

# ---------- static files (Django admin / DRF browsable API) ----------
MIDDLEWARE = list(MIDDLEWARE)  # noqa: F405
if "whitenoise.middleware.WhiteNoiseMiddleware" not in MIDDLEWARE:
    security = "django.middleware.security.SecurityMiddleware"
    position = MIDDLEWARE.index(security) + 1 if security in MIDDLEWARE else 0
    MIDDLEWARE.insert(position, "whitenoise.middleware.WhiteNoiseMiddleware")

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"  # noqa: F405
STORAGES = {
    **STORAGES,  # noqa: F405  (default = media storage, Cloudinary/local, jaisa tha waisa)
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}

# ---------- cache (throttling ke liye) ----------
# Serverless mein har instance alag hota hai, LocMem cache throttle ko kaam nahi karne deta.
# Ek baar chalao: python manage.py createcachetable
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": "django_cache_table",
    }
}

# ---------- security ----------
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_CONTENT_TYPE_NOSNIFF = True

# ---------- demo ----------
# Mock gateway: real paisa nahi, sirf login wala guest. Real gateway lagane par False karo.
PAYMENT_MOCK_ENABLED = config("PAYMENT_MOCK_ENABLED", default=True, cast=bool)

# ---------- logging (Vercel logs stdout se aate hain) ----------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "WARNING"},
    "loggers": {"django.request": {"handlers": ["console"], "level": "ERROR", "propagate": False}},
}