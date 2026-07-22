# Generated manually for panel AI cache fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("panel", "0003_panel_settings_assignment"),
    ]

    operations = [
        migrations.AddField(
            model_name="customercase",
            name="ai_payload",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text="خلاصه تحلیل + اسکریپت شخصی‌سازی‌شده",
                verbose_name="خروجی هوش مصنوعی",
            ),
        ),
        migrations.AddField(
            model_name="customercase",
            name="ai_context_hash",
            field=models.CharField(
                blank=True, default="", max_length=64, verbose_name="هش زمینه AI"
            ),
        ),
        migrations.AddField(
            model_name="customercase",
            name="ai_generated_at",
            field=models.DateTimeField(
                blank=True, null=True, verbose_name="زمان تولید AI"
            ),
        ),
    ]
