# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0021_add_admin_seen_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="service",
            name="short_description",
            field=models.TextField(
                blank=True,
                help_text="خلاصه برای نمایش در صفحه اصلی؛ در صورت خالی بودن از توضیحات کامل استفاده می‌شود.",
                verbose_name="توضیح کوتاه (صفحه اول)",
            ),
        ),
        migrations.AlterField(
            model_name="service",
            name="description",
            field=models.TextField(
                help_text="متن کامل برای صفحه خدمات موسسه.",
                verbose_name="توضیحات کامل (صفحه خدمات)",
            ),
        ),
    ]
