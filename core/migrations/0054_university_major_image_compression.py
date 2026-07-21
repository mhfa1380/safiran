# Generated manually — ImageField + organized upload paths

from django.db import migrations, models

import core.models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0053_country_scholarship_pages"),
    ]

    operations = [
        migrations.AlterField(
            model_name="major",
            name="image",
            field=models.ImageField(
                blank=True,
                help_text="تصویر شاخص رشته؛ خودکار تا ۴۰۰KB فشرده می‌شود.",
                null=True,
                upload_to=core.models.major_image_upload_to,
                verbose_name="تصویر رشته",
            ),
        ),
        migrations.AlterField(
            model_name="university",
            name="image",
            field=models.ImageField(
                blank=True,
                help_text="تصویر را آپلود کنید؛ به‌صورت خودکار تا حداکثر ۴۰۰KB فشرده و در پوشه کشور/دانشگاه ذخیره می‌شود.",
                null=True,
                upload_to=core.models.university_image_upload_to,
                verbose_name="تصویر دانشگاه",
            ),
        ),
        migrations.AlterField(
            model_name="universitygalleryimage",
            name="image",
            field=models.ImageField(
                upload_to=core.models.university_gallery_upload_to,
                verbose_name="تصویر",
            ),
        ),
    ]
