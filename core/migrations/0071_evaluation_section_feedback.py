# Generated manually — بازخورد بخش‌های گزارش ارزیابی

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0070_course_external_link"),
    ]

    operations = [
        migrations.CreateModel(
            name="EvaluationSectionFeedback",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("section", models.CharField(db_index=True, max_length=32, verbose_name="بخش")),
                (
                    "item_key",
                    models.CharField(
                        blank=True,
                        default="",
                        help_text="مثلاً country:ca یا major:computer-science",
                        max_length=120,
                        verbose_name="کلید آیتم",
                    ),
                ),
                ("vote", models.SmallIntegerField(verbose_name="رأی")),
                ("weight", models.FloatField(default=1.0, verbose_name="وزن یادگیری")),
                (
                    "context",
                    models.JSONField(blank=True, default=dict, verbose_name="زمینه پیشنهاد"),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="ثبت")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="به‌روزرسانی")),
                (
                    "evaluation",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="section_feedback",
                        to="core.evaluationrequest",
                        verbose_name="درخواست ارزیابی",
                    ),
                ),
                (
                    "share",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="section_feedback",
                        to="core.evaluationreportshare",
                        verbose_name="لینک گزارش",
                    ),
                ),
            ],
            options={
                "verbose_name": "بازخورد بخش ارزیابی",
                "verbose_name_plural": "بازخورد بخش‌های ارزیابی",
                "db_table": "core_evaluation_section_feedback",
                "ordering": ["-updated_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="evaluationsectionfeedback",
            constraint=models.UniqueConstraint(
                fields=("share", "section", "item_key"),
                name="eval_section_feedback_unique",
            ),
        ),
        migrations.AddIndex(
            model_name="evaluationsectionfeedback",
            index=models.Index(fields=["evaluation", "section"], name="eval_fb_eval_section_idx"),
        ),
        migrations.AddIndex(
            model_name="evaluationsectionfeedback",
            index=models.Index(fields=["-updated_at"], name="eval_fb_updated_idx"),
        ),
    ]
