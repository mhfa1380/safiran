"""
پر کردن description و FAQ صفحات نازک برای بهبود ایندکس گوگل (Crawled/Discovered not indexed).

استفاده:
  python manage.py enrich_indexing_content
  python manage.py enrich_indexing_content --from-gsc --limit 500
  python manage.py enrich_indexing_content --thin-only --all
"""
from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count, Q

from core.gsc_export import load_gsc_not_indexed_slugs
from core.models import Major, MajorFAQ, University, UniversityFAQ
from core.seed_data.content_builders import (
    build_major_description,
    build_major_faqs,
    build_major_meta_description,
    build_major_meta_title,
    build_major_short,
    build_university_description,
    build_university_faqs,
    build_university_meta_description,
    build_university_meta_title,
    build_university_short,
)
from core.study_destinations import ALL_DESTINATION_LABELS

_THIN_DESC_LEN = 80


def _country_label(code: str) -> str:
    return ALL_DESTINATION_LABELS.get(code, code)


def _uni_item_dict(uni: University) -> dict:
    return {
        "name_fa": uni.name_fa,
        "name_en": uni.name_en or "",
        "city": uni.city or "",
        "world_rank": uni.world_rank,
        "website": uni.website or "",
        "mo_science": uni.is_approved_by_mo_science,
        "mo_health": uni.is_approved_by_mo_health,
    }


def _major_needs_enrichment(major: Major, *, thin_only: bool) -> bool:
    if not thin_only:
        return True
    desc = (major.description or "").strip()
    short = (major.short_description or "").strip()
    if len(desc) < _THIN_DESC_LEN and len(short) < 40:
        return True
    return major.faqs.filter(is_active=True).count() == 0


def _university_needs_enrichment(uni: University, *, thin_only: bool) -> bool:
    if not thin_only:
        return True
    desc = (uni.description or "").strip()
    short = (uni.short_description or "").strip()
    if len(desc) < _THIN_DESC_LEN and len(short) < 40:
        return True
    return uni.faqs.filter(is_active=True).count() == 0


class Command(BaseCommand):
    help = "Enrich thin major/university pages with descriptions and FAQs for Google indexing"

    def add_arguments(self, parser):
        parser.add_argument(
            "--from-gsc",
            action="store_true",
            help="Only slugs listed in GSC not-indexed exports",
        )
        parser.add_argument(
            "--thin-only",
            action="store_true",
            default=True,
            help="Only pages with empty/short description or no FAQs (default)",
        )
        parser.add_argument(
            "--all",
            action="store_true",
            help="Enrich all matching slugs even if content exists",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Max majors + universities to update (0 = no limit)",
        )
        parser.add_argument(
            "--majors-only",
            action="store_true",
            help="Skip universities",
        )
        parser.add_argument(
            "--universities-only",
            action="store_true",
            help="Skip majors",
        )

    def handle(self, *args, **options):
        thin_only = not options["all"]
        limit = options["limit"]
        gsc_majors: set[str] | None = None
        gsc_unis: set[str] | None = None

        if options["from_gsc"]:
            raw = load_gsc_not_indexed_slugs()
            gsc_majors, gsc_unis = raw["majors"], raw["universities"]
            self.stdout.write(
                f"GSC slugs: {len(gsc_majors)} majors, {len(gsc_unis)} universities"
            )

        remaining = limit if limit > 0 else None
        major_count = 0
        uni_count = 0

        if not options["universities_only"]:
            major_count = self._enrich_majors(
                gsc_majors,
                thin_only=thin_only,
                remaining=remaining,
            )
            if remaining is not None:
                remaining = max(0, remaining - major_count)

        if not options["majors_only"]:
            uni_count = self._enrich_universities(
                gsc_unis,
                thin_only=thin_only,
                remaining=remaining,
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Enriched {major_count} majors, {uni_count} universities"
            )
        )

    def _enrich_majors(
        self,
        gsc_slugs: set[str] | None,
        *,
        thin_only: bool,
        remaining: int | None,
    ) -> int:
        qs = Major.objects.filter(is_active=True).annotate(
            faq_count=Count("faqs", filter=Q(faqs__is_active=True))
        )
        if gsc_slugs is not None:
            qs = qs.filter(slug__in=gsc_slugs)
        elif thin_only:
            qs = qs.filter(
                Q(description__isnull=True)
                | Q(description="")
                | Q(short_description__isnull=True)
                | Q(short_description="")
                | Q(faq_count=0)
            )

        updated = 0
        for major in qs.order_by("id").iterator(chunk_size=200):
            if remaining is not None and updated >= remaining:
                break
            if thin_only and not _major_needs_enrichment(major, thin_only=True):
                continue

            label = _country_label(major.country or "")
            title = major.title or major.slug
            fields: dict = {}

            if not (major.short_description or "").strip():
                fields["short_description"] = build_major_short(title, label)
            if len((major.description or "").strip()) < _THIN_DESC_LEN:
                fields["description"] = build_major_description(
                    title, major.country or "", label
                )
            if not (major.meta_title or "").strip():
                fields["meta_title"] = build_major_meta_title(
                    title, label, major.country or ""
                )
            if not (major.meta_description or "").strip():
                fields["meta_description"] = build_major_meta_description(
                    title, label, major.country or ""
                )

            with transaction.atomic():
                if fields:
                    for k, v in fields.items():
                        setattr(major, k, v)
                    major.save(update_fields=list(fields.keys()))
                if major.faq_count == 0:
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
            updated += 1

        return updated

    def _enrich_universities(
        self,
        gsc_slugs: set[str] | None,
        *,
        thin_only: bool,
        remaining: int | None,
    ) -> int:
        qs = University.objects.annotate(
            faq_count=Count("faqs", filter=Q(faqs__is_active=True))
        )
        if gsc_slugs is not None:
            qs = qs.filter(slug__in=gsc_slugs)
        elif thin_only:
            qs = qs.filter(
                Q(description__isnull=True)
                | Q(description="")
                | Q(short_description__isnull=True)
                | Q(short_description="")
                | Q(faq_count=0)
            )

        updated = 0
        for uni in qs.order_by("id").iterator(chunk_size=100):
            if remaining is not None and updated >= remaining:
                break
            if thin_only and not _university_needs_enrichment(uni, thin_only=True):
                continue

            label = _country_label(uni.country or "")
            item = _uni_item_dict(uni)
            fields: dict = {}

            if not (uni.short_description or "").strip():
                fields["short_description"] = build_university_short(item, label)
            if len((uni.description or "").strip()) < _THIN_DESC_LEN:
                fields["description"] = build_university_description(
                    item, uni.country or "", label
                )
            if not (uni.meta_title or "").strip():
                fields["meta_title"] = build_university_meta_title(
                    item, label, uni.country or ""
                )
            if not (uni.meta_description or "").strip():
                fields["meta_description"] = build_university_meta_description(
                    item, label, uni.country or ""
                )

            with transaction.atomic():
                if fields:
                    for k, v in fields.items():
                        setattr(uni, k, v)
                    uni.save(update_fields=list(fields.keys()))
                if uni.faq_count == 0:
                    faqs = build_university_faqs(item, label)
                    UniversityFAQ.objects.bulk_create(
                        [
                            UniversityFAQ(
                                university=uni,
                                question=q,
                                answer=a,
                                order=i + 1,
                                is_active=True,
                            )
                            for i, (q, a) in enumerate(faqs)
                        ]
                    )
            updated += 1

        return updated
