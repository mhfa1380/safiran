"""ثبت دوره‌های زبان (مسیر TOEFL) در دیتابیس."""
from django.core.management.base import BaseCommand

from core.seed_data.language_courses import seed_language_courses


class Command(BaseCommand):
    help = "ایجاد یا به‌روزرسانی دوره‌های زبان مسیر TOEFL برای لیست دوره‌ها و ارزیابی هوشمند."

    def handle(self, *args, **options):
        self.stdout.write("Seeding TOEFL language courses…")
        stats = seed_language_courses(stdout_write=self.stdout.write)
        self.stdout.write(
            self.style.SUCCESS(
                f"Done — created: {stats['created']}, updated: {stats['updated']}"
            )
        )
