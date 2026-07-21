"""
بارگذاری دانشگاه‌های برتر جهان (سایر کشورها).

استفاده:
  python manage.py seed_world_universities
  python manage.py seed_world_universities --country uk --skip-images
  python manage.py seed_world_universities --refresh-qs --max-wiki 40
"""
from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import University, UniversityFAQ
from core.seed_data.content_builders import (
    build_university_description,
    build_university_faqs,
    build_university_meta_description,
    build_university_meta_title,
    build_university_short,
)
from core.seed_data.world_university_catalog import (
    build_world_country_catalog,
    get_world_country_label,
)
from core.study_destinations import WORLD_STUDY_COUNTRY_CODES


class Command(BaseCommand):
    help = "Seed top world universities outside Canada, Spain, and China"

    def add_arguments(self, parser):
        parser.add_argument(
            "--country",
            choices=[*WORLD_STUDY_COUNTRY_CODES, "all"],
            default="all",
            help="Which world country to seed (default: all)",
        )
        parser.add_argument(
            "--replace-faqs",
            action="store_true",
            help="Replace existing FAQs for touched universities",
        )
        parser.add_argument(
            "--skip-images",
            action="store_true",
            help="Skip automatic image download after seeding",
        )
        parser.add_argument(
            "--force-images",
            action="store_true",
            help="Replace existing images when seeding",
        )
        parser.add_argument(
            "--images-only",
            action="store_true",
            help="Only download images for existing world-country universities",
        )
        parser.add_argument(
            "--refresh-qs",
            action="store_true",
            help="Re-fetch QS institution list from Wikipedia",
        )
        parser.add_argument(
            "--refresh-wikipedia",
            action="store_true",
            help="Re-fetch Wikipedia country lists (ignore JSON cache)",
        )
        parser.add_argument(
            "--max-wiki",
            type=int,
            default=60,
            help="Max extra Wikipedia universities per country after QS entries",
        )

    def handle(self, *args, **options):
        countries = (
            list(WORLD_STUDY_COUNTRY_CODES)
            if options["country"] == "all"
            else [options["country"]]
        )

        if options["images_only"]:
            from core.seed_data.seed_images import seed_university_images

            ok, skip = seed_university_images(countries, force=options["force_images"])
            self.stdout.write(f"  Images: {ok} set, {skip} skipped")
            self.stdout.write(self.style.SUCCESS("Done."))
            return

        if options["refresh_qs"]:
            from core.seed_data.world_university_catalog import fetch_qs_institutions

            fetch_qs_institutions(refresh=True)
            self.stdout.write("Refreshed QS institution cache.")

        if options["refresh_wikipedia"]:
            from core.seed_data.wikipedia_university_fetcher import CACHE_DIR

            for code in countries:
                p = CACHE_DIR / f"wikipedia_{code}.json"
                if p.is_file():
                    p.unlink()

        all_slugs: set[str] = set(University.objects.values_list("slug", flat=True))
        total_created = total_updated = total_faqs = 0

        with transaction.atomic():
            for code in countries:
                catalog = build_world_country_catalog(
                    code,
                    existing_slugs=all_slugs,
                    use_cache=not options["refresh_wikipedia"],
                    max_wiki_extras=options["max_wiki"],
                )
                label = get_world_country_label(code)
                self.stdout.write(f"  {code}: {len(catalog)} universities in catalog")
                c, u, f = self._seed_country(code, catalog, label, options["replace_faqs"])
                total_created += c
                total_updated += u
                total_faqs += f
                for item in catalog:
                    all_slugs.add(item["slug"])

        self.stdout.write(
            f"Universities: {total_created} created, {total_updated} updated, {total_faqs} FAQs"
        )

        if not options["skip_images"]:
            from core.seed_data.seed_images import seed_university_images

            ok, skip = seed_university_images(countries, force=options["force_images"])
            self.stdout.write(f"  Images: {ok} set, {skip} skipped")

        self.stdout.write(self.style.SUCCESS("Done."))

    def _seed_country(
        self,
        country_code: str,
        catalog: list[dict],
        label: str,
        replace_faqs: bool,
    ) -> tuple[int, int, int]:
        created = updated = faq_count = 0
        for item in catalog:
            defaults = {
                "name_fa": item["name_fa"],
                "name_en": item["name_en"],
                "country": country_code,
                "city": item.get("city") or label,
                "type": University.TYPE_UNIVERSITY,
                "world_rank": item.get("world_rank", ""),
                "website": item.get("website", ""),
                "short_description": build_university_short(item, label),
                "description": build_university_description(item, country_code, label),
                "meta_title": build_university_meta_title(item, label),
                "meta_description": build_university_meta_description(item, label),
                "is_approved_by_mo_science": item.get("mo_science", True),
                "is_approved_by_mo_health": item.get("mo_health", False),
            }
            uni, was_created = University.objects.update_or_create(
                slug=item["slug"],
                defaults=defaults,
            )
            if was_created:
                created += 1
            else:
                updated += 1

            faqs = build_university_faqs(item, label)
            if replace_faqs:
                UniversityFAQ.objects.filter(university=uni).delete()
            if replace_faqs or not uni.faqs.exists():
                UniversityFAQ.objects.bulk_create(
                    [
                        UniversityFAQ(
                            university=uni,
                            question=q,
                            answer=a,
                            order=order,
                            is_active=True,
                        )
                        for order, (q, a) in enumerate(faqs, start=1)
                    ]
                )
                faq_count += len(faqs)
        return created, updated, faq_count
