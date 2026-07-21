# Generated manually — صفحه اختصاصی و جستجوی دستاوردها

from django.db import migrations, models
from django.utils.text import slugify


def populate_achievement_slugs(apps, schema_editor):
    MonthlyAchievement = apps.get_model("core", "MonthlyAchievement")
    for obj in MonthlyAchievement.objects.all():
        if obj.slug:
            continue
        base = slugify(f"{obj.person_name}-{obj.title}", allow_unicode=True)[:180]
        if not base:
            base = f"achievement-{obj.pk}"
        slug = base
        n = 1
        while MonthlyAchievement.objects.filter(slug=slug).exclude(pk=obj.pk).exists():
            slug = f"{base}-{n}"
            n += 1
        obj.slug = slug
        if not (obj.detail_content or "").strip() and obj.description:
            obj.detail_content = f"<p>{obj.description}</p>"
        obj.save(update_fields=["slug", "detail_content"])


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0037_study_country"),
    ]

    operations = [
        migrations.AddField(
            model_name="monthlyachievement",
            name="slug",
            field=models.SlugField(
                blank=True,
                help_text="برای URL صفحه اختصاصی؛ خالی بماند تا خودکار ساخته شود.",
                max_length=200,
                null=True,
                unique=True,
                verbose_name="آدرس صفحه",
            ),
        ),
        migrations.AddField(
            model_name="monthlyachievement",
            name="detail_content",
            field=models.TextField(
                blank=True,
                help_text="توضیحات کامل داستان موفقیت؛ در صفحه اختصاصی نمایش داده می‌شود.",
                verbose_name="متن کامل صفحه",
            ),
        ),
        migrations.AddField(
            model_name="monthlyachievement",
            name="search_keywords",
            field=models.CharField(
                blank=True,
                help_text="کلمات جدا شده با ویرگول؛ مثلاً کانادا، ویزا، MBA، بورسیه",
                max_length=400,
                verbose_name="کلمات کلیدی جستجو",
            ),
        ),
        migrations.AddField(
            model_name="monthlyachievement",
            name="meta_title",
            field=models.CharField(blank=True, max_length=70, verbose_name="عنوان سئو"),
        ),
        migrations.AddField(
            model_name="monthlyachievement",
            name="meta_description",
            field=models.CharField(blank=True, max_length=160, verbose_name="توضیح سئو"),
        ),
        migrations.AddField(
            model_name="monthlyachievement",
            name="view_count",
            field=models.PositiveIntegerField(default=0, verbose_name="بازدید"),
        ),
        migrations.AlterField(
            model_name="monthlyachievement",
            name="description",
            field=models.TextField(verbose_name="خلاصه (لیست)"),
        ),
        migrations.RunPython(populate_achievement_slugs, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="monthlyachievement",
            name="slug",
            field=models.SlugField(
                allow_unicode=True,
                help_text="برای URL صفحه اختصاصی؛ خالی بماند تا خودکار ساخته شود.",
                max_length=200,
                unique=True,
                verbose_name="آدرس صفحه",
            ),
        ),
    ]
