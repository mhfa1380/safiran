"""داده تعرفه به تفکیک کشورهای فعال موسسه (کانادا، اسپانیا، چین)."""

from __future__ import annotations

from typing import Any

from .models import LivingAllowanceCountry, PricingTariff, StudyCountry
from .pricing_calculator import _tariff_line
from .pricing_rates import format_foreign

# نگاشت پیش‌فرض کشور مقصد → ردیف مقرری (در صورت خالی بودن FK در ادمین)
DEFAULT_ALLOWANCE_SLUG = {
    "canada": "canada-group-a",
    "china": "china",
    "spain": "spain",
}


def _resolve_allowance_country(
    study: StudyCountry,
    allowance_by_slug: dict[str, LivingAllowanceCountry],
) -> LivingAllowanceCountry | None:
    if study.allowance_country_id and study.allowance_country:
        return study.allowance_country
    slug = DEFAULT_ALLOWANCE_SLUG.get(study.code)
    if slug:
        return allowance_by_slug.get(slug)
    return allowance_by_slug.get(study.code)


def _consultation_line(
    study: StudyCountry,
    tariff: PricingTariff | None,
    allowance: LivingAllowanceCountry | None,
) -> dict[str, Any]:
    amount = study.consultation_foreign_amount or 0
    currency = (study.consultation_foreign_currency or "").strip()
    if amount and currency:
        display = format_foreign(amount, currency)
        return {
            "key": "consultation",
            "title": tariff.title if tariff else "مشاوره تخصصی (هر جلسه)",
            "price_amount": amount,
            "price_currency": currency,
            "price_display": display,
            "price_type": tariff.price_type if tariff else PricingTariff.PRICE_FIXED,
            "allowance_percent": None,
            "selected": True,
            "reason": "",
            "icon": tariff.icon if tariff else "ti-headphone-alt",
        }
    if tariff:
        return _tariff_line(tariff, country=allowance, reason="")
    return {
        "key": "consultation",
        "title": "مشاوره تخصصی (هر جلسه)",
        "price_display": "بر اساس کشور مقصد",
        "price_amount": 0,
        "price_currency": "",
        "price_type": PricingTariff.PRICE_CONTACT,
        "allowance_percent": None,
        "selected": True,
        "reason": "",
        "icon": "ti-headphone-alt",
    }


def build_study_countries_pricing(
    *,
    study_countries: list[StudyCountry] | None = None,
    tariffs: list[PricingTariff] | None = None,
    allowance_countries: list[LivingAllowanceCountry] | None = None,
) -> dict[str, Any]:
    """ساخت JSON صفحه تعرفه: فقط کشورهای فعال StudyCountry."""
    if study_countries is None:
        study_countries = list(
            StudyCountry.objects.filter(is_active=True)
            .select_related("allowance_country")
            .order_by("order", "id")
        )
    if tariffs is None:
        tariffs = list(PricingTariff.objects.filter(is_active=True).select_related("category"))
    if allowance_countries is None:
        allowance_countries = list(LivingAllowanceCountry.objects.filter(is_active=True))

    allowance_by_slug = {c.slug: c for c in allowance_countries}
    tariffs_by_key = {t.calculator_key: t for t in tariffs}
    consultation_tariff = tariffs_by_key.get("consultation")

    countries_payload: list[dict[str, Any]] = []
    compare_rows: list[dict[str, Any]] = []

    for study in study_countries:
        allowance = _resolve_allowance_country(study, allowance_by_slug)
        tariff_lines: dict[str, dict[str, Any]] = {}

        for t in tariffs:
            if t.calculator_key == "consultation":
                line = _consultation_line(study, consultation_tariff, allowance)
            else:
                line = _tariff_line(t, country=allowance, reason="")
            tariff_lines[t.calculator_key] = {
                "title": line["title"],
                "price_display": line["price_display"],
                "price_amount": line.get("price_amount") or 0,
                "price_currency": line.get("price_currency") or "",
                "allowance_percent": line.get("allowance_percent"),
            }

        consult = tariff_lines.get("consultation", {})
        allowance_slug = allowance.slug if allowance else ""

        entry = {
            "code": study.code,
            "name": study.name,
            "flag": study.get_flag_static(),
            "allowance_slug": allowance_slug,
            "allowance_name": allowance.name if allowance else study.name,
            "allowance_display": allowance.allowance_display if allowance else "",
            "consultation_display": consult.get("price_display", ""),
            "consultation_amount": consult.get("price_amount") or 0,
            "consultation_currency": consult.get("price_currency") or "",
            "tariffs": tariff_lines,
        }
        countries_payload.append(entry)
        consult_display = consult.get("price_display") or ""
        if consult_display == "بر اساس کشور مقصد":
            consult_display = "استعلام از موسسه"
        compare_rows.append(
            {
                "code": study.code,
                "name": study.name,
                "consultation_display": consult_display or "—",
            }
        )

    default_code = countries_payload[0]["code"] if countries_payload else ""

    return {
        "countries": countries_payload,
        "default_code": default_code,
        "compare_rows": compare_rows,
    }
