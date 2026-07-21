from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0064_evaluation_processing_job"),
    ]

    operations = [
        migrations.AddField(
            model_name="major",
            name="meta_title",
            field=models.CharField(blank=True, max_length=200, verbose_name="عنوان SEO"),
        ),
        migrations.AddField(
            model_name="major",
            name="meta_description",
            field=models.CharField(blank=True, max_length=160, verbose_name="توضیح متا (سئو)"),
        ),
    ]
