from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0031_faq_categories_and_enhancements"),
    ]

    operations = [
        migrations.AddField(
            model_name="faq",
            name="detail_content",
            field=models.TextField(
                blank=True,
                help_text="محتوای کامل برای صفحه اختصاصی سوال و سئو؛ اگر خالی باشد از پاسخ کوتاه استفاده می‌شود.",
                verbose_name="توضیحات کامل (صفحه جدا)",
            ),
        ),
        migrations.AddField(
            model_name="faq",
            name="meta_description",
            field=models.CharField(blank=True, max_length=160, verbose_name="توضیح متا (سئو)"),
        ),
        migrations.AddField(
            model_name="faq",
            name="meta_title",
            field=models.CharField(blank=True, max_length=70, verbose_name="عنوان سئو"),
        ),
        migrations.AlterField(
            model_name="faq",
            name="answer",
            field=models.TextField(
                help_text="نمایش در لیست و آکوردئون صفحه سوالات متداول.",
                verbose_name="پاسخ کوتاه",
            ),
        ),
    ]
