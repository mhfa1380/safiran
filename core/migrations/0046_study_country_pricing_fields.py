# تعرفه مشاوره و مقرری به تفکیک کشورهای فعال موسسه

from django.db import migrations, models
import django.db.models.deletion


def link_study_countries_allowance(apps, schema_editor):
    StudyCountry = apps.get_model("core", "StudyCountry")
    LivingAllowanceCountry = apps.get_model("core", "LivingAllowanceCountry")
    slug_map = {
        "canada": "canada-group-a",
        "china": "china",
        "spain": "spain",
    }
    for code, slug in slug_map.items():
        study = StudyCountry.objects.filter(code=code).first()
        allowance = LivingAllowanceCountry.objects.filter(slug=slug).first()
        if study and allowance:
            study.allowance_country_id = allowance.id
            study.save(update_fields=["allowance_country_id"])


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0045_pricing_foreign_currency"),
    ]

    operations = [
        migrations.AddField(
            model_name="studycountry",
            name="allowance_country",
            field=models.ForeignKey(
                blank=True,
                help_text="برای محاسبه درصد پذیرش، ویزا و … در صفحه تعرفه.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="study_countries",
                to="core.livingallowancecountry",
                verbose_name="ردیف مقرری (محاسبه تعرفه)",
            ),
        ),
        migrations.AddField(
            model_name="studycountry",
            name="consultation_foreign_amount",
            field=models.PositiveIntegerField(
                default=0,
                help_text="مطابق ماده ۳-۱ قرارداد؛ مبلغ ثابت به ارز زیر.",
                verbose_name="مبلغ هر جلسه مشاوره (ارز)",
            ),
        ),
        migrations.AddField(
            model_name="studycountry",
            name="consultation_foreign_currency",
            field=models.CharField(
                blank=True,
                choices=[
                    ("EUR", "یورو"),
                    ("USD", "دلار آمریکا"),
                    ("GBP", "پوند انگلیس"),
                    ("AUD", "دلار استرالیا"),
                    ("CAD", "دلار کانادا"),
                    ("CHF", "فرانک سوئیس"),
                    ("DKK", "کرون دانمارک"),
                    ("SEK", "کرون سوئد"),
                    ("NOK", "کرون نروژ"),
                    ("JPY", "ین ژاپن"),
                ],
                default="",
                max_length=10,
                verbose_name="ارز جلسه مشاوره",
            ),
        ),
        migrations.RunPython(link_study_countries_allowance, migrations.RunPython.noop),
    ]
