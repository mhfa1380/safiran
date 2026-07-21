"""داده اولیه دستاوردهای ماه — قابل اجرای مجدد (فقط در صورت خالی بودن)."""

from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand

from core.models import MonthlyAchievement

SEED_ITEMS = [
    {
        "person_name": "سارا محمدی",
        "person_role": "کارشناسی ارشد مهندسی نرم‌افزار — کانادا",
        "title": "از مشاوره اول تا ویزای تحصیلی در ۸ ماه",
        "description": (
            "با برنامه‌ریزی دقیق و انتخاب دانشگاه مناسب، پرونده پذیرش من در دو ترم متوالی "
            "بررسی شد و در نهایت ویزای تحصیلی کانادا را دریافت کردم. تیم موسسه در هر مرحله "
            "مدارک، مصاحبه و آماده‌سازی مالی را همراهی کرد."
        ),
        "month_label": "اردیبهشت ۱۴۰۵",
        "is_featured": True,
        "order": 1,
        "image": "banner_img.png",
        "video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    },
    {
        "person_name": "علی رضایی",
        "person_role": "کارشناسی ارشد مدیریت — آلمان",
        "title": "پذیرش بدون مدرک زبان با شرط دوره زبان",
        "description": (
            "با راهنمایی مشاوران، دانشگاهی را انتخاب کردم که پذیرش مشروط زبان داشت. "
            "پس از گذراندن دوره زبان در آلمان، تحصیل را آغاز کردم و تجربه‌ای امن و "
            "ساختارمند داشتم."
        ),
        "month_label": "اردیبهشت ۱۴۰۵",
        "is_featured": False,
        "order": 2,
        "image": "learning_img.png",
    },
    {
        "person_name": "مریم حسینی",
        "person_role": "دکتری زیست‌فناوری — چین",
        "title": "بورسیه کامل و اسکان در خوابگاه دانشگاه",
        "description": (
            "پرونده بورسیه من با تمرکز بر رزومه پژوهشی و پیشنهاد تحقیقاتی تنظیم شد. "
            "نتیجه، پذیرش با بورسیه کامل و معرفی به اساتید راهنما بود."
        ),
        "month_label": "فروردین ۱۴۰۵",
        "is_featured": True,
        "order": 3,
        "image": "single_cource.webp",
    },
    {
        "person_name": "امیر کریمی",
        "person_role": "کارشناسی معماری — اسپانیا",
        "title": "ساخت پورتفولیو و پذیرش در دانشگاه هنر بارسلونا",
        "description": (
            "برای رشته‌های هنری، کیفیت پورتفولیو تعیین‌کننده است. با بازبینی آثار و "
            "مصاحبه شبیه‌سازی‌شده، پذیرش نهایی را از دانشگاه مورد علاقه‌ام گرفتم."
        ),
        "month_label": "فروردین ۱۴۰۵",
        "is_featured": False,
        "order": 4,
        "image": "single_blog_4.png",
        "subdir": "blog",
    },
    {
        "person_name": "نازنین احمدی",
        "person_role": "کارشناسی پرستاری — کانادا",
        "title": "مسیر COLLEGE و اخذ Co-op",
        "description": (
            "برای مقطع کالج، انتخاب برنامه Co-op اهمیت زیادی دارد. مشاوران مسیر "
            "مناسب با بازار کار کانادا را پیشنهاد دادند و ویزای من بدون تأخیر صادر شد."
        ),
        "month_label": "اسفند ۱۴۰۴",
        "is_featured": False,
        "order": 5,
        "image": "about_overlay.png",
    },
    {
        "person_name": "پارسا نوری",
        "person_role": "MBA — کانادا",
        "title": "تجربه موفق با سابقه کاری ۴ ساله",
        "description": (
            "برای MBA، تمرکز روی رزومه حرفه‌ای و انگیزه‌نامه بود. با داستان‌سرایی "
            "درست در SOP و آماده‌سازی مصاحبه، پذیرش نهایی را دریافت کردم."
        ),
        "month_label": "اسفند ۱۴۰۴",
        "is_featured": True,
        "order": 6,
        "image": "banner_img.png",
    },
]


class Command(BaseCommand):
    help = "ایجاد داده نمونه برای صفحه دستاوردهای ماه"

    def handle(self, *args, **options):
        if MonthlyAchievement.objects.exists():
            self.stdout.write(self.style.WARNING("دستاوردها از قبل وجود دارند؛ seed رد شد."))
            return

        static_root = Path(settings.BASE_DIR) / "static" / "img"
        created = 0

        for raw in SEED_ITEMS:
            item = raw.copy()
            image_name = item.pop("image")
            subdir = item.pop("subdir", "")
            video_url = item.pop("video_url", "")

            image_path = static_root / subdir / image_name if subdir else static_root / image_name
            if not image_path.is_file():
                self.stdout.write(self.style.WARNING(f"تصویر یافت نشد: {image_path}"))
                continue

            achievement = MonthlyAchievement(
                video_url=video_url,
                is_active=True,
                **item,
            )
            with image_path.open("rb") as img_file:
                achievement.image.save(image_name, File(img_file), save=False)
            achievement.save()
            created += 1

        self.stdout.write(self.style.SUCCESS(f"Created {created} sample achievements."))
