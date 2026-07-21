"""
به‌روزرسانی محتوای کشورهای مقصد (StudyCountry) از کاتالوگ seed.

استفاده:
  python manage.py seed_study_countries
  python manage.py seed_study_countries --country canada
  python manage.py seed_study_countries --dry-run
"""
from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import StudyCountry
from core.seed_data.country_catalog import STUDY_COUNTRY_CATALOG, STUDY_COUNTRY_CODES
from core.seed_data.world_country_catalog import (
    WORLD_STUDY_COUNTRY_CODES_LIST,
    build_world_study_country_catalog,
)


class Command(BaseCommand):
    help = "Seed or refresh StudyCountry content (intro, guides, SEO) from country_catalog"

    def add_arguments(self, parser):
        parser.add_argument(
            "--country",
            choices=STUDY_COUNTRY_CODES + WORLD_STUDY_COUNTRY_CODES_LIST + ["all", "world"],
            default="all",
            help="Which country to update (default: all primary + world catalogs)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would change without writing to DB",
        )
        parser.add_argument(
            "--create-missing",
            action="store_true",
            help="Create StudyCountry rows if code does not exist",
        )
        parser.add_argument(
            "--images",
            action="store_true",
            help="Download hero + section images from Wikimedia after seeding",
        )
        parser.add_argument(
            "--images-only",
            action="store_true",
            help="Only refresh country images (skip content update)",
        )
        parser.add_argument(
            "--force-images",
            action="store_true",
            help="Re-download images even if they already exist",
        )

    def handle(self, *args, **options):
        country_opt = options["country"]
        dry_run = options["dry_run"]
        create_missing = options["create_missing"]
        images_only = options["images_only"]
        seed_images = options["images"] or images_only
        force_images = options["force_images"]

        if images_only and dry_run:
            self.stderr.write(self.style.ERROR("--images-only cannot be used with --dry-run"))
            return

        items = STUDY_COUNTRY_CATALOG
        if country_opt == "world":
            items = build_world_study_country_catalog()
        elif country_opt != "all":
            items = [i for i in STUDY_COUNTRY_CATALOG if i["code"] == country_opt]
            if not items:
                items = [
                    i
                    for i in build_world_study_country_catalog()
                    if i["code"] == country_opt
                ]
        else:
            items = STUDY_COUNTRY_CATALOG + build_world_study_country_catalog()

        if not items:
            self.stderr.write(self.style.ERROR("No catalog entries matched."))
            return

        if images_only:
            self._seed_images(country_opt, force=force_images)
            return

        updated = created = skipped = 0

        def _apply():
            nonlocal updated, created, skipped
            for item in items:
                code = item["code"]
                defaults = {k: v for k, v in item.items() if k != "code"}
                existing = StudyCountry.objects.filter(code=code).first()
                if not existing and not create_missing:
                    self.stderr.write(
                        self.style.WARNING(f"  [{code}] not in DB — use --create-missing to add")
                    )
                    skipped += 1
                    continue
                if dry_run:
                    action = "create" if not existing else "update"
                    self.stdout.write(f"  [{code}] would {action}")
                    continue
                _, was_created = StudyCountry.objects.update_or_create(
                    code=code,
                    defaults=defaults,
                )
                if was_created:
                    created += 1
                    self.stdout.write(self.style.SUCCESS(f"  [{code}] created"))
                else:
                    updated += 1
                    self.stdout.write(f"  [{code}] updated")

        if dry_run:
            _apply()
            self.stdout.write(self.style.WARNING("Dry run — no changes saved."))
            return

        with transaction.atomic():
            _apply()

        self.stdout.write(
            self.style.SUCCESS(f"Done: {created} created, {updated} updated, {skipped} skipped")
        )

        if seed_images:
            self._seed_images(country_opt, force=force_images)

    def _seed_images(self, country_opt: str, *, force: bool) -> None:
        from core.seed_data.seed_images import seed_study_country_images

        codes = None
        if country_opt not in ("all", "world"):
            codes = [country_opt]
        self.stdout.write("Downloading country images from Wikimedia…")
        ok, skip = seed_study_country_images(codes, force=force, with_sections=True)
        self.stdout.write(self.style.SUCCESS(f"Images: {ok} hero updated, {skip} skipped"))
