# Extended scholarship guides: Canada grad, China & Spain all degrees

from django.db import migrations


def seed(apps, schema_editor):
    from core.country_scholarship_seed import seed_all_extended

    seed_all_extended(apps)


def unseed(apps, schema_editor):
    from core.country_scholarship_seed import unseed_extended

    unseed_extended(apps)


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0053_country_scholarship_pages"),
        ("core", "0054_university_major_image_compression"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
