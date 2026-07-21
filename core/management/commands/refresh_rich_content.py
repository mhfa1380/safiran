"""
به‌روزرسانی محتوای غنی صفحات — فازبندی بر اساس GSC و اولویت جستجوی کاربران.

فاز q: کوئری‌های پرجستجو (اولویت اول)
فاز ۱: Performance (پربازدید + CTR پایین)
فاز ۲: Crawled not indexed
فاز ۳: Discovered not indexed
فاز ۴: همه صفحات فعال

استفاده:
  python manage.py refresh_rich_content --phase q --replace-faqs
  python manage.py refresh_rich_content --phase 2 --limit 300 --replace-faqs
"""
from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from core.gsc_export import (
    load_gsc_crawled_not_indexed_slugs,
    load_gsc_discovered_not_indexed_slugs,
)
from core.gsc_performance import load_gsc_performance_priorities
from core.gsc_query_priority import resolve_queries_to_slugs
from core.models import Major, MajorFAQ, University, UniversityFAQ
from core.seed_data.content_builders import build_major_meta_description, build_major_meta_title
from core.seed_data.rich_content import (
    build_rich_major_description,
    build_rich_major_faqs,
    build_rich_major_short,
    build_rich_university_description,
    build_rich_university_faqs,
    build_rich_university_short,
    university_dict_from_model,
)
from core.study_destinations import ALL_DESTINATION_LABELS


def _label(code: str) -> str:
    return ALL_DESTINATION_LABELS.get(code, code)


class Command(BaseCommand):
    help = "Refresh long human SEO content for majors/universities by GSC phase"

    def add_arguments(self, parser):
        parser.add_argument(
            "--phase",
            choices=("q", "1", "2", "3", "4", "all"),
            default="q",
            help="q=search queries (top priority), 1=Performance, 2-3=not indexed, 4=all",
        )
        parser.add_argument("--limit", type=int, default=0, help="Max items per kind (0=all)")
        parser.add_argument("--majors-only", action="store_true")
        parser.add_argument("--universities-only", action="store_true")
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument(
            "--replace-faqs",
            action="store_true",
            help="Replace existing FAQs with rich versions",
        )

    def handle(self, *args, **options):
        phases = ("q", "1", "2", "3", "4") if options["phase"] == "all" else (options["phase"],)
        major_slugs: set[str] = set()
        uni_slugs: set[str] = set()
        queries_by_major: dict[str, list[str]] = {}
        queries_by_university: dict[str, list[str]] = {}

        query_data = resolve_queries_to_slugs()
        queries_by_major.update(query_data["queries_by_major"])
        queries_by_university.update(query_data["queries_by_university"])

        for phase in phases:
            m, u = self._slugs_for_phase(phase, query_data)
            major_slugs |= m
            uni_slugs |= u
            self.stdout.write(f"Phase {phase}: +{len(m)} majors, +{len(u)} universities")

        if query_data["top_queries"]:
            self.stdout.write(f"Top search queries: {len(query_data['top_queries'])}")

        limit = options["limit"] or None
        dry = options["dry_run"]
        replace_faqs = options["replace_faqs"]

        mc = uc = 0
        if not options["universities_only"]:
            mc = self._refresh_majors(
                major_slugs,
                limit=limit,
                dry_run=dry,
                replace_faqs=replace_faqs,
                queries_by_major=queries_by_major,
            )
        if not options["majors_only"]:
            uc = self._refresh_universities(
                uni_slugs,
                limit=limit,
                dry_run=dry,
                replace_faqs=replace_faqs,
                queries_by_university=queries_by_university,
            )

        msg = f"Rich content: {mc} majors, {uc} universities"
        if dry:
            msg = "[dry-run] " + msg
        self.stdout.write(self.style.SUCCESS(msg))
        if not dry and (mc or uc):
            from core.cache_utils import invalidate_layout_caches

            invalidate_layout_caches()

    def _slugs_for_phase(self, phase: str, query_data: dict) -> tuple[set[str], set[str]]:
        if phase == "q":
            return set(query_data["majors"]), set(query_data["universities"])
        if phase == "1":
            data = load_gsc_performance_priorities()
            return set(data["majors"]), set(data["universities"])
        if phase == "2":
            data = load_gsc_crawled_not_indexed_slugs()
            return set(data["majors"]), set(data["universities"])
        if phase == "3":
            data = load_gsc_discovered_not_indexed_slugs()
            return set(data["majors"]), set(data["universities"])
        if phase == "4":
            return (
                set(Major.objects.filter(is_active=True).values_list("slug", flat=True)),
                set(University.objects.values_list("slug", flat=True)),
            )
        return set(), set()

    def _refresh_majors(
        self,
        slugs: set[str],
        *,
        limit: int | None,
        dry_run: bool,
        replace_faqs: bool,
        queries_by_major: dict[str, list[str]],
    ) -> int:
        if not slugs:
            return 0
        qs = Major.objects.filter(is_active=True, slug__in=slugs).order_by("id")
        updated = 0
        for major in qs.iterator(chunk_size=100):
            if limit is not None and updated >= limit:
                break
            label = _label(major.country or "")
            title = major.title or major.slug
            qlist = queries_by_major.get(major.slug, [])
            desc = build_rich_major_description(
                title, major.country or "", label, search_queries=qlist
            )
            short = build_rich_major_short(title, label, major.country or "")
            meta_title = build_major_meta_title(title, label, major.country or "")
            meta_description = build_major_meta_description(title, label, major.country or "")
            if dry_run:
                updated += 1
                continue
            with transaction.atomic():
                major.short_description = short
                major.description = desc
                major.meta_title = meta_title
                major.meta_description = meta_description
                major.save(
                    update_fields=[
                        "short_description",
                        "description",
                        "meta_title",
                        "meta_description",
                    ]
                )
                if replace_faqs or not major.faqs.exists():
                    if replace_faqs:
                        major.faqs.all().delete()
                    faqs = build_rich_major_faqs(
                        title, label, major.country or "", search_queries=qlist
                    )
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

    def _refresh_universities(
        self,
        slugs: set[str],
        *,
        limit: int | None,
        dry_run: bool,
        replace_faqs: bool,
        queries_by_university: dict[str, list[str]],
    ) -> int:
        if not slugs:
            return 0
        qs = University.objects.filter(slug__in=slugs).order_by("id")
        updated = 0
        for uni in qs.iterator(chunk_size=50):
            if limit is not None and updated >= limit:
                break
            item = university_dict_from_model(uni)
            label = _label(uni.country or "")
            qlist = queries_by_university.get(uni.slug, [])
            desc = build_rich_university_description(
                item,
                uni.country or "",
                label,
                slug=uni.slug,
                search_queries=qlist,
            )
            short = build_rich_university_short(item, label, uni.country or "")
            if dry_run:
                updated += 1
                continue
            with transaction.atomic():
                uni.short_description = short
                uni.description = desc
                uni.save(update_fields=["short_description", "description"])
                if replace_faqs or not uni.faqs.exists():
                    if replace_faqs:
                        uni.faqs.all().delete()
                    faqs = build_rich_university_faqs(
                        item, label, uni.country or "", search_queries=qlist
                    )
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
