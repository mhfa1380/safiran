"""
تولید و ذخیره تصاویر مرتبط برای همه رشته‌های فعال (همه کشورها).

استفاده:
  python manage.py seed_major_images
  python manage.py seed_major_images --country usa
  python manage.py seed_major_images --force
  python manage.py seed_major_images --resume
"""
from __future__ import annotations

from datetime import datetime, timezone

from django.core.management.base import BaseCommand
from django.db.models import Q

from core.models import Major
from core.seed_data.seed_images import (
    _USED_MAJOR_IMAGE_DIGESTS,
    major_pks_not_refreshed_since,
    preload_major_image_digests_from_db,
    reset_major_image_uniqueness_state,
    seed_major_images,
)

JOB_STARTED_AT = datetime(2026, 6, 26, 8, 19, 0, tzinfo=timezone.utc)


class Command(BaseCommand):
    help = "Attach relevant Wikipedia-based cover images to all active majors"

    def add_arguments(self, parser):
        parser.add_argument(
            "--country",
            default="all",
            help="Country code (e.g. canada, usa) or 'all' for every active major",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Replace existing images",
        )
        parser.add_argument(
            "--resume",
            action="store_true",
            help="Continue only majors not refreshed in the current batch",
        )
        parser.add_argument(
            "--workers",
            type=int,
            default=6,
            help="Parallel Wikipedia fetch workers (default: 6)",
        )

    def handle(self, *args, **options):
        country_opt = (options["country"] or "all").strip().lower()
        force = options["force"]
        resume = options["resume"]
        workers = max(1, min(int(options["workers"] or 6), 12))

        countries: list[str] | None = None
        if country_opt != "all":
            countries = [country_opt]

        only_pks: list[int] | None = None
        if resume:
            only_pks = major_pks_not_refreshed_since(JOB_STARTED_AT, countries)
            loaded = preload_major_image_digests_from_db(countries)
            self.stdout.write(
                f"Resume: {len(only_pks)} majors pending, {loaded} existing digests loaded "
                f"(workers={workers})..."
            )
        else:
            total = Major.objects.filter(is_active=True)
            if countries:
                total = total.filter(country__in=countries)
            if not force:
                total = total.filter(Q(image="") | Q(image__isnull=True))
            self.stdout.write(f"Processing {total.count()} active majors (workers={workers})...")
            if not force:
                reset_major_image_uniqueness_state()

        ok, skip = seed_major_images(
            countries,
            force=force and not resume,
            workers=workers,
            resume=resume,
            only_pks=only_pks,
        )
        remaining = Major.objects.filter(is_active=True).filter(Q(image="") | Q(image__isnull=True)).count()
        self.stdout.write(
            self.style.SUCCESS(
                f"Done: {ok} set, {skip} skipped (unique images: {len(_USED_MAJOR_IMAGE_DIGESTS)}, "
                f"remaining without image: {remaining})"
            )
        )
