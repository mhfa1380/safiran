"""
تنظیمات پروژه سفیران آینده روشن
موسسه اعزام دانشجو به خارج - بابل، مازندران
"""
from pathlib import Path
import os
from urllib.parse import urlparse

BASE_DIR = Path(__file__).resolve().parent.parent

# تنظیمات محیط و امنیت
# - در محیط پروداکشن حتما متغیرهای محیطی زیر را ست کنید:
#   DJANGO_SECRET_KEY، DJANGO_ALLOWED_HOSTS، DJANGO_ENV=production
DJANGO_ENV = os.environ.get("DJANGO_ENV", "development").lower()

SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "django-insecure-change-me-in-development-only",
)

DEBUG = DJANGO_ENV != "production"

_default_allowed_hosts = "localhost,127.0.0.1,[::1]"
ALLOWED_HOSTS = [
    h.strip()
    for h in os.environ.get("DJANGO_ALLOWED_HOSTS", _default_allowed_hosts).split(",")
    if h.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "django.contrib.sitemaps",
    "core",
    "core.admin_institute",   # موسسه و تیم
    "core.admin_content",    # محتوا و صفحات
    "core.admin_universities",  # دانشگاه‌ها
    "core.admin_requests",   # درخواست‌ها و تماس
    "compressor",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "safiran_site.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.context_processors.institute_info",
                "core.context_processors.seo_context",
            ],
        },
    },
]

WSGI_APPLICATION = "safiran_site.wsgi.application"

CSRF_FAILURE_VIEW = "core.views.csrf_failure"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
        "OPTIONS": {
            "timeout": 30,
        },
    }
}

# استفاده از کانکشن پایدار برای کاهش سربار ساخت اتصال جدید در هر ریکوئست
CONN_MAX_AGE = int(os.environ.get("DJANGO_DB_CONN_MAX_AGE", "60"))

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "fa-ir"
TIME_ZONE = "Asia/Tehran"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
    "compressor.finders.CompressorFinder",
]

# django-compressor settings
COMPRESS_ENABLED = not DEBUG
COMPRESS_OFFLINE = not DEBUG

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# آدرس آپلود تصویر برای CKEditor (فقط staff)
CKEDITOR_UPLOAD_URL = "/admin/ckeditor-upload/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# آدرس پایه سایت برای سئو — همیشه آدرس واقعی (حتی در تست لوکال)
SITE_URL = "https://www.saroshan.ir"

# Sites framework برای sitemap
SITE_ID = 1

# تنظیمات امنیتی اضافی برای محیط پروداکشن
if not DEBUG:
    # فقط روی HTTPS
    SECURE_SSL_REDIRECT = True

    # کوکی‌ها فقط روی HTTPS ارسال شوند
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

    # جلوگیری از حملات مرورگر
    SECURE_HSTS_SECONDS = 31536000  # ۱ سال
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True

    # تنظیم CSRF trusted origins بر اساس دامنه اصلی سایت
    parsed_site = urlparse(SITE_URL)
    if parsed_site.scheme and parsed_site.netloc:
        CSRF_TRUSTED_ORIGINS = [f"{parsed_site.scheme}://{parsed_site.netloc}"]
