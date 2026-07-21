"""به‌روزرسانی slug و کلمات کلیدی دستاوردهای موجود."""

from django.core.management.base import BaseCommand

from core.models import MonthlyAchievement

KEYWORDS_MAP = {
    "سارا محمدی": "کانادا, ویزا, ارشد, نرم‌افزار, پذیرش",
    "علی رضایی": "آلمان, زبان, ارشد, مدیریت, پذیرش مشروط",
    "مریم حسینی": "چین, بورسیه, دکتری, زیست‌فناوری",
    "امیر کریمی": "اسپانیا, معماری, پورتفولیو, کارشناسی",
    "نازنین احمدی": "کانادا, پرستاری, کالج, co-op, ویزا",
    "پارسا نوری": "کانادا, MBA, کار, SOP, مصاحبه",
}


class Command(BaseCommand):
    help = "Update search_keywords and slugs for achievements"

    def handle(self, *args, **options):
        updated = 0
        for obj in MonthlyAchievement.objects.all():
            changed = False
            if not obj.slug:
                obj.slug = obj._build_unique_slug()
                changed = True
            if not obj.search_keywords and obj.person_name in KEYWORDS_MAP:
                obj.search_keywords = KEYWORDS_MAP[obj.person_name]
                changed = True
            if not (obj.detail_content or "").strip() and obj.description:
                obj.detail_content = f"<p>{obj.description}</p>"
                changed = True
            if changed:
                obj.save()
                updated += 1
        self.stdout.write(f"Updated {updated} achievements.")
