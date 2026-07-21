# Merge migration branches

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0041_contract_services_faq"),
        ("core", "0042_evaluation_call_center"),
    ]

    operations = []
