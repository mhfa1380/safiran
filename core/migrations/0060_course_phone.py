from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0059_course_instructor"),
    ]

    operations = [
        migrations.AddField(
            model_name="course",
            name="phone",
            field=models.CharField(
                blank=True,
                help_text="در صورت خالی بودن، شماره مدرس نمایش داده می‌شود.",
                max_length=20,
                verbose_name="شماره تماس دوره",
            ),
        ),
    ]
