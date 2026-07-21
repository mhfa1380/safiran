# تعرفه قراردادی — درصد مقرری و به‌روزرسانی خدمات

from django.db import migrations, models


def update_contract_tariffs(apps, schema_editor):
    PricingCategory = apps.get_model("core", "PricingCategory")
    PricingTariff = apps.get_model("core", "PricingTariff")

    PricingTariff.objects.all().update(is_active=False)

    categories = [
        ("contract-consult", "مشاوره", "مشاوره تخصصی مطابق ماده ۱-۱ و ۳-۱ قرارداد", "ti-headphone-alt", 1),
        ("contract-admission", "اخذ پذیرش", "پذیرش از دانشگاه‌های مورد تأیید وزارت علوم", "ti-book", 2),
        ("contract-visa", "روادید تحصیلی", "اخذ روادید تحصیلی — ماده ۱-۳", "ti-id-badge", 3),
        ("contract-registration", "ثبتنام", "ثبتنام نهایی در دانشگاه — ماده ۱-۴", "ti-pencil", 4),
        ("contract-relocation", "اقامت و استقرار", "انتقال، اسکان و راهنمایی — ماده ۱-۵", "ti-home", 5),
    ]
    cat_map = {}
    for slug, name, desc, icon, order in categories:
        cat, _ = PricingCategory.objects.update_or_create(
            slug=slug,
            defaults={"name": name, "description": desc, "icon": icon, "order": order, "is_active": True},
        )
        cat_map[slug] = cat

    tariffs = [
        (
            "consultation-session",
            "مشاوره تخصصی (هر جلسه)",
            "consultation",
            "contract-consult",
            "ارائه مشاوره و اطلاعات جامع درباره کشور، دانشگاه، رشته، هزینه‌ها و روادید.",
            "طبق ماده ۳-۱ قرارداد: ۵۰٬۰۰۰ تومان (۵۰۰٬۰۰۰ ریال) برای هر جلسه مشاوره. "
            "شامل بررسی شرایط ادامه تحصیل، انتخاب مسیر و پاسخ به سوالات متعارف.",
            50_000,
            0,
            "fixed",
            "ti-headphone-alt",
            True,
            False,
            "study,language,visa_only,docs_only",
            "",
            1,
        ),
        (
            "admission-service",
            "اخذ پذیرش دانشگاه",
            "admission",
            "contract-admission",
            "اخذ پذیرش از دانشگاه‌های مورد تأیید وزارت علوم برای کشور و مقطع درخواستی.",
            "حداکثر ۴۰٪ از یک‌ماه مقرری دانشجوی بورسیه مجرد در کشور مقصد، "
            "با احتساب معادل ریالی به نرخ روز (ماده ۳-۲ قرارداد).",
            0,
            40,
            "from",
            "ti-medall",
            True,
            True,
            "study,language",
            "",
            2,
        ),
        (
            "visa-service",
            "اخذ روادید تحصیلی",
            "visa",
            "contract-visa",
            "تکمیل پرونده، هماهنگی سفارت و پیگیری تا صدور ویزا.",
            "حداکثر ۲۰٪ از یک‌ماه مقرری بورسیه مجرد در کشور مقصد، "
            "معادل ریالی به نرخ روز (ماده ۳-۳ قرارداد).",
            0,
            20,
            "from",
            "ti-id-badge",
            True,
            True,
            "study,language,visa_only",
            "",
            3,
        ),
        (
            "registration-service",
            "ثبتنام در دانشگاه",
            "registration",
            "contract-registration",
            "ثبتنام نهایی و ارائه اطلاعات مورد نیاز دانشگاه.",
            "حداکثر ۲۰٪ از یک‌ماه مقرری (ماده ۳-۴ قرارداد).",
            0,
            20,
            "from",
            "ti-pencil-alt",
            True,
            True,
            "study,language",
            "admission",
            4,
        ),
        (
            "relocation-service",
            "انتقال، اسکان و جانمایی",
            "relocation",
            "contract-relocation",
            "جابجایی، اقامت و اسکان مناسب و راهنمایی در کشور مقصد.",
            "۲۰٪ از یک‌ماه مقرری بورسیه مجرد با معادل ریالی به نرخ روز (ماده ۳-۵ قرارداد).",
            0,
            20,
            "from",
            "ti-home",
            True,
            True,
            "study",
            "visa",
            5,
        ),
        (
            "contract-full-package",
            "پکیج کامل قراردادی",
            "contract_full",
            "contract-admission",
            "مجموع خدمات مشاوره، پذیرش، ویزا، ثبتنام و استقرار برای شروع مسیر.",
            "شامل تمام بندهای اصلی قرارداد برای متقاضی تازه‌کار. "
            "مبالغ هر بند جداگانه بر اساس مقرری کشور مقصد محاسبه می‌شود.",
            0,
            0,
            "from",
            "ti-package",
            True,
            False,
            "study",
            "",
            6,
        ),
        (
            "scholarship-success-fee",
            "حق‌الزحمه اخذ بورس تحصیلی",
            "scholarship_fee",
            "contract-admission",
            "در صورت موفقیت در اخذ بورس کامل یا نیمه دوره.",
            "طبق بند ۳-۷: در صورت بورس کامل، معادل ۷۰٪ یک‌ماه مقرری + ۱۰٪ شهریه ترم/سال اول؛ "
            "در صورت نیمه دوره، ۵۰٪ مقرری + ۱۰٪ شهریه. مبلغ شهریه با اسناد مثبته تعیین می‌شود.",
            0,
            0,
            "contact",
            "ti-star",
            False,
            False,
            "",
            "",
            7,
        ),
    ]

    for row in tariffs:
        (
            slug,
            title,
            key,
            cat_slug,
            short,
            desc,
            price_toman,
            allowance_percent,
            ptype,
            icon,
            calc_opt,
            is_core,
            goals,
            deps,
            order,
        ) = row
        PricingTariff.objects.update_or_create(
            calculator_key=key,
            defaults={
                "category": cat_map[cat_slug],
                "slug": slug,
                "title": title,
                "short_description": short,
                "description": desc,
                "price_toman": price_toman,
                "allowance_percent": allowance_percent or None,
                "price_type": ptype,
                "icon": icon,
                "is_calculator_option": calc_opt,
                "is_core": is_core,
                "auto_for_goals": goals,
                "depends_on_keys": deps,
                "order": order,
                "is_active": True,
            },
        )


def reverse_tariffs(apps, schema_editor):
    apps.get_model("core", "PricingTariff").objects.filter(
        calculator_key__in=[
            "consultation",
            "admission",
            "visa",
            "registration",
            "relocation",
            "contract_full",
            "scholarship_fee",
        ]
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0041_service_categories_check"),
    ]

    operations = [
        migrations.AddField(
            model_name="pricingtariff",
            name="allowance_percent",
            field=models.PositiveSmallIntegerField(
                blank=True,
                help_text="طبق قرارداد: حداکثر درصدی از یک‌ماه مقرری بورس دانشجوی مجرد در کشور مقصد",
                null=True,
                verbose_name="درصد مقرری ماهانه",
            ),
        ),
        migrations.RunPython(update_contract_tariffs, reverse_tariffs),
    ]
