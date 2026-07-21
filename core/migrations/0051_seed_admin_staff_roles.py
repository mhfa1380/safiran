from django.db import migrations


def seed_roles(apps, schema_editor):
    from core.admin_roles import seed_admin_staff_roles

    seed_admin_staff_roles()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0050_blogpost_author"),
    ]

    operations = [
        migrations.RunPython(seed_roles, migrations.RunPython.noop),
    ]
