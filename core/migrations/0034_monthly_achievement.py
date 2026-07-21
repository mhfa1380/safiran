from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0033_alter_faq_is_featured_alter_faq_slug"),
    ]

    operations = [
        migrations.CreateModel(
            name="MonthlyAchievement",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("person_name", models.CharField(max_length=150, verbose_name="نام و نام خانوادگی")),
                (
                    "person_role",
                    models.CharField(
                        blank=True,
                        help_text="مثلاً پذیرش کارشناسی ارشد — کانادا",
                        max_length=200,
                        verbose_name="عنوان / مقصد",
                    ),
                ),
                ("title", models.CharField(max_length=250, verbose_name="عنوان دستاورد")),
                ("description", models.TextField(verbose_name="توضیحات")),
                (
                    "image",
                    models.ImageField(
                        help_text="تصویر پرتره یا مستند دستاورد",
                        upload_to="achievements/",
                        verbose_name="عکس",
                    ),
                ),
                (
                    "video_file",
                    models.FileField(
                        blank=True,
                        help_text="ویدیوی مصاحبه یا مستند (اختیاری)",
                        upload_to="achievements/videos/",
                        verbose_name="فایل ویدیو",
                    ),
                ),
                (
                    "video_url",
                    models.URLField(
                        blank=True,
                        help_text="یوتیوب، آپارات و… (اگر فایل آپلود نکردید)",
                        verbose_name="لینک ویدیو",
                    ),
                ),
                (
                    "month_label",
                    models.CharField(
                        blank=True,
                        help_text="مثلاً اردیبهشت ۱۴۰۵ — برای فیلتر در صفحه",
                        max_length=80,
                        verbose_name="برچسب ماه",
                    ),
                ),
                (
                    "is_featured",
                    models.BooleanField(
                        default=False,
                        help_text="کارت بزرگ‌تر در ابتدای لیست",
                        verbose_name="نمایش ویژه",
                    ),
                ),
                ("order", models.PositiveSmallIntegerField(default=0, verbose_name="ترتیب نمایش")),
                ("is_active", models.BooleanField(default=True, verbose_name="فعال")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ثبت")),
            ],
            options={
                "verbose_name": "دستاورد ماه",
                "verbose_name_plural": "دستاوردهای ماه",
                "db_table": "core_monthly_achievement",
                "ordering": ["-is_featured", "order", "-created_at"],
            },
        ),
    ]
