# Seed sample consultation slots for the next 14 days

from datetime import date, timedelta

from django.db import migrations


def seed_slots(apps, schema_editor):
    ConsultationSlot = apps.get_model("core", "ConsultationSlot")
    slots = [
        "۰۹:۰۰ - ۰۹:۳۰",
        "۰۹:۳۰ - ۱۰:۰۰",
        "۱۰:۰۰ - ۱۰:۳۰",
        "۱۰:۳۰ - ۱۱:۰۰",
        "۱۱:۰۰ - ۱۱:۳۰",
        "۱۴:۰۰ - ۱۴:۳۰",
        "۱۴:۳۰ - ۱۵:۰۰",
        "۱۵:۰۰ - ۱۵:۳۰",
    ]
    start = date.today()
    for day_offset in range(14):
        d = start + timedelta(days=day_offset)
        if d.weekday() < 5:  # شنبه تا چهارشنبه
            for i, tl in enumerate(slots):
                ConsultationSlot.objects.create(date=d, time_label=tl, order=i)


def reverse_seed(apps, schema_editor):
    ConsultationSlot = apps.get_model("core", "ConsultationSlot")
    ConsultationSlot.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0015_add_consultation_slot"),
    ]

    operations = [
        migrations.RunPython(seed_slots, reverse_seed),
    ]
