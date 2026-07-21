"""
بررسی سریع Redis، کش Django و Celery — قبل/بعد از deploy روی سرور.

  python manage.py check_runtime
"""

from __future__ import annotations

from django.conf import settings
from django.core.cache import cache
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "وضعیت کش Redis و Celery را گزارش می‌دهد"

    def handle(self, *args, **options):
        cache_cfg = settings.CACHES["default"]
        backend = cache_cfg["BACKEND"]
        self.stdout.write(f"DEBUG: {settings.DEBUG}")
        self.stdout.write(f"Cache backend: {backend}")
        if "redis" in backend.lower():
            self.stdout.write(f"Redis URL: {cache_cfg.get('LOCATION')}")
            self.stdout.write(f"Key prefix: {cache_cfg.get('KEY_PREFIX', '')}")

        test_key = "runtime:health"
        try:
            cache.set(test_key, "ok", 30)
            value = cache.get(test_key)
            if value == "ok":
                self.stdout.write(self.style.SUCCESS("Cache read/write: OK"))
            else:
                self.stdout.write(self.style.ERROR(f"Cache read failed: {value!r}"))
        except Exception as exc:
            self.stdout.write(self.style.ERROR(f"Cache error: {exc}"))

        session_engine = getattr(settings, "SESSION_ENGINE", "django.contrib.sessions.backends.db")
        self.stdout.write(f"Session engine: {session_engine}")

        celery_on = bool(getattr(settings, "CELERY_ENABLED", False))
        self.stdout.write(f"CELERY_ENABLED: {celery_on}")
        if celery_on:
            self.stdout.write(f"Broker: {getattr(settings, 'CELERY_BROKER_URL', '')}")
            self.stdout.write(f"Result: {getattr(settings, 'CELERY_RESULT_BACKEND', '')}")
            try:
                from safiran_site.celery import app

                ping = app.control.ping(timeout=2.0)
                if ping:
                    self.stdout.write(self.style.SUCCESS(f"Celery workers: {len(ping)} online"))
                else:
                    self.stdout.write(
                        self.style.WARNING("Celery enabled but no worker responded (start worker)")
                    )
            except Exception as exc:
                self.stdout.write(self.style.WARNING(f"Celery ping skipped: {exc}"))

        whitenoise_age = int(getattr(settings, "WHITENOISE_MAX_AGE", 0))
        self.stdout.write(f"WhiteNoise max-age: {whitenoise_age}s")
        self.stdout.write(f"Page cache seconds: {getattr(settings, 'PAGE_CACHE_SECONDS', 0)}")
