"""
تنظیمات Production پروژه سفیران آینده روشن
Optimized & Secure Django Settings
"""

from pathlib import Path
import os

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _env_bool(name: str, default: str = "0") -> bool:
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes", "on")


def _env_list(name: str, default: list[str]) -> list[str]:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    return [part.strip() for part in raw.split(",") if part.strip()]


def _redis_url_with_db(url: str, db: int) -> str:
    """redis://host:6379/1 → همان host با شماره دیتابیس دیگر."""
    base = (url or "redis://127.0.0.1:6379/1").strip().rstrip("/")
    if "/" in base.rsplit(":", 1)[-1]:
        base = base.rsplit("/", 1)[0]
    return f"{base}/{int(db)}"


# ======================================================
# CORE
# ======================================================

DEBUG = _env_bool("DJANGO_DEBUG", "0")

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "CHANGE_THIS_SECRET_KEY")

ALLOWED_HOSTS = _env_list(
    "DJANGO_ALLOWED_HOSTS",
    ["saroshan.ir", "www.saroshan.ir", "127.0.0.1", "localhost"],
)

# ======================================================
# PROXY / SSL
# ======================================================

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True

# چون پشت CDN / Nginx هستی
SECURE_SSL_REDIRECT = False

# ======================================================
# CSRF / SESSION
# ======================================================

CSRF_TRUSTED_ORIGINS = _env_list(
    "DJANGO_CSRF_TRUSTED_ORIGINS",
    ["https://saroshan.ir", "https://www.saroshan.ir"],
)

SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG

SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"

if DEBUG:
    _local_origins = [
        "http://127.0.0.1",
        "http://localhost",
        "http://127.0.0.1:8000",
        "http://localhost:8000",
        "http://127.0.0.1:8001",
        "http://localhost:8001",
        "http://127.0.0.1:1225",
        "http://localhost:1225",
    ]
    CSRF_TRUSTED_ORIGINS = list(dict.fromkeys(CSRF_TRUSTED_ORIGINS + _local_origins))

# ======================================================
# APPS
# ======================================================

INSTALLED_APPS = [
    # Django
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "django.contrib.sitemaps",

    # Third Party
    "import_export",
    "compressor",

    # Local Apps
    "core",
    "core.admin_institute",
    "core.admin_content",
    "core.admin_universities",
    "core.admin_requests",
    "panel.apps.PanelConfig",
]

# ======================================================
# MIDDLEWARE
# ======================================================

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "core.middleware.GscLegacyRedirectMiddleware",
    "core.middleware.CanonicalHostMiddleware",
    "django.middleware.gzip.GZipMiddleware",

    # Static files
    "whitenoise.middleware.WhiteNoiseMiddleware",

    "core.middleware.DatabaseConnectionMiddleware",
    "core.middleware.DatabaseErrorMiddleware",
    "core.middleware.FreshnessHeadersMiddleware",

    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "safiran_site.urls"
WSGI_APPLICATION = "safiran_site.wsgi.application"

# ======================================================
# TEMPLATES
# ======================================================

_TEMPLATES_BASE = {
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [BASE_DIR / "templates"],
    "OPTIONS": {
        "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",

                # Custom
                "core.context_processors.institute_info",
                "core.context_processors.active_courses_info",
                "core.context_processors.nav_countries_info",
                "core.context_processors.site_navigation_info",
                "core.context_processors.seo_context",
                "core.context_processors.corner_promos_context",
                "core.context_processors.mhfa_live_context",
                "panel.context_processors.panel_ai",
        ],
    },
}

if not DEBUG:
    _TEMPLATES_BASE["OPTIONS"]["loaders"] = [
        (
            "django.template.loaders.cached.Loader",
            [
                "django.template.loaders.filesystem.Loader",
                "django.template.loaders.app_directories.Loader",
            ],
        ),
    ]
else:
    _TEMPLATES_BASE["APP_DIRS"] = True

TEMPLATES = [_TEMPLATES_BASE]

# ======================================================
# DATABASE
# ======================================================

DATABASES = {
    "default": {
        "ENGINE": os.getenv("DB_ENGINE", "django.db.backends.sqlite3"),
        "NAME": os.getenv("DB_NAME", str(BASE_DIR / "db.sqlite3")),
        "USER": os.getenv("DB_USER", ""),
        "PASSWORD": os.getenv("DB_PASSWORD", ""),
        "HOST": os.getenv("DB_HOST", ""),
        "PORT": os.getenv("DB_PORT", ""),
        "CONN_MAX_AGE": int(os.getenv("DB_CONN_MAX_AGE", "60")),
        "CONN_HEALTH_CHECKS": _env_bool("DB_CONN_HEALTH_CHECKS", "1"),
        "OPTIONS": {
            # ثانیه — sqlite3.connect(timeout=...)؛ هم‌راستا با PRAGMA busy_timeout
            "timeout": int(os.getenv("DB_SQLITE_TIMEOUT", "60")),
        },
    }
}

# SQLite — WAL، busy_timeout و retry میان‌افزار (جلوگیری از 5xx هنگام خزیدن همزمان)
DB_SQLITE_BUSY_TIMEOUT_MS = int(os.getenv("DB_SQLITE_BUSY_TIMEOUT_MS", "60000"))
DB_SQLITE_RETRY_ATTEMPTS = int(os.getenv("DB_SQLITE_RETRY_ATTEMPTS", "8"))
DB_SQLITE_RETRY_BASE_DELAY = float(os.getenv("DB_SQLITE_RETRY_BASE_DELAY", "0.05"))
DB_SQLITE_RETRY_MAX_DELAY = float(os.getenv("DB_SQLITE_RETRY_MAX_DELAY", "1.5"))

if DATABASES["default"]["ENGINE"] == "django.db.backends.sqlite3":
    DATABASES["default"]["NAME"] = BASE_DIR / "db.sqlite3"
    DATABASES["default"]["CONN_MAX_AGE"] = 0
    DATABASES["default"].pop("USER", None)
    DATABASES["default"].pop("PASSWORD", None)
    DATABASES["default"].pop("HOST", None)
    DATABASES["default"].pop("PORT", None)
    # timeout اتصال (ثانیه) = busy_timeout_ms / 1000
    _sqlite_connect_timeout = max(30, DB_SQLITE_BUSY_TIMEOUT_MS // 1000)
    DATABASES["default"]["OPTIONS"]["timeout"] = int(
        os.getenv("DB_SQLITE_TIMEOUT", str(_sqlite_connect_timeout))
    )
elif DATABASES["default"]["ENGINE"] == "django.db.backends.postgresql":
    DATABASES["default"]["OPTIONS"] = {}

# ======================================================
# CACHE (LocMem پیش‌فرض؛ Redis برای چند worker / ترافیک بالا)
# ======================================================

_CACHE_BACKEND = os.getenv("DJANGO_CACHE_BACKEND", "locmem").strip().lower()

_REDIS_URL = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/1")

if _CACHE_BACKEND == "redis":
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": _REDIS_URL,
            "KEY_PREFIX": os.getenv("CACHE_KEY_PREFIX", "safiran"),
            "TIMEOUT": int(os.getenv("CACHE_DEFAULT_TIMEOUT", "300")),
        }
    }
    if _env_bool("SESSION_CACHE_REDIS", "1"):
        SESSION_ENGINE = "django.contrib.sessions.backends.cache"
        SESSION_CACHE_ALIAS = "default"
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "safiran-default",
            "OPTIONS": {"MAX_ENTRIES": int(os.getenv("CACHE_LOCMEM_MAX_ENTRIES", "4000"))},
        }
    }

# کش — TTL کوتاه‌تر برای محتوا، بلندتر برای منو/موسسه؛ پس از ویرایش ادمین باطل می‌شود
INSTITUTE_CACHE_SECONDS = int(os.getenv("INSTITUTE_CACHE_SECONDS", "300"))
SITE_NAV_CACHE_SECONDS = int(os.getenv("SITE_NAV_CACHE_SECONDS", "300"))
PUBLIC_STATS_CACHE_SECONDS = int(os.getenv("PUBLIC_STATS_CACHE_SECONDS", "90"))
PAGE_CACHE_SECONDS = int(os.getenv("PAGE_CACHE_SECONDS", "180"))
EVAL_CATALOG_CACHE_SECONDS = int(os.getenv("EVAL_CATALOG_CACHE_SECONDS", "300"))
PRICING_CACHE_SECONDS = int(os.getenv("PRICING_CACHE_SECONDS", "120"))
API_CACHE_SECONDS = int(os.getenv("API_CACHE_SECONDS", "45"))
# در توسعه محلی کش HTML خاموش است مگر PAGE_CACHE_IN_DEBUG=1
PAGE_CACHE_IN_DEBUG = _env_bool("PAGE_CACHE_IN_DEBUG", "0")

# ======================================================
# CELERY (کارهای سنگین — ارزیابی، بله، MHFA)
# ======================================================
# production: CELERY_ENABLED=1 + worker جدا (scripts/systemd/safiran-celery.service)
CELERY_ENABLED = _env_bool("CELERY_ENABLED", "0")
CELERY_BROKER_URL = os.getenv(
    "CELERY_BROKER_URL", _redis_url_with_db(_REDIS_URL, 0)
)
CELERY_RESULT_BACKEND = os.getenv(
    "CELERY_RESULT_BACKEND", _redis_url_with_db(_REDIS_URL, 2)
)
CELERY_TASK_ALWAYS_EAGER = _env_bool("CELERY_TASK_ALWAYS_EAGER", "0")
CELERY_TASK_TRACK_STARTED = True
CELERY_RESULT_EXPIRES = int(os.getenv("CELERY_RESULT_EXPIRES", "3600"))
CELERY_WORKER_PREFETCH_MULTIPLIER = int(os.getenv("CELERY_WORKER_PREFETCH", "1"))
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"

# ======================================================
# DATABASE MAINTENANCE (retention & cleanup)
# ======================================================
# اجرا: python manage.py maintain_database
# cron روزانه پیشنهاد می‌شود.

DB_MAINTENANCE_ENABLED = _env_bool("DB_MAINTENANCE_ENABLED", "1")
DB_MAINTENANCE_VACUUM = _env_bool("DB_MAINTENANCE_VACUUM", "1")
DB_SIZE_WARN_MB = int(os.getenv("DB_SIZE_WARN_MB", "400"))

DB_RETENTION = {
    # سشن‌های منقضی (همیشه)
    "expired_shares_grace_days": int(os.getenv("DB_RETENTION_SHARES_GRACE_DAYS", "7")),
    # رزرو مشاوره انجام‌شده (قدیمی نگه داشته نمی‌شود)
    "consultation_done_days": int(os.getenv("DB_RETENTION_CONSULTATION_DONE_DAYS", "365")),
    # پیام تماس پاسخ‌داده‌شده
    "contact_replied_days": int(os.getenv("DB_RETENTION_CONTACT_REPLIED_DAYS", "365")),
    # پیام خوانده‌شده و دیده‌شده در ادمین
    "contact_read_days": int(os.getenv("DB_RETENTION_CONTACT_READ_DAYS", "180")),
    # پرونده ارزیابی منصرف/بسته
    "evaluation_lost_days": int(os.getenv("DB_RETENTION_EVAL_LOST_DAYS", "365")),
    # اسلات گذشته بدون رزرو
    "past_slots_days": int(os.getenv("DB_RETENTION_PAST_SLOTS_DAYS", "90")),
    # لاگ اقدامات ادمین جنگو (پیش‌فرض django.contrib.admin)
    "admin_log_days": int(os.getenv("DB_RETENTION_ADMIN_LOG_DAYS", "30")),
    # لاگ تغییرات با امکان بازگردانی (AdminChangeLog)
    "audit_log_days": int(os.getenv("DB_RETENTION_AUDIT_LOG_DAYS", "30")),
}

# کش کوئری‌های سنگین ادمین (ثانیه)
ADMIN_STATS_CACHE_SECONDS = int(os.getenv("ADMIN_STATS_CACHE_SECONDS", "30"))

# ======================================================
# PASSWORDS
# ======================================================

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"
    },
]

# ======================================================
# LANGUAGE / TIME
# ======================================================

LANGUAGE_CODE = "fa-ir"

TIME_ZONE = "Asia/Tehran"

USE_I18N = True
USE_TZ = True

CELERY_TIMEZONE = TIME_ZONE

# ======================================================
# تعرفه — نرخ تبدیل ارز به تومان (برای ماشین‌حساب مقرری)
# ======================================================

PRICING_EXCHANGE_RATES_TOMAN = {
    "EUR": int(os.getenv("RATE_EUR_TOMAN", "110000")),
    "USD": int(os.getenv("RATE_USD_TOMAN", "100000")),
    "GBP": int(os.getenv("RATE_GBP_TOMAN", "130000")),
    "AUD": int(os.getenv("RATE_AUD_TOMAN", "65000")),
    "CAD": int(os.getenv("RATE_CAD_TOMAN", "75000")),
    "CHF": int(os.getenv("RATE_CHF_TOMAN", "115000")),
    "DKK": int(os.getenv("RATE_DKK_TOMAN", "15000")),
    "SEK": int(os.getenv("RATE_SEK_TOMAN", "10000")),
    "NOK": int(os.getenv("RATE_NOK_TOMAN", "10000")),
    "JPY": int(os.getenv("RATE_JPY_TOMAN", "700")),
}

# ======================================================
# STATIC FILES
# ======================================================

STATIC_URL = "/static/"

# فایل‌های development
STATICFILES_DIRS = [
    BASE_DIR / "static",
]

# خروجی collectstatic
STATIC_ROOT = BASE_DIR / "staticfiles"

STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
    "compressor.finders.CompressorFinder",
]

# production: کش مرورگر برای فایل‌های استاتیک (ثانیه)
WHITENOISE_MAX_AGE = int(os.getenv("WHITENOISE_MAX_AGE", "0" if DEBUG else "31536000"))

STATICFILES_STORAGE = (
    "whitenoise.storage.CompressedStaticFilesStorage"
)

# ======================================================
# DJANGO COMPRESSOR
# ======================================================

COMPRESS_ENABLED = False
COMPRESS_OFFLINE = False

COMPRESS_ROOT = STATIC_ROOT
COMPRESS_URL = STATIC_URL

# ======================================================
# MEDIA
# ======================================================

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# ======================================================
# SITE
# ======================================================

SITE_ID = int(os.getenv("SITE_ID", "1"))
# دامنهٔ canonical — باید با ریدایرکت www در CDN/میان‌افزار هم‌خوان باشد
SITE_URL = os.getenv("SITE_URL", "https://saroshan.ir").rstrip("/")

# پاپ‌آپ‌های دعوت (بله + ارزیابی) گوشه پایین چپ
CORNER_PROMOS_ENABLED = _env_bool("CORNER_PROMOS_ENABLED", "1")

# اعلام خودکار به‌روزرسانی sitemap به گوگل/بینگ پس از تغییر محتوا
SEO_SITEMAP_PING_ENABLED = _env_bool("SEO_SITEMAP_PING_ENABLED", "1")

# ======================================================
# BALE NOTIFIER (optional)
# ======================================================
BALE_BOT_TOKEN = os.getenv("BALE_BOT_TOKEN", "")
BALE_CHAT_ID = os.getenv("BALE_CHAT_ID", "")
# چت جدا برای اعلان وبلاگ؛ اگر خالی باشد همان BALE_CHAT_ID استفاده می‌شود
BALE_BLOG_CHAT_ID = os.getenv("BALE_BLOG_CHAT_ID", "").strip()
# لینک عضویت کانال بله (پاپ‌آپ گوشه راست سایت)
BALE_CHANNEL_URL = os.getenv(
    "BALE_CHANNEL_URL", "https://ble.ir/join/8knpWPFBLj"
).strip()
BALE_TIMEOUT_SECONDS = int(os.getenv("BALE_TIMEOUT_SECONDS", "8"))
BALE_RETRY_MAX_ATTEMPTS = int(os.getenv("BALE_RETRY_MAX_ATTEMPTS", "3"))
BALE_RETRY_DELAY_SECONDS = float(os.getenv("BALE_RETRY_DELAY_SECONDS", "2"))
BALE_NOTIFY_BLOG_SAVES = os.getenv("BALE_NOTIFY_BLOG_SAVES", "true").lower() in (
    "1",
    "true",
    "yes",
    "on",
)

# لینک‌های اضافی sameAs برای شناسایی موسسه توسط AI/schema (اینستاگرام، تلگرام و …)
# AI_DISCOVERY_SAME_AS=https://instagram.com/...,https://t.me/...
AI_DISCOVERY_SAME_AS = tuple(
    u.strip()
    for u in os.getenv("AI_DISCOVERY_SAME_AS", "").split(",")
    if u.strip()
)

# ======================================================
# MHFA LIVE PANEL (https://live.mhfa.ir)
# ======================================================
MHFA_LIVE_ENABLED = _env_bool("MHFA_LIVE_ENABLED", "0")
MHFA_PANEL_URL = os.getenv("MHFA_PANEL_URL", "https://live.mhfa.ir").rstrip("/")
MHFA_SITE_SLUG = os.getenv("MHFA_SITE_SLUG", "saroshan")
MHFA_AGENT_TOKEN = os.getenv("MHFA_AGENT_TOKEN", "")
MHFA_INBOX_TOKEN = os.getenv("MHFA_INBOX_TOKEN", "")
MHFA_FOOTER_ENABLED = _env_bool("MHFA_FOOTER_ENABLED", "0")
MHFA_FOOTER_KEY = os.getenv("MHFA_FOOTER_KEY", "default")
MHFA_FOOTER_CACHE_SECONDS = int(os.getenv("MHFA_FOOTER_CACHE_SECONDS", "86400"))
MHFA_FOOTER_FETCH_TIMEOUT_SECONDS = int(os.getenv("MHFA_FOOTER_FETCH_TIMEOUT_SECONDS", "2"))
MHFA_LIVE_TIMEOUT_SECONDS = int(os.getenv("MHFA_LIVE_TIMEOUT_SECONDS", "8"))
MHFA_INBOX_RETRY_MAX_ATTEMPTS = int(os.getenv("MHFA_INBOX_RETRY_MAX_ATTEMPTS", "3"))
MHFA_INBOX_RETRY_DELAY_SECONDS = float(os.getenv("MHFA_INBOX_RETRY_DELAY_SECONDS", "2"))
MHFA_NOTIFY_BLOG_SAVES = os.getenv("MHFA_NOTIFY_BLOG_SAVES", "true").lower() in (
    "1",
    "true",
    "yes",
    "on",
)

# ======================================================
# PANEL AI (Xiaomi MiMo)
# ======================================================
PANEL_AI_ENABLED = _env_bool("PANEL_AI_ENABLED", "1")
MIMO_API_KEY = os.getenv("MIMO_API_KEY", "").strip()
MIMO_BASE_URL = os.getenv("MIMO_BASE_URL", "https://api.xiaomimimo.com/v1").rstrip("/")
MIMO_MODEL = os.getenv("MIMO_MODEL", "mimo-v2.5-pro").strip() or "mimo-v2.5-pro"
MIMO_TIMEOUT_SECONDS = int(os.getenv("MIMO_TIMEOUT_SECONDS", "30"))

# ======================================================
# SECURITY HEADERS
# ======================================================

SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

SECURE_CONTENT_TYPE_NOSNIFF = True

X_FRAME_OPTIONS = "SAMEORIGIN"

# ======================================================
# ADMIN EXPORT (django-import-export)
# ======================================================

IMPORT_EXPORT_EXPORT_PERMISSION_CODE = "view"
EXPORT_FORMATS = [
    "core.admin_export.SafiranCSV",
    "core.admin_export.SafiranXLSX",
]

# ======================================================
# DEFAULT PK
# ======================================================

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ======================================================
# CSRF ERROR VIEW
# ======================================================

CSRF_FAILURE_VIEW = "core.views.csrf_failure"