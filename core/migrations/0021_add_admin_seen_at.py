# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0020_add_team_member"),
    ]

    operations = [
        migrations.AddField(
            model_name="consultationrequest",
            name="admin_seen_at",
            field=models.DateTimeField(
                blank=True,
                help_text="زمانی که ادمین لیست را مشاهده کرده (برای badge پیام جدید)",
                null=True,
                verbose_name="مشاهده توسط ادمین",
            ),
        ),
        migrations.AddField(
            model_name="consultationslot",
            name="admin_seen_at",
            field=models.DateTimeField(
                blank=True,
                help_text="برای badge تایم‌های رزرو شده جدید",
                null=True,
                verbose_name="مشاهده توسط ادمین",
            ),
        ),
        migrations.AddField(
            model_name="evaluationrequest",
            name="admin_seen_at",
            field=models.DateTimeField(
                blank=True,
                help_text="برای badge درخواست‌های جدید",
                null=True,
                verbose_name="مشاهده توسط ادمین",
            ),
        ),
        migrations.AddField(
            model_name="contactmessage",
            name="admin_seen_at",
            field=models.DateTimeField(
                blank=True,
                help_text="برای badge پیام‌های جدید",
                null=True,
                verbose_name="مشاهده توسط ادمین",
            ),
        ),
    ]
