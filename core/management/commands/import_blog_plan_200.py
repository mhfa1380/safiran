"""
وارد کردن ۲۰۰ مقاله از plan_200.json به BlogPost با محتوای کامل SEO.
"""

from __future__ import annotations

import json
from pathlib import Path

from django.conf import settings
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction

from core.blog_covers import generate_blog_cover
from core.blog_content import generate_blog_article
from core.models import BlogAuthor, BlogPost

PLAN_PATH = Path(settings.BASE_DIR) / "data" / "blog_seo_plan" / "plan_200.json"


class Command(BaseCommand):
    help = "Import 200 SEO blog posts from plan_200.json with full HTML content"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Update existing posts with same slug",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Limit number of posts (0 = all)",
        )
        parser.add_argument(
            "--skip-covers",
            action="store_true",
            help="Do not generate cover images",
        )
        parser.add_argument(
            "--skip-dates",
            action="store_true",
            help="Do not run stagger_blog_publish after import",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Generate only, no DB writes",
        )

    def handle(self, *args, **options):
        if not PLAN_PATH.is_file():
            self.stderr.write(f"Missing {PLAN_PATH}")
            return

        plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
        articles = plan.get("articles", [])
        if options["limit"]:
            articles = articles[: options["limit"]]

        force = options["force"]
        dry_run = options["dry_run"]
        covers_dir = Path(settings.BASE_DIR) / "static" / "img" / "blog" / "covers"
        covers_dir.mkdir(parents=True, exist_ok=True)

        author = None
        if not dry_run:
            author, _ = BlogAuthor.objects.get_or_create(
                name="موژان الفیان",
                defaults={
                    "bio": (
                        "کارشناس مهاجرت تحصیلی در موسسه سفیران آینده روشن؛ "
                        "تولید محتوای تخصصی درباره اپلای، ویزا و زندگی دانشجویی."
                    ),
                    "role": "کارشناس مهاجرت تحصیلی",
                    "is_active": True,
                    "order": 0,
                },
            )

        created = updated = skipped = 0
        low_word = 0

        for raw in articles:
            slug = raw["slug"]
            exists = BlogPost.objects.filter(slug=slug).exists()
            if exists and not force:
                skipped += 1
                continue

            generated = generate_blog_article(raw)
            wc = generated["word_count"]
            if wc < 1500:
                low_word += 1

            if dry_run:
                self.stdout.write(f"[dry] {slug} ({wc} words)")
                continue

            defaults = {
                "title": raw["title"][:250],
                "excerpt": generated["excerpt"],
                "content": generated["content"],
                "country_tag": raw.get("category", "")[:100],
                "is_published": True,
                "meta_title": generated["meta_title"][:200],
                "meta_description": generated["meta_description"],
                "meta_keywords": generated["meta_keywords"][:300],
                "author": author,
            }

            with transaction.atomic():
                if exists:
                    post = BlogPost.objects.get(slug=slug)
                    for k, v in defaults.items():
                        setattr(post, k, v)
                    post.save()
                    updated += 1
                else:
                    post = BlogPost(slug=slug, **defaults)
                    post.save()
                    created += 1

                if not options["skip_covers"]:
                    jpeg = generate_blog_cover(slug, raw.get("category", ""))
                    (covers_dir / f"{slug}.jpg").write_bytes(jpeg)
                    post.image.save(f"{slug}.jpg", ContentFile(jpeg), save=True)

        if not dry_run:
            cache.delete("blog_tags")
            call_command("inject_blog_internal_links", verbosity=0)
            if not options["skip_dates"]:
                call_command("stagger_blog_publish", verbosity=1)

        self.stdout.write(
            self.style.SUCCESS(
                f"Import done: {created} created, {updated} updated, "
                f"{skipped} skipped, {low_word} below 1500 words"
            )
        )
        total = BlogPost.objects.filter(is_published=True).count()
        self.stdout.write(f"Published posts total: {total}")
