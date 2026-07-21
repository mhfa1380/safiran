# نمایش تعرفه به ارز اصلی — بدون تومان در سایت

from django.db import migrations, models


def strip_toman_text(apps, schema_editor):
    PricingTariff = apps.get_model("core", "PricingTariff")
    Service = apps.get_model("core", "Service")
    FAQ = apps.get_model("core", "FAQ")

    tariff_updates = {
        "consultation": {
            "short_description": "هر جلسه — مطابق ماده ۳-۱ قرارداد (مبلغ ثابت؛ استعلام از موسسه).",
            "description": (
                "ارائه مشاوره و اطلاعات جامع درباره کشور، دانشگاه، رشته، هزینه‌ها و روادید. "
                "حق‌الزحمه هر جلسه مطابق ماده ۳-۱ قرارداد استاندارد موسسات اعزام تعیین می‌شود "
                "(در سایت معادل ریالی/تومانی نمایش داده نمی‌شود)."
            ),
            "price_toman": 0,
        },
        "admission": {
            "description": (
                "حداکثر ۴۰٪ از یک‌ماه مقرری دانشجوی بورسیه مجرد در کشور مقصد، "
                "به همان ارز فهرست مقرری مصوب (ماده ۳-۲ قرارداد)."
            ),
        },
        "visa": {
            "description": (
                "حداکثر ۲۰٪ از یک‌ماه مقرری بورسیه مجرد در کشور مقصد، "
                "به ارز همان کشور (ماده ۳-۳ قرارداد)."
            ),
        },
        "registration": {
            "description": (
                "حداکثر ۲۰٪ یک‌ماه مقرری — به ارز کشور مقصد (ماده ۳-۴ قرارداد)."
            ),
        },
        "relocation": {
            "description": (
                "۲۰٪ یک‌ماه مقرری — به ارز کشور مقصد (ماده ۳-۵ قرارداد)."
            ),
        },
    }
    for key, fields in tariff_updates.items():
        PricingTariff.objects.filter(calculator_key=key).update(**fields)

    Service.objects.filter(slug="moshavere-gheyradi").update(
        short_description="هر جلسه — مطابق ماده ۳-۱ قرارداد.",
        description=(
            "مطابق ماده ۱-۱ و ۳-۱ قرارداد: مشاوره و اطلاعات جامع درباره کشور، دانشگاه، "
            "رشته و روادید. مبلغ هر جلسه طبق قرارداد موسسه است."
        ),
        highlights="مطابق ماده ۱-۱ قرارداد\nهر جلسه — طبق قرارداد\nحضوری یا آنلاین\nبدون تعهد برای ادامه",
    )
    Service.objects.filter(slug="akhz-paziresh").update(
        description=(
            "ماده ۱-۲: اخذ پذیرش از دانشگاه‌های مورد تأیید. حق‌الزحمه حداکثر ۴۰٪ "
            "یک‌ماه مقرری به ارز کشور مقصد (ماده ۳-۲)."
        ),
        highlights="دانشگاه‌های مورد تأیید\nحداکثر ۴۰٪ مقرری ماهانه\nارز کشور مقصد\nپیگیری تا Offer",
    )
    Service.objects.filter(slug="akhz-visa").update(
        description=(
            "ماده ۱-۳: اخذ روادید تحصیلی. حق‌الزحمه حداکثر ۲۰٪ یک‌ماه مقرری "
            "به ارز کشور مقصد (ماده ۳-۳)."
        ),
        highlights="ماده ۱-۳ قرارداد\nحداکثر ۲۰٪ مقرری\nارز کشور مقصد\nقوانین استرداد ۳-۸",
    )

    FAQ.objects.filter(slug="تعرفه-خدمات-چگونه-محاسبه-میشود").update(
        answer=(
            "تعرفه‌ها منطبق با فهرست مقرری دانشجویان بورسیه مصوب است. "
            "حق‌الزحمه پذیرش حداکثر ۴۰٪، ویزا و ثبتنام هر کدام حداکثر ۲۰٪ و استقرار ۲۰٪ "
            "از یک‌ماه مقرری کشور مقصد — به همان ارز جدول مقرری (یورو، دلار، پوند و …). "
            "مشاوره طبق ماده ۳-۱ قرارداد است."
        ),
    )
    FAQ.objects.filter(slug="mablaq-moshavere").update(
        answer="طبق ماده ۳-۱ قرارداد استاندارد موسسات اعزام؛ مبلغ هر جلسه را از موسسه استعلام کنید.",
    )


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0044_evaluation_report_share"),
    ]

    operations = [
        migrations.AddField(
            model_name="pricingtariff",
            name="price_foreign_amount",
            field=models.PositiveIntegerField(
                default=0,
                help_text="برای تعرفه ثابت مثل مشاوره؛ به ارز زیر",
                verbose_name="مبلغ ثابت (ارز)",
            ),
        ),
        migrations.AddField(
            model_name="pricingtariff",
            name="price_foreign_currency",
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
                verbose_name="ارز مبلغ ثابت",
            ),
        ),
        migrations.AlterField(
            model_name="pricingtariff",
            name="price_toman",
            field=models.PositiveIntegerField(
                default=0,
                help_text="فقط برای آرشیو؛ در سایت نمایش داده نمی‌شود.",
                verbose_name="قیمت (تومان) — داخلی",
            ),
        ),
        migrations.RunPython(strip_toman_text, migrations.RunPython.noop),
    ]
