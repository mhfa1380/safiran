"""
همگام‌سازی اسلاگ‌های GSC not-indexed برای لینک داخلی و sitemap.

استفاده:
  python manage.py sync_gsc_indexing_priorities
"""
from __future__ import annotations

from django.core.management.base import BaseCommand

from core.gsc_export import load_gsc_not_indexed_slugs, write_gsc_not_indexed_cache
from core.gsc_indexing import invalidate_gsc_indexing_cache


class Command(BaseCommand):
    help = "Sync GSC not-indexed slugs into cache for internal linking and sitemap boost"

    def handle(self, *args, **options):
        slugs = load_gsc_not_indexed_slugs()
        path = write_gsc_not_indexed_cache(slugs)
        invalidate_gsc_indexing_cache()
        self.stdout.write(
            self.style.SUCCESS(
                f"Wrote {path.name}: {len(slugs['majors'])} majors, "
                f"{len(slugs['universities'])} universities, {len(slugs['blogs'])} blogs"
            )
        )
