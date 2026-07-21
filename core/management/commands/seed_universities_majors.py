"""
بارگذاری ۳۰ دانشگاه برتر هر کشور مقصد + رشته‌های کامل با محتوای سئو.

استفاده:
  python manage.py seed_universities_majors
  python manage.py seed_universities_majors --country canada
  python manage.py seed_universities_majors --majors-only
  python manage.py seed_universities_majors --universities-only
  python manage.py seed_universities_majors --links-only
"""
from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import Major, MajorFAQ, StudyCountry, University, UniversityFAQ, UniversityMajorLink
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
    major_slug,
)
from core.seed_data.major_catalog import MAJORS_BY_COUNTRY, get_all_catalog_slugs
from core.seed_data.university_catalog import (
    COUNTRY_LABELS,
    UNIVERSITY_CATALOG_BY_COUNTRY,
)
from core.seed_data.university_catalog_merge import (
    clear_merged_catalog_cache,
    get_all_merged_catalogs,
    get_merged_university_catalog,
)
from core.seed_data.university_major_links import (
    UNIVERSITY_SLUG_PROFILES,
    _default_categories,
    _major_matches_categories,
    get_major_titles_for_university,
)


class Command(BaseCommand):
    help = "Seed top-30 universities per study country and full major catalog with SEO content"

    def add_arguments(self, parser):
        parser.add_argument(
            "--country",
            choices=["canada", "spain", "china", "all"],
            default="all",
            help="Which country to seed (default: all active study countries)",
        )
        parser.add_argument(
            "--universities-only",
            action="store_true",
            help="Only seed universities (skip majors)",
        )
        parser.add_argument(
            "--majors-only",
            action="store_true",
            help="Only seed majors (skip universities)",
        )
        parser.add_argument(
            "--replace-faqs",
            action="store_true",
            help="Replace existing FAQs for touched universities/majors",
        )
        parser.add_argument(
            "--images-only",
            action="store_true",
            help="Only attach/download images for universities and majors",
        )
        parser.add_argument(
            "--force-images",
            action="store_true",
            help="Replace existing images when seeding",
        )
        parser.add_argument(
            "--all-major-countries",
            action="store_true",
            help="With --images-only: process every active major country, not only study catalog countries",
        )
        parser.add_argument(
            "--prune-majors",
            action="store_true",
            help="Deactivate majors whose slug is not in the current catalog (per country)",
        )
        parser.add_argument(
            "--links-only",
            action="store_true",
            help="Only seed university–major bidirectional links",
        )
        parser.add_argument(
            "--replace-links",
            action="store_true",
            help="Remove existing links for touched countries before re-linking",
        )
        parser.add_argument(
            "--expand-all",
            action="store_true",
            help="Include all universities from Wikipedia lists (Canada/Spain/China), not only top 30",
        )
        parser.add_argument(
            "--refresh-wikipedia",
            action="store_true",
            help="Re-fetch Wikipedia university lists (ignore JSON cache)",
        )
        parser.add_argument(
            "--skip-images",
            action="store_true",
            help="Skip automatic image download after seeding",
        )

    def handle(self, *args, **options):
        self._expand_all = options["expand_all"]
        self._refresh_wikipedia = options["refresh_wikipedia"]
        if self._refresh_wikipedia:
            clear_merged_catalog_cache()
        country_opt = options["country"]
        if options["universities_only"] and options["majors_only"]:
            self.stderr.write(self.style.ERROR("Cannot use both --universities-only and --majors-only"))
            return
        if options["links_only"] and (
            options["universities_only"] or options["majors_only"] or options["images_only"]
        ):
            self.stderr.write(self.style.ERROR("--links-only cannot combine with other mode flags"))
            return
        if options["images_only"] and (options["universities_only"] or options["majors_only"]):
            self.stderr.write(self.style.ERROR("--images-only cannot combine with --universities-only/--majors-only"))
            return

        countries = self._resolve_countries(country_opt)
        if not countries:
            self.stderr.write(self.style.WARNING("No active StudyCountry records found."))
            return

        self.stdout.write(f"Seeding for countries: {', '.join(countries)}")

        if options["links_only"]:
            with transaction.atomic():
                for code in countries:
                    self._seed_university_major_links(code, replace=options["replace_links"])
            self.stdout.write(self.style.SUCCESS("Done."))
            return

        if options["images_only"]:
            from core.seed_data.seed_images import (
                _WIKI_RAW_CACHE,
                seed_major_images,
                seed_study_country_images,
                seed_university_images,
            )

            major_countries = countries
            if options["all_major_countries"]:
                major_countries = None
                self.stdout.write("  Majors: all active countries")

            _WIKI_RAW_CACHE.clear()
            u_ok, u_skip = seed_university_images(countries, force=options["force_images"])
            m_ok, m_skip = seed_major_images(major_countries, force=options["force_images"])
            c_ok, c_skip = seed_study_country_images(countries, force=options["force_images"])
            self.stdout.write(f"  Images universities: {u_ok} set, {u_skip} skipped")
            self.stdout.write(f"  Images majors: {m_ok} set, {m_skip} skipped")
            self.stdout.write(f"  Images study countries: {c_ok} set, {c_skip} skipped")
            self.stdout.write(self.style.SUCCESS("Done."))
            return

        with transaction.atomic():
            if not options["majors_only"]:
                for code in countries:
                    self._seed_universities(code, replace_faqs=options["replace_faqs"])
            if not options["universities_only"]:
                for code in countries:
                    self._seed_majors(code, replace_faqs=options["replace_faqs"])
                if options["prune_majors"]:
                    self._prune_majors(countries)
            for code in countries:
                self._seed_university_major_links(code, replace=options["replace_links"])

        from core.seed_data.seed_images import (
            seed_major_images,
            seed_study_country_images,
            seed_university_images,
        )

        if not options["skip_images"]:
            u_ok, u_skip = seed_university_images(countries, force=options["force_images"])
            m_ok, m_skip = seed_major_images(countries, force=options["force_images"])
            c_ok, c_skip = seed_study_country_images(countries, force=options["force_images"])
            self.stdout.write(f"  Images universities: {u_ok} set, {u_skip} skipped")
            self.stdout.write(f"  Images majors: {m_ok} set, {m_skip} skipped")
            self.stdout.write(f"  Images study countries: {c_ok} set, {c_skip} skipped")

        self.stdout.write(self.style.SUCCESS("Done."))

    def _resolve_countries(self, country_opt: str) -> list[str]:
        qs = StudyCountry.objects.filter(is_active=True).values_list("code", flat=True)
        active = set(qs)
        catalog_codes = set(UNIVERSITY_CATALOG_BY_COUNTRY)
        if country_opt == "all":
            return sorted(active & catalog_codes)
        if country_opt in active:
            return [country_opt]
        self.stderr.write(
            self.style.WARNING(f"Country '{country_opt}' not in active StudyCountry; seeding anyway.")
        )
        return [country_opt] if country_opt in catalog_codes else []

    def _catalog_for_country(self, country_code: str) -> list[dict]:
        if self._expand_all:
            return get_merged_university_catalog(
                country_code,
                include_wikipedia=True,
                refresh_wikipedia=self._refresh_wikipedia,
            )
        return UNIVERSITY_CATALOG_BY_COUNTRY.get(country_code, [])

    def _seed_universities(self, country_code: str, *, replace_faqs: bool) -> None:
        catalog = self._catalog_for_country(country_code)
        label = COUNTRY_LABELS.get(country_code, country_code)
        created = updated = faq_count = 0

        for item in catalog:
            defaults = {
                "name_fa": item["name_fa"],
                "name_en": item["name_en"],
                "country": country_code,
                "city": item["city"],
                "type": University.TYPE_UNIVERSITY,
                "world_rank": item["world_rank"],
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

            if replace_faqs:
                uni.faqs.all().delete()
            if replace_faqs or not uni.faqs.exists():
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
                faq_count += len(faqs)

        self.stdout.write(
            f"  Universities [{country_code}]: {created} created, {updated} updated, {faq_count} FAQs"
        )

    def _seed_majors(self, country_code: str, *, replace_faqs: bool) -> None:
        titles = MAJORS_BY_COUNTRY.get(country_code, [])
        label = COUNTRY_LABELS.get(country_code, country_code)
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
            major, was_created = Major.objects.update_or_create(
                slug=slug,
                defaults=defaults,
            )
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

    def _prune_majors(self, countries: list[str]) -> None:
        catalog_slugs = get_all_catalog_slugs()
        pruned = 0
        for code in countries:
            keep = catalog_slugs.get(code, set())
            stale = Major.objects.filter(country=code, is_active=True).exclude(slug__in=keep)
            count = stale.count()
            if count:
                stale.update(is_active=False)
                pruned += count
                self.stdout.write(
                    self.style.WARNING(f"  Majors [{code}]: deactivated {count} stale row(s)")
                )
        if pruned:
            self.stdout.write(f"  Majors prune total: {pruned} deactivated")
        else:
            self.stdout.write("  Majors prune: nothing to remove")

    def _seed_university_major_links(self, country_code: str, *, replace: bool) -> None:
        catalog = self._catalog_for_country(country_code)
        majors_by_slug = {
            m.slug: m
            for m in Major.objects.filter(country=country_code, is_active=True).only("id", "slug")
        }
        if replace:
            deleted, _ = UniversityMajorLink.objects.filter(university__country=country_code).delete()
            if deleted:
                self.stdout.write(f"  Links [{country_code}]: removed {deleted} old link(s)")

        created = updated = skipped_uni = 0
        for item in catalog:
            uni = University.objects.filter(slug=item["slug"], country=country_code).first()
            if not uni:
                skipped_uni += 1
                continue
            titles = get_major_titles_for_university(item, country_code)
            keep_major_ids: set[int] = set()
            for order, title in enumerate(titles, start=1):
                slug = major_slug(country_code, title)
                major = majors_by_slug.get(slug)
                if not major:
                    continue
                keep_major_ids.add(major.id)
                _, was_created = UniversityMajorLink.objects.update_or_create(
                    university=uni,
                    major=major,
                    defaults={
                        "order": order,
                        "is_featured": order <= 8,
                    },
                )
                if was_created:
                    created += 1
                else:
                    updated += 1
            if keep_major_ids:
                stale = UniversityMajorLink.objects.filter(university=uni).exclude(
                    major_id__in=keep_major_ids
                )
                stale.delete()

        sync_created = self._sync_majors_to_universities(country_code)
        total_links = UniversityMajorLink.objects.filter(university__country=country_code).count()
        self.stdout.write(
            f"  Links [{country_code}]: {created} created, {updated} updated, "
            f"{sync_created} major-to-uni sync, {total_links} total links"
            + (f", {skipped_uni} university(ies) missing" if skipped_uni else "")
        )

    def _sync_majors_to_universities(self, country_code: str) -> int:
        """هر رشته فعال را به دانشگاه‌های هم‌پروفایل (حداکثر ۱۲) وصل می‌کند."""
        catalog = sorted(
            self._catalog_for_country(country_code),
            key=lambda x: int(x.get("world_rank") or 99),
        )
        unis = {
            u.slug: u
            for u in University.objects.filter(country=country_code).only("id", "slug")
        }
        created = 0
        for major in Major.objects.filter(country=country_code, is_active=True).only(
            "id", "title", "slug"
        ):
            matched: list[University] = []
            for item in catalog:
                uni = unis.get(item["slug"])
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
                    defaults={
                        "order": order,
                        "is_featured": order <= 4,
                    },
                )
                if was_created:
                    created += 1
        return created
