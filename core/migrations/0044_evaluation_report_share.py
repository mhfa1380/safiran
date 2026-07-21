# Generated manually

import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0043_merge_contract_and_evaluation"),
    ]

    operations = [
        migrations.CreateModel(
            name="EvaluationReportShare",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("token", models.UUIDField(db_index=True, editable=False, unique=True, verbose_name="توکن")),
                ("report", models.JSONField(verbose_name="گزارش پیشنهاد")),
                ("view_count", models.PositiveIntegerField(default=0, verbose_name="تعداد بازدید")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")),
                ("expires_at", models.DateTimeField(db_index=True, verbose_name="انقضا")),
                (
                    "evaluation",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="report_shares",
                        to="core.evaluationrequest",
                        verbose_name="درخواست ارزیابی",
                    ),
                ),
            ],
            options={
                "verbose_name": "لینک نتیجه ارزیابی",
                "verbose_name_plural": "لینک‌های نتیجه ارزیابی",
                "db_table": "core_evaluation_report_share",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="evaluationreportshare",
            index=models.Index(fields=["expires_at"], name="eval_share_expires_idx"),
        ),
    ]
