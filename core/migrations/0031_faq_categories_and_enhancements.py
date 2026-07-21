# Generated for FAQ categories, SEO fields, and smart search support

from django.db import migrations, models
import django.db.models.deletion


def seed_faq_categories(apps, schema_editor):
    FAQ = apps.get_model("core", "FAQ")
    FAQCategory = apps.get_model("core", "FAQCategory")

    categories = [
        (1, "moshavere-shoro", "مشاوره و شروع مسیر", "ti-headphone-alt", "سوالات درباره مشاوره، ارزیابی و شروع فرایند مهاجرت تحصیلی."),
        (2, "paziresh-visa", "پذیرش، ویزا و مدارک", "ti-id-badge", "سوالات مربوط به پذیرش دانشگاه، ویزای تحصیلی و مدارک."),
        (3, "zanestegi-hazine", "زندگی، هزینه و بورسیه", "ti-wallet", "سوالات درباره هزینه تحصیل، بورسیه، کار و زندگی در کشور مقصد."),
    ]
    cat_by_slug = {}
    for order, slug, name, icon, desc in categories:
        cat, _ = FAQCategory.objects.get_or_create(
            slug=slug,
            defaults={
                "name": name,
                "icon": icon,
                "description": desc,
                "order": order,
                "is_active": True,
            },
        )
        cat_by_slug[slug] = cat

    assignment = {
        1: "moshavere-shoro",
        2: "paziresh-visa",
        3: "paziresh-visa",
        4: "paziresh-visa",
        5: "zanestegi-hazine",
        6: "zanestegi-hazine",
        7: "moshavere-shoro",
    }
    for faq in FAQ.objects.all():
        slug = assignment.get(faq.order, "moshavere-shoro")
        faq.category_id = cat_by_slug[slug].id
        if not faq.slug:
            from django.utils.text import slugify

            base = slugify(faq.question, allow_unicode=True)[:180] or f"faq-{faq.id}"
            unique = base
            n = 1
            while FAQ.objects.filter(slug=unique).exclude(pk=faq.pk).exists():
                unique = f"{base}-{n}"
                n += 1
            faq.slug = unique
        faq.save()

    FAQ.objects.filter(order__lte=3).update(is_featured=True)


def reverse_seed(apps, schema_editor):
    FAQ = apps.get_model("core", "FAQ")
    FAQ.objects.update(category_id=None)
    FAQCategory = apps.get_model("core", "FAQCategory")
    FAQCategory.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0030_alter_consultationrequest_consultation_type"),
    ]

    operations = [
        migrations.CreateModel(
            name="FAQCategory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120, verbose_name="نام دسته")),
                ("slug", models.SlugField(help_text="برای آدرس صفحه دسته، مثلاً visa یا moshavere", max_length=150, unique=True, verbose_name="شناسه آدرس")),
                ("description", models.TextField(blank=True, help_text="نمایش زیر عنوان دسته در صفحه FAQ", verbose_name="توضیح کوتاه")),
                ("icon", models.CharField(blank=True, help_text="کلاس آیکون Themify، مثلاً ti-help-alt", max_length=60, verbose_name="آیکون")),
                ("meta_title", models.CharField(blank=True, help_text="اگر خالی باشد از نام دسته استفاده می‌شود.", max_length=70, verbose_name="عنوان سئو")),
                ("meta_description", models.CharField(blank=True, max_length=160, verbose_name="توضیح متا (سئو)")),
                ("order", models.PositiveSmallIntegerField(default=0, verbose_name="ترتیب نمایش")),
                ("is_active", models.BooleanField(default=True, verbose_name="فعال")),
            ],
            options={
                "verbose_name": "دسته سوالات متداول",
                "verbose_name_plural": "دسته‌های سوالات متداول",
                "db_table": "core_faq_category",
                "ordering": ["order", "id"],
            },
        ),
        migrations.AddField(
            model_name="faq",
            name="slug",
            field=models.SlugField(blank=True, help_text="برای لینک مستقیم به سوال؛ در صورت خالی بودن خودکار ساخته می‌شود.", max_length=200),
        ),
        migrations.AddField(
            model_name="faq",
            name="search_keywords",
            field=models.TextField(blank=True, help_text="کلمات مرتبط با کاما جدا کنید تا در جستجو و پیشنهاد هوشمند بهتر دیده شود.", verbose_name="کلمات کلیدی جستجو"),
        ),
        migrations.AddField(
            model_name="faq",
            name="is_featured",
            field=models.BooleanField(default=False, help_text="در بخش «سوالات پرتکرار» نمایش داده می‌شود.", verbose_name="پیشنهاد ویژه"),
        ),
        migrations.AddField(
            model_name="faq",
            name="view_count",
            field=models.PositiveIntegerField(default=0, editable=False, verbose_name="تعداد بازدید"),
        ),
        migrations.AddField(
            model_name="faq",
            name="category",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="faqs", to="core.faqcategory", verbose_name="دسته"),
        ),
        migrations.RunPython(seed_faq_categories, reverse_seed),
        migrations.AlterField(
            model_name="faq",
            name="slug",
            field=models.SlugField(blank=True, help_text="برای لینک مستقیم به سوال؛ در صورت خالی بودن خودکار ساخته می‌شود.", max_length=200, unique=True),
        ),
    ]
