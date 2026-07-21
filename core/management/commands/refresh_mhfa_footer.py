"""واکشی روزانه فوتر مرکزی از live.mhfa.ir — برای cron."""

from django.conf import settings
from django.core.management.base import BaseCommand

from core.mhfa_live import refresh_footer_cache_sync


class Command(BaseCommand):
    help = "واکشی فوتر مرکزی MHFA Live و ذخیره در کش سرور (پیشنهاد: یک‌بار در روز)"

    def handle(self, *args, **options):
        if not getattr(settings, "MHFA_FOOTER_ENABLED", False):
            self.stdout.write(self.style.WARNING("MHFA_FOOTER_ENABLED=0 — کاری انجام نشد."))
            return

        key = str(getattr(settings, "MHFA_FOOTER_KEY", "default")).strip() or "default"
        ok = refresh_footer_cache_sync(key)
        if ok:
            self.stdout.write(self.style.SUCCESS(f"MHFA footer refreshed (key={key})."))
        else:
            self.stdout.write(
                self.style.WARNING(
                    f"MHFA footer fetch failed; stale cache kept if available (key={key})."
                )
            )
