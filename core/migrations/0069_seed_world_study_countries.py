# Seed lightweight StudyCountry pages for world destinations (GSC 404 fix)

from __future__ import annotations

from django.db import migrations


def seed_world_study_countries(apps, schema_editor):
    StudyCountry = apps.get_model("core", "StudyCountry")
    from core.seed_data.world_country_catalog import build_world_study_country_catalog

    for item in build_world_study_country_catalog():
        code = item["code"]
        defaults = {k: v for k, v in item.items() if k != "code"}
        StudyCountry.objects.update_or_create(code=code, defaults=defaults)


def unseed_world_study_countries(apps, schema_editor):
    StudyCountry = apps.get_model("core", "StudyCountry")
    from core.seed_data.world_country_catalog import WORLD_STUDY_COUNTRY_CODES_LIST

    StudyCountry.objects.filter(code__in=WORLD_STUDY_COUNTRY_CODES_LIST).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0068_alter_consultationrequest_country_and_more"),
    ]

    operations = [
        migrations.RunPython(seed_world_study_countries, unseed_world_study_countries),
    ]
