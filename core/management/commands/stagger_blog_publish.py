"""
زمان‌بندی تاریخ انتشار وبلاگ (۲ پست در روز، از امروز به عقب) و تصاویر شاخص اختصاصی.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from django.conf import settings
from django.core.cache import cache
from django.core.files import File
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db.models import Case, IntegerField, Value, When
from django.utils import timezone

from core.blog_covers import generate_blog_cover
from core.blog_internal_links import stable_minute_offset
from core.models import BlogPost
from core.seed_data.blog_publish_order import (
    BLOG_ORIGINAL_32_SLUGS,
    build_full_popularity_order,
)

# ساعت‌های انتشار در هر روز (تهران)
_SLOT_HOURS = (10, 35), (16, 20)


class Command(BaseCommand):
    help = "تاریخ‌گذاری ۲ بلاگ/روز بر اساس محبوبیت + تصویر شاخص برای ۳۲ مقاله اول"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dates-only",
            action="store_true",
            help="فقط created_at را به‌روز کن",
        )
        parser.add_argument(
            "--images-only",
            action="store_true",
            help="فقط تصاویر را بساز/آپلود کن",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="بدون ذخیره در دیتابیس",
        )
        parser.add_argument(
            "--posts-per-day",
            type=int,
            default=2,
            help="تعداد پست در هر روز (پیش‌فرض: ۲)",
        )

    def handle(self, *args, **options):
        dates_only = options["dates_only"]
        images_only = options["images_only"]
        dry_run = options["dry_run"]
        per_day = max(1, options["posts_per_day"])

        if dates_only and images_only:
            self.stderr.write("Use only one of --dates-only or --images-only.")
            return

        do_dates = not images_only
        do_images = not dates_only

        covers_dir = Path(settings.BASE_DIR) / "static" / "img" / "blog" / "covers"
        covers_dir.mkdir(parents=True, exist_ok=True)

        order_index = self._build_order_index()
        posts = self._ordered_posts(order_index)

        if not posts:
            self.stdout.write(self.style.WARNING("No published blog posts found."))
            return

        if do_dates:
            self._apply_dates(posts, per_day, dry_run)

        if do_images:
            self._apply_images(posts, covers_dir, dry_run)

        if not dry_run:
            cache.delete("blog_tags")

        self.stdout.write(self.style.SUCCESS(f"Done — processed {len(posts)} posts."))

    def _build_order_index(self) -> dict[str, int]:
        return {slug: i for i, slug in enumerate(build_full_popularity_order())}

    def _ordered_posts(self, order_index: dict[str, int]) -> list[BlogPost]:
        fallback = len(order_index) + 10_000
        whens = [
            When(slug=slug, then=Value(rank)) for slug, rank in order_index.items()
        ]
        qs = BlogPost.objects.filter(is_published=True).annotate(
            _pop_rank=Case(
                *whens,
                default=Value(fallback),
                output_field=IntegerField(),
            )
        )
        return list(qs.order_by("_pop_rank", "slug"))

    def _publish_datetime(self, slot_index: int, per_day: int, slug: str = "") -> datetime:
        day_offset = slot_index // per_day
        slot_in_day = slot_index % per_day
        hour, minute = _SLOT_HOURS[slot_in_day % len(_SLOT_HOURS)]
        minute = (minute + (slot_index * 5)) % 60
        if slug:
            minute = (minute + stable_minute_offset(slug)) % 60
        base = timezone.localtime(timezone.now()).replace(
            hour=hour, minute=minute, second=0, microsecond=0
        )
        return base - timedelta(days=day_offset)

    def _apply_dates(self, posts: list[BlogPost], per_day: int, dry_run: bool) -> None:
        self.stdout.write("Scheduling publish dates (higher popularity = newer):")
        for i, post in enumerate(posts):
            dt = self._publish_datetime(i, per_day, post.slug)
            local = timezone.localtime(dt)
            if dry_run:
                self.stdout.write(f"  [dry] {post.slug} -> {local:%Y-%m-%d %H:%M}")
                continue
            BlogPost.objects.filter(pk=post.pk).update(
                created_at=dt,
                updated_at=dt,
            )
            if i < 6 or i >= len(posts) - 2:
                self.stdout.write(f"  {post.slug} -> {local:%Y-%m-%d %H:%M}")

        if len(posts) > 8:
            self.stdout.write(f"  ... and {len(posts) - 8} more posts")

    def _apply_images(
        self,
        posts: list[BlogPost],
        covers_dir: Path,
        dry_run: bool,
    ) -> None:
        self.stdout.write("Blog cover images:")
        cover_slugs = BLOG_ORIGINAL_32_SLUGS | {
            "free-online-study-abroad-evaluation-smart-report",
        }
        for post in posts:
            if post.slug not in cover_slugs:
                continue

            filename = f"{post.slug}.jpg"
            file_path = covers_dir / filename
            jpeg = generate_blog_cover(post.slug, post.country_tag or "")
            if not dry_run:
                file_path.write_bytes(jpeg)
                post.image.save(filename, ContentFile(jpeg), save=True)
            else:
                self.stdout.write(f"  [dry] cover -> {file_path.name}")
            self.stdout.write(f"  {post.slug} -> blog/covers/{filename}")
