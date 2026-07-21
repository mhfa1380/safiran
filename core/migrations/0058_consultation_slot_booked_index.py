# ایندکس برای شمارش سریع اسلات‌های رزرو‌شده در آمار عمومی

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0057_update_default_blog_author"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="consultationslot",
            index=models.Index(fields=["is_booked"], name="slot_is_booked_idx"),
        ),
    ]
