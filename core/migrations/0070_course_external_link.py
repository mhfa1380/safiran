from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0069_seed_world_study_countries"),
    ]

    operations = [
        migrations.AddField(
            model_name="course",
            name="external_url",
            field=models.URLField(
                blank=True,
                help_text="اختیاری — اگر پر شود کلیک روی دوره به این آدرس می‌رود و صفحه جزئیات داخلی نمایش داده نمی‌شود.",
                max_length=500,
                verbose_name="لینک خارجی دوره",
            ),
        ),
        migrations.AddField(
            model_name="course",
            name="external_link_label",
            field=models.CharField(
                blank=True,
                help_text="متن دکمه اصلی — پیش‌فرض: «مشاهده دوره»",
                max_length=80,
                verbose_name="برچسب دکمه لینک خارجی",
            ),
        ),
    ]
