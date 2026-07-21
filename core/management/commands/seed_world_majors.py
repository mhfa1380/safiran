"""
بارگذاری رشته‌های تحصیلی برای کشورهای جهانی (سایر کشورها).

استفاده:
  python manage.py seed_world_majors
  python manage.py seed_world_majors --country uk --links-only
"""
from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import Major, MajorFAQ, University, UniversityMajorLink
from core.seed_data.content_builders import (
    build_major_description,
    build_major_faqs,
    build_major_meta_description,
    build_major_meta_title,
    build_major_short,
    major_slug,
)
from core.seed_data.major_catalog import MAJORS_BY_COUNTRY, get_country_label
from core.seed_data.university_major_links import (
    UNIVERSITY_SLUG_PROFILES,
    _default_categories,
    _major_matches_categories,
    get_major_titles_for_university,
)
from core.study_destinations import WORLD_STUDY_COUNTRY_CODES


class Command(BaseCommand):
    help = "Seed majors and university links for world study countries"

    def add_arguments(self, parser):
        parser.add_argument(
            "--country",
            choices=[*WORLD_STUDY_COUNTRY_CODES, "all"],
            default="all",
        )
        parser.add_argument("--replace-faqs", action="store_true")
        parser.add_argument("--links-only", action="store_true")
        parser.add_argument("--replace-links", action="store_true")
        parser.add_argument("--skip-images", action="store_true")
        parser.add_argument("--force-images", action="store_true")
        parser.add_argument(
            "--images-only",
            action="store_true",
            help="Only download images for existing world-country majors",
        )

    def handle(self, *args, **options):
        countries = (
            list(WORLD_STUDY_COUNTRY_CODES)
            if options["country"] == "all"
            else [options["country"]]
        )

        if options["links_only"]:
            with transaction.atomic():
                for code in countries:
                    self._seed_links(code, replace=options["replace_links"])
            self.stdout.write(self.style.SUCCESS("Done."))
            return

        if options["images_only"]:
            from core.seed_data.seed_images import seed_major_images

            ok, skip = seed_major_images(countries, force=options["force_images"])
            self.stdout.write(f"  Major images: {ok} set, {skip} skipped")
            self.stdout.write(self.style.SUCCESS("Done."))
            return

        with transaction.atomic():
            for code in countries:
                self._seed_majors(code, replace_faqs=options["replace_faqs"])
                self._seed_links(code, replace=options["replace_links"])

        if not options["skip_images"]:
            from core.seed_data.seed_images import seed_major_images

            ok, skip = seed_major_images(countries, force=options["force_images"])
            self.stdout.write(f"  Major images: {ok} set, {skip} skipped")

        self.stdout.write(self.style.SUCCESS("Done."))

    def _seed_majors(self, country_code: str, *, replace_faqs: bool) -> None:
        titles = MAJORS_BY_COUNTRY.get(country_code, [])
        label = get_country_label(country_code)
        created = updated = faq_count = 0

        for order, title in enumerate(titles, start=1):
            slug = major_slug(country_code, title)
            defaults = {
                "title": title,
                "country": country_code,
                "short_description": build_major_short(title, label),
                "description": build_major_description(title, country_code, label),
                "meta_title": build_major_meta_title(title, label),
                "meta_description": build_major_meta_description(title, label),
                "order": order,
                "is_active": True,
            }
            major, was_created = Major.objects.update_or_create(slug=slug, defaults=defaults)
            if was_created:
                created += 1
            else:
                updated += 1

            if replace_faqs:
                major.faqs.all().delete()
            if replace_faqs or not major.faqs.exists():
                faqs = build_major_faqs(title, label)
                MajorFAQ.objects.bulk_create(
                    [
                        MajorFAQ(
                            major=major,
                            question=q,
                            answer=a,
                            order=i + 1,
                            is_active=True,
                        )
                        for i, (q, a) in enumerate(faqs)
                    ]
                )
                faq_count += len(faqs)

        self.stdout.write(
            f"  Majors [{country_code}]: {created} created, {updated} updated "
            f"({len(titles)} total), {faq_count} FAQs"
        )

    def _seed_links(self, country_code: str, *, replace: bool) -> None:
        majors_by_slug = {
            m.slug: m
            for m in Major.objects.filter(country=country_code, is_active=True).only("id", "slug")
        }
        if replace:
            deleted, _ = UniversityMajorLink.objects.filter(university__country=country_code).delete()
            if deleted:
                self.stdout.write(f"  Links [{country_code}]: removed {deleted} old link(s)")

        unis = list(
            University.objects.filter(country=country_code)
            .only("id", "slug", "world_rank", "is_approved_by_mo_health")
            .order_by("world_rank")
        )
        created = updated = 0
        for uni in unis:
            item = {
                "slug": uni.slug,
                "world_rank": uni.world_rank or "99",
                "mo_health": uni.is_approved_by_mo_health,
            }
            titles = get_major_titles_for_university(item, country_code)
            keep_major_ids: set[int] = set()
            for order, title in enumerate(titles, start=1):
                major = majors_by_slug.get(major_slug(country_code, title))
                if not major:
                    continue
                keep_major_ids.add(major.id)
                _, was_created = UniversityMajorLink.objects.update_or_create(
                    university=uni,
                    major=major,
                    defaults={"order": order, "is_featured": order <= 8},
                )
                if was_created:
                    created += 1
                else:
                    updated += 1
            if keep_major_ids:
                UniversityMajorLink.objects.filter(university=uni).exclude(
                    major_id__in=keep_major_ids
                ).delete()

        sync_created = self._sync_majors_to_universities(country_code, unis)
        total = UniversityMajorLink.objects.filter(university__country=country_code).count()
        self.stdout.write(
            f"  Links [{country_code}]: {created} created, {updated} updated, "
            f"{sync_created} major-to-uni sync, {total} total"
        )

    def _sync_majors_to_universities(self, country_code: str, unis: list) -> int:
        created = 0
        uni_items = [
            {
                "slug": u.slug,
                "world_rank": u.world_rank or "99",
                "mo_health": u.is_approved_by_mo_health,
            }
            for u in unis
        ]
        unis_by_slug = {u.slug: u for u in unis}
        for major in Major.objects.filter(country=country_code, is_active=True).only(
            "id", "title", "slug"
        ):
            matched = []
            for item in sorted(uni_items, key=lambda x: int(x.get("world_rank") or 99)):
                uni = unis_by_slug.get(item["slug"])
                if not uni:
                    continue
                profiles = UNIVERSITY_SLUG_PROFILES.get(country_code, {}).get(
                    item["slug"]
                ) or _default_categories(item)
                if _major_matches_categories(major.title, profiles):
                    matched.append(uni)
            for order, uni in enumerate(matched[:12], start=1):
                _, was_created = UniversityMajorLink.objects.update_or_create(
                    university=uni,
                    major=major,
                    defaults={"order": order, "is_featured": order <= 4},
                )
                if was_created:
                    created += 1
        return created
