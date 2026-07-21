"""همگام‌سازی کوئری‌های GSC برای اولویت محتوا."""
from __future__ import annotations

from django.core.management.base import BaseCommand

from core.gsc_query_priority import resolve_queries_to_slugs, write_gsc_queries_cache


class Command(BaseCommand):
    help = "Sync GSC search queries cache and show slug mapping"

    def handle(self, *args, **options):
        path = write_gsc_queries_cache()
        data = resolve_queries_to_slugs()
        self.stdout.write(self.style.SUCCESS(f"Wrote {path.name} ({len(data['top_queries'])} queries)"))
        self.stdout.write(
            f"Mapped: {len(data['majors'])} majors, {len(data['universities'])} universities"
        )
        for q in data["top_queries"][:12]:
            self.stdout.write(
                f"  {q['impressions']:.0f} imp | query id {hash(q['q']) & 0xffff:x}"
            )
