# Generated manually for evaluation call-center fields

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("core", "0041_service_categories_check"),
    ]

    operations = [
        migrations.AddField(
            model_name="evaluationrequest",
            name="status",
            field=models.CharField(
                choices=[
                    ("new", "جدید — تماس نگرفته"),
                    ("contacted", "تماس گرفته شده"),
                    ("follow_up", "نیاز به پیگیری"),
                    ("in_progress", "در حال پیگیری"),
                    ("completed", "تکمیل / قرارداد"),
                    ("lost", "منصرف / بسته شده"),
                ],
                db_index=True,
                default="new",
                max_length=20,
                verbose_name="وضعیت پیگیری",
            ),
        ),
        migrations.AddField(
            model_name="evaluationrequest",
            name="priority",
            field=models.CharField(
                choices=[
                    ("low", "کم"),
                    ("normal", "معمولی"),
                    ("high", "بالا"),
                    ("urgent", "فوری"),
                ],
                db_index=True,
                default="normal",
                max_length=10,
                verbose_name="اولویت",
            ),
        ),
        migrations.AddField(
            model_name="evaluationrequest",
            name="follow_up_required",
            field=models.BooleanField(
                db_index=True,
                default=True,
                help_text="اگر فعال باشد در فیلتر «منتظر پیگیری» نمایش داده می‌شود.",
                verbose_name="نیاز به پیگیری",
            ),
        ),
        migrations.AddField(
            model_name="evaluationrequest",
            name="follow_up_category",
            field=models.CharField(
                blank=True,
                choices=[
                    ("general", "عمومی"),
                    ("documents", "مدارک و پرونده"),
                    ("language", "آزمون زبان"),
                    ("financial", "تمکن مالی / هزینه"),
                    ("university", "انتخاب دانشگاه / رشته"),
                    ("visa", "ویزا و اقامت"),
                    ("contract", "قرارداد و پرداخت"),
                    ("other", "سایر"),
                ],
                max_length=20,
                verbose_name="دسته پیگیری",
            ),
        ),
        migrations.AddField(
            model_name="evaluationrequest",
            name="contact_result",
            field=models.CharField(
                choices=[
                    ("not_yet", "هنوز تماس گرفته نشده"),
                    ("answered", "پاسخ داد — علاقه‌مند"),
                    ("no_answer", "جواب نداد"),
                    ("busy", "مشغول — تماس مجدد"),
                    ("callback", "درخواست تماس مجدد"),
                    ("whatsapp", "پیگیری از واتساپ/پیام"),
                    ("not_interested", "تمایلی ندارد"),
                    ("converted", "تبدیل به مشتری / قرارداد"),
                ],
                db_index=True,
                default="not_yet",
                max_length=20,
                verbose_name="نتیجه آخرین تماس",
            ),
        ),
        migrations.AddField(
            model_name="evaluationrequest",
            name="admin_notes",
            field=models.TextField(
                blank=True,
                help_text="خلاصه مکالمه، تعهدات و نکات پیگیری برای تیم کال‌سنتر.",
                verbose_name="یادداشت کارشناس (داخلی)",
            ),
        ),
        migrations.AddField(
            model_name="evaluationrequest",
            name="recommendation_snapshot",
            field=models.JSONField(
                blank=True,
                help_text="خروجی الگوریتم هنگام ثبت فرم؛ فقط خواندنی.",
                null=True,
                verbose_name="پیشنهاد هوشمند (ذخیره خودکار)",
            ),
        ),
        migrations.AddField(
            model_name="evaluationrequest",
            name="contacted_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="زمان آخرین تماس"),
        ),
        migrations.AddField(
            model_name="evaluationrequest",
            name="next_follow_up_at",
            field=models.DateTimeField(
                blank=True,
                db_index=True,
                null=True,
                verbose_name="زمان پیگیری بعدی",
            ),
        ),
        migrations.AddField(
            model_name="evaluationrequest",
            name="assigned_to",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="assigned_evaluations",
                to=settings.AUTH_USER_MODEL,
                verbose_name="کارشناس مسئول",
            ),
        ),
        migrations.AddField(
            model_name="evaluationrequest",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, verbose_name="آخرین به‌روزرسانی"),
        ),
        migrations.CreateModel(
            name="EvaluationContactLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "contact_result",
                    models.CharField(
                        choices=[
                            ("not_yet", "هنوز تماس گرفته نشده"),
                            ("answered", "پاسخ داد — علاقه‌مند"),
                            ("no_answer", "جواب نداد"),
                            ("busy", "مشغول — تماس مجدد"),
                            ("callback", "درخواست تماس مجدد"),
                            ("whatsapp", "پیگیری از واتساپ/پیام"),
                            ("not_interested", "تمایلی ندارد"),
                            ("converted", "تبدیل به مشتری / قرارداد"),
                        ],
                        max_length=20,
                        verbose_name="نتیجه تماس",
                    ),
                ),
                ("notes", models.TextField(blank=True, verbose_name="خلاصه مکالمه")),
                ("follow_up_required", models.BooleanField(default=False, verbose_name="نیاز به پیگیری مجدد")),
                (
                    "follow_up_category",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("general", "عمومی"),
                            ("documents", "مدارک و پرونده"),
                            ("language", "آزمون زبان"),
                            ("financial", "تمکن مالی / هزینه"),
                            ("university", "انتخاب دانشگاه / رشته"),
                            ("visa", "ویزا و اقامت"),
                            ("contract", "قرارداد و پرداخت"),
                            ("other", "سایر"),
                        ],
                        max_length=20,
                        verbose_name="دسته پیگیری",
                    ),
                ),
                (
                    "next_follow_up_at",
                    models.DateTimeField(blank=True, null=True, verbose_name="پیگیری بعدی"),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ثبت")),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="evaluation_contact_logs",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="ثبت‌کننده",
                    ),
                ),
                (
                    "evaluation",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="contact_logs",
                        to="core.evaluationrequest",
                        verbose_name="درخواست ارزیابی",
                    ),
                ),
            ],
            options={
                "verbose_name": "لاگ تماس ارزیابی",
                "verbose_name_plural": "لاگ‌های تماس ارزیابی",
                "db_table": "core_evaluation_contact_log",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="evaluationrequest",
            index=models.Index(fields=["status", "follow_up_required"], name="eval_status_follow_idx"),
        ),
        migrations.AddIndex(
            model_name="evaluationrequest",
            index=models.Index(fields=["next_follow_up_at"], name="eval_next_followup_idx"),
        ),
        migrations.AddIndex(
            model_name="evaluationrequest",
            index=models.Index(fields=["priority", "created_at"], name="eval_priority_created_idx"),
        ),
    ]
