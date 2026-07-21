"""
بهینه‌سازی سئو صفحات پرترافیک GSC — متا، تصاویر و CTR.

استفاده:
  python manage.py improve_gsc_seo
  python manage.py improve_gsc_seo --all-majors --all-universities
  python manage.py boost_gsc_seo
"""
from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from core.gsc_seo_overrides import (
    BLOG_OVERRIDES,
    GSC_BLOG_SLUGS,
    GSC_MAJOR_SLUGS,
    GSC_UNIVERSITY_SLUGS,
    MAJOR_OVERRIDES,
    SERVICE_CATEGORY_OVERRIDES,
    UNIVERSITY_OVERRIDES,
)
from core.models import BlogPost, Major, ServiceCategory, StudyCountry, University
from core.seed_data.content_builders import build_major_meta_description, build_major_meta_title
from core.seed_data.seed_images import attach_major_image, attach_university_image
from core.study_destinations import ALL_DESTINATION_LABELS


class Command(BaseCommand):
    help = "Improve SEO meta and images for Google Search Console top pages"

    def add_arguments(self, parser):
        parser.add_argument(
            "--meta-only",
            action="store_true",
            help="Only update meta titles/descriptions",
        )
        parser.add_argument(
            "--images-only",
            action="store_true",
            help="Only fetch/refresh images",
        )
        parser.add_argument(
            "--force-images",
            action="store_true",
            help="Replace existing images",
        )
        parser.add_argument(
            "--all-majors",
            action="store_true",
            help="Apply meta to all active majors, not only GSC slugs",
        )
        parser.add_argument(
            "--all-universities",
            action="store_true",
            help="Apply meta to all universities, not only GSC slugs",
        )
        parser.add_argument(
            "--world-countries",
            action="store_true",
            help="Refresh meta for all active StudyCountry rows",
        )
        parser.add_argument(
            "--all-images",
            action="store_true",
            help="Attach images for all majors/universities missing cover",
        )

    def handle(self, *args, **options):
        do_meta = not options["images_only"]
        do_images = not options["meta_only"]
        all_images = options["all_images"] or options["all_majors"] or options["all_universities"]

        if do_meta:
            with transaction.atomic():
                u = self._apply_university_meta(options["all_universities"])
                m = self._apply_major_meta(options["all_majors"])
                c = self._apply_world_country_meta(options["world_countries"])
                b = self._apply_blog_meta()
                s = self._apply_service_meta()
            self.stdout.write(
                self.style.SUCCESS(
                    f"Meta updated: {u} universities, {m} majors, {c} countries, "
                    f"{b} blogs, {s} service categories"
                )
            )

        if do_images:
            ui, us = self._apply_university_images(
                force=options["force_images"], all_universities=all_images
            )
            mi, ms = self._apply_major_images(force=options["force_images"], all_majors=all_images)
            self.stdout.write(
                self.style.SUCCESS(
                    f"Images: {ui} universities updated ({us} skipped), "
                    f"{mi} majors updated ({ms} skipped)"
                )
            )

    def _apply_university_meta(self, all_universities: bool) -> int:
        slugs = None if all_universities else GSC_UNIVERSITY_SLUGS
        qs = University.objects.all()
        if slugs:
            qs = qs.filter(slug__in=slugs)
        count = 0
        for uni in qs.iterator():
            override = UNIVERSITY_OVERRIDES.get(uni.slug)
            if override:
                uni.meta_title = override["meta_title"]
                uni.meta_description = override["meta_description"]
            else:
                label = ALL_DESTINATION_LABELS.get(uni.country, uni.country)
                from core.seed_data.content_builders import (
                    build_university_meta_description,
                    build_university_meta_title,
                )

                item = {
                    "name_fa": uni.name_fa,
                    "name_en": uni.name_en,
                    "world_rank": uni.world_rank,
                    "city": uni.city,
                }
                uni.meta_title = build_university_meta_title(item, label, uni.country or "")
                uni.meta_description = build_university_meta_description(
                    item, label, uni.country or ""
                )
            uni.save(update_fields=["meta_title", "meta_description"])
            count += 1
        return count

    def _apply_major_meta(self, all_majors: bool) -> int:
        slugs = None if all_majors else GSC_MAJOR_SLUGS
        qs = Major.objects.filter(is_active=True)
        if slugs:
            qs = qs.filter(slug__in=slugs)
        count = 0
        for major in qs.iterator():
            override = MAJOR_OVERRIDES.get(major.slug)
            if override:
                major.meta_title = override["meta_title"]
                major.meta_description = override["meta_description"]
            else:
                label = ALL_DESTINATION_LABELS.get(major.country, major.country)
                major.meta_title = build_major_meta_title(
                    major.title, label, major.country or ""
                )
                major.meta_description = build_major_meta_description(
                    major.title, label, major.country or ""
                )
            major.save(update_fields=["meta_title", "meta_description"])
            count += 1
        return count

    def _apply_world_country_meta(self, all_countries: bool) -> int:
        if not all_countries:
            return 0
        from core.study_destinations import PRIMARY_STUDY_COUNTRY_CODES
        from core.seed_data.world_country_catalog import build_world_study_country_catalog

        catalog = {item["code"]: item for item in build_world_study_country_catalog()}
        count = 0
        for code, item in catalog.items():
            if code in PRIMARY_STUDY_COUNTRY_CODES:
                continue
            updated = StudyCountry.objects.filter(code=code, is_active=True).update(
                meta_title=item["meta_title"],
                meta_description=item["meta_description"],
            )
            count += updated
        return count

    def _apply_blog_meta(self) -> int:
        count = 0
        for slug in GSC_BLOG_SLUGS:
            override = BLOG_OVERRIDES.get(slug)
            if not override:
                continue
            updated = BlogPost.objects.filter(slug=slug).update(
                meta_title=override.get("meta_title", ""),
                meta_description=override.get("meta_description", ""),
            )
            count += updated
        return count

    def _apply_service_meta(self) -> int:
        count = 0
        for slug, override in SERVICE_CATEGORY_OVERRIDES.items():
            updated = ServiceCategory.objects.filter(slug=slug).update(
                meta_title=override.get("meta_title", ""),
                meta_description=override.get("meta_description", ""),
            )
            count += updated
        return count

    def _apply_university_images(self, *, force: bool, all_universities: bool = False) -> tuple[int, int]:
        ok = skip = 0
        qs = University.objects.all()
        if not all_universities:
            qs = qs.filter(slug__in=GSC_UNIVERSITY_SLUGS)
        for uni in qs.iterator():
            if attach_university_image(uni, force=force):
                ok += 1
            else:
                skip += 1
        return ok, skip

    def _apply_major_images(self, *, force: bool, all_majors: bool = False) -> tuple[int, int]:
        ok = skip = 0
        qs = Major.objects.filter(is_active=True)
        if not all_majors:
            qs = qs.filter(slug__in=GSC_MAJOR_SLUGS)
        for major in qs.iterator():
            if attach_major_image(major, force=force):
                ok += 1
            else:
                skip += 1
        return ok, skip
