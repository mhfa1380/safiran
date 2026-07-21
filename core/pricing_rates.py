"""محاسبه تعرفه بر اساس مقرری مصوب — فقط ارز اصلی (بدون تبدیل تومان)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import LivingAllowanceCountry

CURRENCY_LABELS = {
    "EUR": "یورو",
    "USD": "دلار آمریکا",
    "GBP": "پوند انگلیس",
    "AUD": "دلار استرالیا",
    "CAD": "دلار کانادا",
    "CHF": "فرانک سوئیس",
    "DKK": "کرون دانمارک",
    "SEK": "کرون سوئد",
    "NOK": "کرون نروژ",
    "JPY": "ین ژاپن",
}


def currency_label(code: str) -> str:
    return CURRENCY_LABELS.get(code, code)


def format_foreign(amount: int, currency: str) -> str:
    label = currency_label(currency)
    return f"{amount:,} {label}".replace(",", "٬")


def compute_allowance_fee(
    country: LivingAllowanceCountry,
    percent: int,
) -> dict:
    """محاسبه سقف حق‌الزحمه بر اساس درصد یک‌ماه مقرری — فقط به ارز کشور."""
    foreign_amount = int(country.amount * percent / 100)
    currency = country.currency
    foreign_display = format_foreign(foreign_amount, currency)
    display = f"حداکثر {percent}٪ مقرری ({foreign_display})"
    return {
        "foreign_amount": foreign_amount,
        "foreign_display": foreign_display,
        "currency": currency,
        "display": display,
        "percent": percent,
    }


def sum_by_currency(items: list[dict]) -> dict[str, int]:
    """جمع مبالغ به تفکیک واحد پول."""
    totals: dict[str, int] = {}
    for item in items:
        currency = item.get("price_currency")
        amount = item.get("price_amount") or 0
        if currency and amount:
            totals[currency] = totals.get(currency, 0) + amount
    return totals


def format_totals(totals: dict[str, int], *, prefix: str = "") -> str:
    if not totals:
        return ""
    parts = [f"{prefix}{format_foreign(amt, cur)}" if prefix else format_foreign(amt, cur) for cur, amt in sorted(totals.items())]
    return " + ".join(parts)


def format_percent_of_total(total: int, percent: int, currency: str) -> str:
    if not total:
        return ""
    part = int(total * percent / 100)
    return format_foreign(part, currency)
