# Generated manually

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0022_add_service_short_description"),
    ]

    operations = [
        migrations.AddField(
            model_name="course",
            name="description",
            field=models.TextField(blank=True, verbose_name="توضیحات کامل دوره"),
        ),
        migrations.AddField(
            model_name="course",
            name="features",
            field=models.TextField(
                blank=True,
                help_text="هر خط یک ویژگی؛ مثلاً: پشتیبانی آنلاین، گواهینامه معتبر",
                verbose_name="ویژگی‌های دوره",
            ),
        ),
        migrations.AddField(
            model_name="course",
            name="duration_hours",
            field=models.PositiveIntegerField(blank=True, default=0, verbose_name="مدت دوره (ساعت)"),
        ),
        migrations.AddField(
            model_name="course",
            name="price",
            field=models.CharField(
                blank=True,
                help_text="مثلاً: تماس بگیرید، رایگان، یا مبلغ",
                max_length=150,
                verbose_name="قیمت",
            ),
        ),
        migrations.AddField(
            model_name="course",
            name="delivery_mode",
            field=models.CharField(
                blank=True,
                choices=[
                    ("in_person", "حضوری"),
                    ("online", "آنلاین"),
                    ("both", "حضوری و آنلاین"),
                ],
                default="both",
                max_length=20,
                verbose_name="نحوه برگزاری",
            ),
        ),
        migrations.AddField(
            model_name="course",
            name="sample_video",
            field=models.URLField(blank=True, verbose_name="لینک ویدیو نمونه تدریس"),
        ),
        migrations.CreateModel(
            name="CourseSyllabus",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=250, verbose_name="عنوان سرفصل")),
                ("description", models.TextField(blank=True, verbose_name="توضیحات")),
                ("order", models.PositiveSmallIntegerField(default=0, verbose_name="ترتیب")),
                (
                    "course",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="syllabus_items",
                        to="core.course",
                        verbose_name="دوره",
                    ),
                ),
            ],
            options={
                "verbose_name": "سرفصل دوره",
                "verbose_name_plural": "سرفصل‌های دوره",
                "db_table": "core_course_syllabus",
                "ordering": ["order", "id"],
            },
        ),
    ]
