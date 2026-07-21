"""
بهینه‌سازی کامل سئو GSC — متا همه صفحات، تصاویر و ping sitemap.

استفاده:
  python manage.py boost_gsc_seo
  python manage.py boost_gsc_seo --meta-only
"""
from __future__ import annotations

from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Full GSC SEO boost: meta for all pages, images, world countries, sitemap ping"

    def add_arguments(self, parser):
        parser.add_argument(
            "--meta-only",
            action="store_true",
            help="Only refresh meta titles/descriptions",
        )
        parser.add_argument(
            "--skip-images",
            action="store_true",
            help="Skip image attachment",
        )
        parser.add_argument(
            "--force-images",
            action="store_true",
            help="Replace existing images",
        )

    def handle(self, *args, **options):
        meta_only = options["meta_only"]
        improve_args = ["--all-majors", "--all-universities", "--world-countries"]
        if meta_only:
            improve_args.append("--meta-only")
        if options["skip_images"]:
            improve_args.append("--meta-only")
        if options["force_images"]:
            improve_args.append("--force-images")

        self.stdout.write("Running improve_gsc_seo (full boost)...")
        call_command("improve_gsc_seo", *improve_args)

        if not meta_only:
            self.stdout.write("Refreshing rich human content by search queries (phase q)...")
            call_command("refresh_rich_content", "--phase", "q", "--replace-faqs")

        self.stdout.write("Syncing GSC not-indexed priorities...")
        call_command("sync_gsc_indexing_priorities")

        if not meta_only:
            self.stdout.write("Enriching thin GSC pages for indexing...")
            call_command("enrich_indexing_content", "--from-gsc", "--thin-only")

        if not meta_only and not options["skip_images"]:
            self.stdout.write("Refreshing world country catalog...")
            call_command("seed_study_countries", "--create-missing")

        from core.seo_ping import ping_search_engines_sitemap

        ping_search_engines_sitemap()
        self.stdout.write(self.style.SUCCESS("GSC SEO boost complete — sitemap ping queued"))
