"""
گسترش کامل دانشگاه‌های چین، کانادا و اسپانیا از ویکی‌پدیا + لینک رشته‌ها + تصاویر.

فقط رکوردهای جدید اضافه می‌شوند؛ slug تکراری یا نام انگلیسی تکراری نادیده گرفته می‌شود.
تصاویر فقط برای دانشگاه/رشته‌ای که تصویر ندارند دانلود می‌شوند.

استفاده:
  python manage.py expand_all_universities
  python manage.py expand_all_universities --country canada
  python manage.py expand_all_universities --refresh-wikipedia
"""
from __future__ import annotations

from django.core.management import call_command
from django.core.management.base import BaseCommand

from core.models import Major, University, UniversityMajorLink
from core.seed_data.university_catalog_merge import get_merged_university_catalog


class Command(BaseCommand):
    help = (
        "Add all Wikipedia-listed universities for Canada/Spain/China, "
        "link majors, and attach missing images (no duplicates)"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--country",
            choices=["canada", "spain", "china", "all"],
            default="all",
        )
        parser.add_argument(
            "--refresh-wikipedia",
            action="store_true",
            help="Re-download Wikipedia lists (ignore cache)",
        )
        parser.add_argument(
            "--skip-images",
            action="store_true",
            help="Skip image download step",
        )

    def handle(self, *args, **options):
        country = options["country"]
        before_uni = University.objects.count()
        before_links = UniversityMajorLink.objects.count()

        self.stdout.write("Step 1/3: Seed universities (expanded catalog) + majors + links...")
        call_command(
            "seed_universities_majors",
            country=country,
            expand_all=True,
            refresh_wikipedia=options["refresh_wikipedia"],
            skip_images=True,
            verbosity=1,
        )

        after_uni = University.objects.count()
        after_links = UniversityMajorLink.objects.count()
        self.stdout.write(
            self.style.SUCCESS(
                f"Universities: {before_uni} → {after_uni} (+{after_uni - before_uni}), "
                f"links: {before_links} → {after_links} (+{after_links - before_links})"
            )
        )

        if not options["skip_images"]:
            self.stdout.write("Step 2/3: Images for universities/majors without cover...")
            countries = ["canada", "spain", "china"] if country == "all" else [country]
            call_command(
                "seed_universities_majors",
                country=country,
                images_only=True,
                verbosity=1,
            )

        self.stdout.write("Step 3/3: Catalog sizes (merged Wikipedia + top 30):")
        codes = ["canada", "spain", "china"] if country == "all" else [country]
        for code in codes:
            cat = get_merged_university_catalog(code, include_wikipedia=True)
            db = University.objects.filter(country=code).count()
            majors = Major.objects.filter(country=code, is_active=True).count()
            links = UniversityMajorLink.objects.filter(university__country=code).count()
            self.stdout.write(
                f"  {code}: catalog={len(cat)} db={db} majors={majors} links={links}"
            )

        self.stdout.write(
            self.style.SUCCESS(
                "Done. New pages are in sitemap.xml automatically (UniversitySitemap + MajorSitemap)."
            )
        )
