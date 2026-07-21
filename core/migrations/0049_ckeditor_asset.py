import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("core", "0048_admin_change_log"),
    ]

    operations = [
        migrations.CreateModel(
            name="CkeditorAsset",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "path",
                    models.CharField(
                        help_text="نسبت به MEDIA_ROOT، مثلاً ckeditor/abc.jpg",
                        max_length=300,
                        unique=True,
                        verbose_name="مسیر فایل",
                    ),
                ),
                ("size_bytes", models.PositiveIntegerField(default=0, verbose_name="حجم (بایت)")),
                ("uploaded_at", models.DateTimeField(auto_now_add=True, verbose_name="زمان آپلود")),
                (
                    "uploaded_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="ckeditor_uploads",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="آپلودکننده",
                    ),
                ),
                ("usage_count", models.PositiveIntegerField(default=0, verbose_name="تعداد استفاده")),
                (
                    "usage_snapshot",
                    models.JSONField(
                        blank=True,
                        default=list,
                        help_text="فهرست محتواهایی که این تصویر در آن‌ها درج شده است.",
                        verbose_name="محل‌های استفاده",
                    ),
                ),
                (
                    "primary_category",
                    models.CharField(
                        blank=True,
                        db_index=True,
                        help_text="مثلاً وبلاگ، دوره آموزشی",
                        max_length=80,
                        verbose_name="دسته اصلی",
                    ),
                ),
                (
                    "categories_summary",
                    models.CharField(
                        blank=True,
                        help_text="مثلاً وبلاگ (۲) · دوره (۱)",
                        max_length=300,
                        verbose_name="خلاصه دسته‌بندی",
                    ),
                ),
                (
                    "is_orphan",
                    models.BooleanField(
                        db_index=True,
                        default=True,
                        help_text="در هیچ محتوای فعالی استفاده نشده است.",
                        verbose_name="بدون استفاده",
                    ),
                ),
                ("indexed_at", models.DateTimeField(blank=True, null=True, verbose_name="آخرین ایندکس")),
            ],
            options={
                "verbose_name": "فایل CKEditor",
                "verbose_name_plural": "فایل‌های CKEditor",
                "db_table": "core_ckeditor_asset",
                "ordering": ["-uploaded_at", "-id"],
            },
        ),
    ]
