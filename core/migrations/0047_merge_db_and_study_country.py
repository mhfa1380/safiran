# Merge migration branches

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0046_db_indexes_and_maintenance"),
        ("core", "0046_study_country_pricing_fields"),
    ]

    operations = []
