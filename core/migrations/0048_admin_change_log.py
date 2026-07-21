# لاگ تغییرات ادمین با امکان بازگردانی

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("contenttypes", "0002_remove_content_type_name"),
        ("core", "0047_merge_db_and_study_country"),
    ]

    operations = [
        migrations.CreateModel(
            name="AdminChangeLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("object_id", models.CharField(db_index=True, max_length=64, verbose_name="شناسه شیء")),
                ("object_repr", models.CharField(max_length=255, verbose_name="نمایش شیء")),
                (
                    "action",
                    models.CharField(
                        choices=[
                            ("create", "ایجاد"),
                            ("update", "ویرایش"),
                            ("delete", "حذف"),
                            ("revert", "بازگردانی"),
                        ],
                        max_length=20,
                        verbose_name="عملیات",
                    ),
                ),
                (
                    "payload",
                    models.JSONField(
                        default=dict,
                        help_text="before / after / changed_fields برای بازگردانی و نمایش diff",
                        verbose_name="داده",
                    ),
                ),
                ("note", models.CharField(blank=True, max_length=500, verbose_name="یادداشت")),
                ("reverted_at", models.DateTimeField(blank=True, null=True, verbose_name="زمان بازگردانی")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="زمان")),
                (
                    "content_type",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="contenttypes.contenttype",
                        verbose_name="نوع محتوا",
                    ),
                ),
                (
                    "reverted_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="admin_reverts_done",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="بازگردانی توسط",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="admin_change_logs",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="کاربر",
                    ),
                ),
            ],
            options={
                "verbose_name": "لاگ تغییر ادمین",
                "verbose_name_plural": "لاگ تغییرات ادمین",
                "db_table": "core_admin_change_log",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="adminchangelog",
            index=models.Index(fields=["content_type", "object_id"], name="adm_log_ct_obj_idx"),
        ),
        migrations.AddIndex(
            model_name="adminchangelog",
            index=models.Index(fields=["created_at"], name="adm_log_created_idx"),
        ),
        migrations.AddIndex(
            model_name="adminchangelog",
            index=models.Index(fields=["action", "created_at"], name="adm_log_act_cr_idx"),
        ),
    ]
