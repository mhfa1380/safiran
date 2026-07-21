# Indexes for faster major list/search filters

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0055_seed_scholarship_guides_extended"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="major",
            index=models.Index(fields=["is_active", "country"], name="core_major_active_country_idx"),
        ),
        migrations.AddIndex(
            model_name="major",
            index=models.Index(fields=["is_active", "order"], name="core_major_active_order_idx"),
        ),
    ]
