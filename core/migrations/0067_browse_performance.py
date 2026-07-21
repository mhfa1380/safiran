# Generated manually for browse performance

from django.db import migrations, models


def backfill_world_rank_num(apps, schema_editor):
    University = apps.get_model("core", "University")
    batch = []
    for uni in University.objects.only("id", "world_rank", "world_rank_num").iterator(chunk_size=500):
        raw = str(uni.world_rank or "").strip()
        rank_num = 9999
        if raw:
            try:
                rank_num = min(max(int(raw.split("-")[0].strip()), 1), 9999)
            except (TypeError, ValueError):
                rank_num = 9999
        if uni.world_rank_num != rank_num:
            uni.world_rank_num = rank_num
            batch.append(uni)
        if len(batch) >= 500:
            University.objects.bulk_update(batch, ["world_rank_num"])
            batch = []
    if batch:
        University.objects.bulk_update(batch, ["world_rank_num"])


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0066_referral_source_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="university",
            name="world_rank_num",
            field=models.PositiveSmallIntegerField(
                db_index=True,
                default=9999,
                help_text="برای مرتب‌سازی سریع لیست؛ از world_rank پر می‌شود.",
                verbose_name="رتبه عددی (مرتب‌سازی)",
            ),
        ),
        migrations.AddIndex(
            model_name="major",
            index=models.Index(fields=["is_active", "country", "order", "id"], name="major_browse_idx"),
        ),
        migrations.AddIndex(
            model_name="university",
            index=models.Index(
                fields=["country", "world_rank_num", "name_fa"],
                name="uni_browse_rank_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="university",
            index=models.Index(
                fields=["country", "type", "world_rank_num"],
                name="uni_browse_type_idx",
            ),
        ),
        migrations.RunPython(backfill_world_rank_num, migrations.RunPython.noop),
    ]
