# پر کردن تعرفه‌های خالی و قیمت‌گذاری ارزی (یورو / دلار کانادا)

from django.db import migrations


def populate_pricing(apps, schema_editor):
    from core.seed_data.pricing_catalog import (
        DEPRECATED_CATEGORY_SLUGS,
        PRICING_CATEGORIES,
        PRICING_TARIFFS,
        STUDY_COUNTRY_CONSULTATION,
    )

    PricingCategory = apps.get_model("core", "PricingCategory")
    PricingTariff = apps.get_model("core", "PricingTariff")
    StudyCountry = apps.get_model("core", "StudyCountry")

    PricingCategory.objects.filter(slug__in=DEPRECATED_CATEGORY_SLUGS).update(is_active=False)

    cat_map = {}
    for row in PRICING_CATEGORIES:
        cat, _ = PricingCategory.objects.update_or_create(
            slug=row["slug"],
            defaults={
                "name": row["name"],
                "description": row["description"],
                "icon": row["icon"],
                "order": row["order"],
                "is_active": True,
            },
        )
        cat_map[row["slug"]] = cat

    PricingTariff.objects.update(is_active=False)

    for row in PRICING_TARIFFS:
        (
            slug,
            title,
            key,
            cat_slug,
            short,
            desc,
            foreign_amount,
            currency,
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
                "price_toman": 0,
                "price_foreign_amount": foreign_amount or 0,
                "price_foreign_currency": currency or "",
                "allowance_percent": allowance_percent,
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

    for code, (amount, currency) in STUDY_COUNTRY_CONSULTATION.items():
        StudyCountry.objects.filter(code=code, is_active=True).update(
            consultation_foreign_amount=amount,
            consultation_foreign_currency=currency,
        )


def reverse_populate(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0060_course_phone"),
    ]

    operations = [
        migrations.RunPython(populate_pricing, reverse_populate),
    ]
