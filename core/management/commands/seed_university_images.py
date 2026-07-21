"""
دریافت و ذخیره تصویر واقعی دانشگاه از ویکی‌پدیا برای همه دانشگاه‌ها.

استفاده:
  python manage.py seed_university_images
  python manage.py seed_university_images --country china
  python manage.py seed_university_images --force
"""
from __future__ import annotations

from django.core.management.base import BaseCommand

from core.models import University
from core.seed_data.seed_images import _WIKI_RAW_CACHE, seed_university_images, university_has_placeholder_image


class Command(BaseCommand):
    help = "Attach real Wikipedia cover images to universities (replaces gradient placeholders)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--country",
            default="all",
            help="Country code (e.g. canada, usa) or 'all'",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Replace all existing images, not only placeholders",
        )

    def handle(self, *args, **options):
        country_opt = (options["country"] or "all").strip().lower()
        force = options["force"]

        countries: list[str] | None = None
        if country_opt != "all":
            countries = [country_opt]

        qs = University.objects.all()
        if countries:
            qs = qs.filter(country__in=countries)

        if force:
            target = qs.count()
        else:
            target = "placeholder/missing"

        self.stdout.write(f"Processing universities for {country_opt} (force={force}, target={target})...")

        _WIKI_RAW_CACHE.clear()
        ok, skip = seed_university_images(countries, force=force)

        remaining = 0
        for u in University.objects.all().iterator():
            if countries and u.country not in countries:
                continue
            if university_has_placeholder_image(u):
                remaining += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Done: {ok} updated, {skip} skipped "
                f"(wiki cache: {len(_WIKI_RAW_CACHE)} entries, placeholders left: {remaining})"
            )
        )
