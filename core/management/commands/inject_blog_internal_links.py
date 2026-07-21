"""
درج لینک‌های داخلی SEO در محتوای همه پست‌های وبلاگ.
"""

from __future__ import annotations

from django.core.cache import cache
from django.core.management.base import BaseCommand

from core.blog_internal_links import inject_links_into_content
from core.models import BlogPost


class Command(BaseCommand):
    help = "Inject internal link blocks into all published blog post HTML"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Count only, no save",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
        )

    def handle(self, *args, **options):
        qs = BlogPost.objects.filter(is_published=True).order_by("slug")
        if options["limit"]:
            qs = qs[: options["limit"]]

        updated = 0
        for post in qs:
            new_content = inject_links_into_content(post.content or "", post)
            if new_content == post.content:
                continue
            if not options["dry_run"]:
                BlogPost.objects.filter(pk=post.pk).update(content=new_content)
            updated += 1

        if not options["dry_run"]:
            cache.delete("blog_tags")

        self.stdout.write(
            self.style.SUCCESS(
                f"Internal links: {updated} posts updated (of {qs.count()} checked)"
            )
        )
