# ایندکس‌های پرکاربرد برای کاهش قفل و سرعت کوئری

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0045_pricing_foreign_currency"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="contactmessage",
            index=models.Index(fields=["created_at"], name="contact_created_idx"),
        ),
        migrations.AddIndex(
            model_name="contactmessage",
            index=models.Index(fields=["admin_seen_at"], name="contact_seen_idx"),
        ),
        migrations.AddIndex(
            model_name="contactmessage",
            index=models.Index(
                fields=["status", "created_at"], name="contact_status_cr_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="consultationrequest",
            index=models.Index(fields=["admin_seen_at"], name="consult_seen_idx"),
        ),
        migrations.AddIndex(
            model_name="consultationrequest",
            index=models.Index(
                fields=["status", "updated_at"], name="consult_status_upd_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="evaluationcontactlog",
            index=models.Index(
                fields=["evaluation", "created_at"], name="eval_log_ev_cr_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="evaluationcontactlog",
            index=models.Index(fields=["created_at"], name="eval_log_created_idx"),
        ),
    ]
