from django.db import migrations, models


def infer_member_groups(apps, schema_editor):
    TeamMember = apps.get_model("core", "TeamMember")
    for member in TeamMember.objects.all():
        combined = f"{member.position or ''} {member.title or ''}".lower()
        if any(k in combined for k in ("مدیر", "راهبر", "بنیان", "مدیرعامل", "هیئت")):
            group = "leadership"
        elif "ارشد" in combined:
            group = "senior_consultant"
        elif any(k in combined for k in ("پذیرش", "پرونده", "اپلای")):
            group = "admissions"
        elif any(k in combined for k in ("پشتیبان", "پشتیبانی", "منشی", "هماهنگ")):
            group = "support"
        elif "مشاور" in combined:
            group = "consultant"
        else:
            group = "consultant"
        member.member_group = group
        member.save(update_fields=["member_group"])


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0039_service_categories_and_enhancements"),
    ]

    operations = [
        migrations.AddField(
            model_name="teammember",
            name="member_group",
            field=models.CharField(
                choices=[
                    ("leadership", "مدیریت و راهبری"),
                    ("senior_consultant", "مشاوران ارشد"),
                    ("consultant", "مشاوران تحصیلی"),
                    ("admissions", "کارشناسان پذیرش و پرونده"),
                    ("support", "پشتیبانی و هماهنگی"),
                ],
                default="consultant",
                help_text="برای گروه‌بندی در صفحه درباره ما",
                max_length=30,
                verbose_name="گروه نمایش",
            ),
        ),
        migrations.AlterModelOptions(
            name="teammember",
            options={
                "ordering": ["member_group", "order", "id"],
                "verbose_name": "عضو تیم",
                "verbose_name_plural": "اعضای تیم",
            },
        ),
        migrations.RunPython(infer_member_groups, migrations.RunPython.noop),
    ]
