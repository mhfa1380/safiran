"""ایجاد/به‌روزرسانی پست‌های وبلاگ پرطرفدار بر اساس کلیک FAQ و خدمات."""

from pathlib import Path

from django.conf import settings
from django.core.cache import cache
from django.core.files import File
from django.core.management.base import BaseCommand
from core.models import BlogAuthor, BlogPost
from core.seed_data.blog_posts import BLOG_SEED_POSTS, BLOG_UNPUBLISH_SLUGS
from core.seed_data.blog_posts_extended import BLOG_SEED_POSTS_EXTENDED
from core.seed_data.blog_post_evaluation import BLOG_POST_EVALUATION_LANDING

ALL_BLOG_SEED_POSTS = [BLOG_POST_EVALUATION_LANDING] + BLOG_SEED_POSTS + BLOG_SEED_POSTS_EXTENDED


class Command(BaseCommand):
    help = "پر کردن وبلاگ با مطالب SEO (FAQ، کشورها، مهاجرت، غذا و فرهنگ)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="به‌روزرسانی پست‌های موجود با همان slug",
        )

    def handle(self, *args, **options):
        force = options["force"]
        static_root = Path(settings.BASE_DIR) / "static" / "img"

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
        for raw in ALL_BLOG_SEED_POSTS:
            slug = raw["slug"]
            exists = BlogPost.objects.filter(slug=slug).exists()
            if exists and not force:
                skipped += 1
                continue

            cover_path = static_root / "blog" / "covers" / f"{slug}.jpg"
            if cover_path.is_file():
                image_path = cover_path
                image_name = cover_path.name
            else:
                subdir, image_name = raw["image"]
                image_path = static_root / subdir / image_name if subdir else static_root / image_name
            if not image_path.is_file():
                self.stdout.write(self.style.WARNING(f"تصویر یافت نشد: {image_path}"))
                continue

            defaults = {
                "title": raw["title"],
                "excerpt": raw["excerpt"].strip(),
                "content": raw["content"].strip(),
                "country_tag": raw["country_tag"],
                "is_published": True,
                "meta_title": raw["meta_title"],
                "meta_description": raw["meta_description"],
                "meta_keywords": raw["meta_keywords"],
                "author": author,
            }

            if exists:
                post = BlogPost.objects.get(slug=slug)
                for key, val in defaults.items():
                    setattr(post, key, val)
                post.save()
                updated += 1
            else:
                post = BlogPost(slug=slug, **defaults)
                post.save()
                created += 1

            with image_path.open("rb") as img_file:
                post.image.save(image_name, File(img_file), save=True)

        unpublished = (
            BlogPost.objects.filter(slug__in=BLOG_UNPUBLISH_SLUGS, is_published=True)
            .update(is_published=False)
        )

        cache.delete("blog_tags")

        self.stdout.write(
            self.style.SUCCESS(
                f"وبلاگ: {created} ایجاد، {updated} به‌روز، {skipped} رد شد؛ "
                f"{unpublished} پست غیرمرتبط از انتشار خارج شد."
            )
        )
        total = BlogPost.objects.filter(is_published=True).count()
        self.stdout.write(f"تعداد پست‌های منتشرشده: {total}")
