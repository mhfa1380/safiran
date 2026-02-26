# Generated manually

from django.db import migrations, models
from django.utils.text import slugify


def populate_major_slugs(apps, schema_editor):
    Major = apps.get_model("core", "Major")
    used = set()
    for m in Major.objects.all():
        if not m.slug:
            base = slugify(m.title, allow_unicode=False) or f"major-{m.id}"
            slug = base
            n = 1
            while slug in used:
                slug = f"{base}-{n}"
                n += 1
            used.add(slug)
            m.slug = slug
            m.save(update_fields=["slug"])


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0023_add_course_details_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="major",
            name="slug",
            field=models.SlugField(
                blank=True,
                help_text="برای آدرس صفحه؛ خالی = از عنوان ساخته می‌شود.",
                max_length=250,
                null=True,
                unique=True,
                verbose_name="شناسه آدرس",
            ),
        ),
        migrations.AddField(
            model_name="major",
            name="short_description",
            field=models.TextField(blank=True, verbose_name="خلاصه (لیست)"),
        ),
        migrations.AddField(
            model_name="major",
            name="image",
            field=models.URLField(blank=True, verbose_name="آدرس تصویر"),
        ),
        migrations.RunPython(populate_major_slugs, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="major",
            name="slug",
            field=models.SlugField(
                blank=True,
                help_text="برای آدرس صفحه؛ خالی = از عنوان ساخته می‌شود.",
                max_length=250,
                null=False,
                unique=True,
                verbose_name="شناسه آدرس",
            ),
        ),
    ]
