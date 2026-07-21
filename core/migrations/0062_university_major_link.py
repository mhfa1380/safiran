# Generated manually for university–major bidirectional links

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0061_populate_pricing_catalog"),
    ]

    operations = [
        migrations.CreateModel(
            name="UniversityMajorLink",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "is_featured",
                    models.BooleanField(
                        default=False,
                        help_text="در ابتدای لیست رشته‌های دانشگاه یا دانشگاه‌های رشته نمایش داده می‌شود.",
                        verbose_name="شاخص در لیست",
                    ),
                ),
                ("order", models.PositiveSmallIntegerField(default=0, verbose_name="ترتیب")),
                (
                    "major",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="university_links",
                        to="core.major",
                        verbose_name="رشته",
                    ),
                ),
                (
                    "university",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="major_links",
                        to="core.university",
                        verbose_name="دانشگاه",
                    ),
                ),
            ],
            options={
                "verbose_name": "رشته در دانشگاه",
                "verbose_name_plural": "رشته‌های دانشگاه",
                "db_table": "core_university_major_link",
                "ordering": ["order", "id"],
            },
        ),
        migrations.AddConstraint(
            model_name="universitymajorlink",
            constraint=models.UniqueConstraint(
                fields=("university", "major"),
                name="core_university_major_link_unique",
            ),
        ),
        migrations.AddIndex(
            model_name="universitymajorlink",
            index=models.Index(fields=["university", "order"], name="uni_major_uni_ord_idx"),
        ),
        migrations.AddIndex(
            model_name="universitymajorlink",
            index=models.Index(fields=["major", "order"], name="uni_major_maj_ord_idx"),
        ),
        migrations.AddIndex(
            model_name="universitymajorlink",
            index=models.Index(fields=["university", "is_featured"], name="uni_major_uni_feat_idx"),
        ),
        migrations.AddIndex(
            model_name="universitymajorlink",
            index=models.Index(fields=["major", "is_featured"], name="uni_major_maj_feat_idx"),
        ),
    ]
