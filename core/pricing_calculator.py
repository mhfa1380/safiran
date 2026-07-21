"""
ماشین‌حساب تعرفه — منطبق با قرارداد موسسه و فهرست مقرری مصوب (ارز اصلی، بدون تومان).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .models import LivingAllowanceCountry, PricingTariff, StudyCountry
from .pricing_rates import (
    compute_allowance_fee,
    format_foreign,
    format_percent_of_total,
    format_totals,
    sum_by_currency,
)

GOAL_STUDY = "study"
GOAL_LANGUAGE = "language"
GOAL_VISA_ONLY = "visa_only"
GOAL_DOCS_ONLY = "docs_only"
VALID_GOALS = {GOAL_STUDY, GOAL_LANGUAGE, GOAL_VISA_ONLY, GOAL_DOCS_ONLY}

SITUATION_STARTING = "starting"
SITUATION_HAS_ADMISSION = "has_admission"
SITUATION_IN_PROGRESS = "in_progress"
SITUATION_VISA_STAGE = "visa_stage"
VALID_SITUATIONS = {
    SITUATION_STARTING,
    SITUATION_HAS_ADMISSION,
    SITUATION_IN_PROGRESS,
    SITUATION_VISA_STAGE,
}

KEY_CONSULTATION = "consultation"
KEY_ADMISSION = "admission"
KEY_VISA = "visa"
KEY_REGISTRATION = "registration"
KEY_RELOCATION = "relocation"
PACKAGE_KEY = "contract_full"

CONTRACT_PAYMENT_NOTE = (
    "طبق قرارداد: ۴۰٪ حق‌الزحمه هنگام امضا و مابقی پس از انجام کامل تعهدات پرداخت می‌شود. "
    "مبالغ حق‌الزحمه مطابق ارز کشور مقصد در قرارداد درج شده است."
)
APPLICANT_COSTS_NOTE = (
    "هزینه ترجمه مدارک، ثبت‌نام دانشگاه، هزینه سفارت و بلیط بر عهده متقاضی است (ماده ۶ قرارداد)."
)
CURRENCY_NOTE = (
    "تمامی مبالغ بر اساس فهرست مقرری مصوب و ارز همان کشور (یورو، دلار، پوند و …) نمایش داده می‌شود؛ "
    "به‌دلیل نوسان نرخ ارز، معادل ریالی در سایت محاسبه نمی‌شود."
)


@dataclass
class CalculatorInput:
    goal: str
    situation: str
    country_slug: str = ""
    extra_keys: list[str] = field(default_factory=list)
    excluded_keys: list[str] = field(default_factory=list)


def _tariff_line(
    t: PricingTariff,
    *,
    country: LivingAllowanceCountry | None,
    reason: str = "",
) -> dict[str, Any]:
    price_amount = 0
    price_currency = ""
    price_display = t.price_display

    if t.allowance_percent and country:
        fee = compute_allowance_fee(country, t.allowance_percent)
        price_amount = fee["foreign_amount"]
        price_currency = fee["currency"]
        price_display = fee["display"]
    elif t.price_foreign_amount and t.price_foreign_currency:
        price_amount = t.price_foreign_amount
        price_currency = t.price_foreign_currency
        price_display = format_foreign(price_amount, price_currency)
    elif t.price_type == PricingTariff.PRICE_CONTACT:
        price_display = "تماس بگیرید"

    return {
        "key": t.calculator_key,
        "title": t.title,
        "short": t.short_description,
        "price_amount": price_amount,
        "price_currency": price_currency,
        "price_display": price_display,
        "price_type": t.price_type,
        "allowance_percent": t.allowance_percent,
        "selected": True,
        "reason": reason,
        "icon": t.icon or "",
    }


def _base_keys_for_path(goal: str, situation: str) -> set[str]:
    keys: set[str] = {KEY_CONSULTATION}

    if goal == GOAL_DOCS_ONLY:
        return keys

    if goal == GOAL_VISA_ONLY:
        keys.add(KEY_VISA)
        return keys

    if goal == GOAL_LANGUAGE:
        keys.update({KEY_ADMISSION, KEY_VISA})
        return keys

    if situation == SITUATION_HAS_ADMISSION:
        keys.update({KEY_VISA, KEY_REGISTRATION})
    elif situation == SITUATION_VISA_STAGE:
        keys.add(KEY_VISA)
    elif situation == SITUATION_IN_PROGRESS:
        keys.update({KEY_ADMISSION})
    else:
        keys.add(PACKAGE_KEY)

    return keys


def _resolve_dependencies(keys: set[str], tariffs_by_key: dict[str, PricingTariff]) -> set[str]:
    changed = True
    while changed:
        changed = False
        for key in list(keys):
            t = tariffs_by_key.get(key)
            if not t:
                continue
            for dep in t.get_depends_on():
                if dep not in keys and dep in tariffs_by_key:
                    keys.add(dep)
                    changed = True
    return keys


def _expand_package(keys: set[str]) -> set[str]:
    if PACKAGE_KEY not in keys:
        return keys
    keys.discard(PACKAGE_KEY)
    keys.update(
        {
            KEY_CONSULTATION,
            KEY_ADMISSION,
            KEY_VISA,
            KEY_REGISTRATION,
            KEY_RELOCATION,
        }
    )
    return keys


def _apply_situation_filters(keys: set[str], goal: str, situation: str) -> set[str]:
    if goal == GOAL_STUDY and situation == SITUATION_HAS_ADMISSION:
        keys.discard(KEY_ADMISSION)
        keys.discard(KEY_RELOCATION)
    if goal == GOAL_STUDY and situation == SITUATION_VISA_STAGE:
        keys.discard(KEY_ADMISSION)
        keys.discard(KEY_REGISTRATION)
        keys.discard(KEY_RELOCATION)
    if goal == GOAL_STUDY and situation == SITUATION_IN_PROGRESS:
        keys.discard(KEY_RELOCATION)
    return keys


def _suggest_extras(keys: set[str], goal: str, tariffs: list[PricingTariff]) -> list[dict[str, Any]]:
    suggestions = []
    for t in tariffs:
        if not t.is_calculator_option or t.calculator_key in keys:
            continue
        goals = t.get_auto_goals()
        if goals and goal not in goals:
            continue
        suggestions.append(
            {
                "key": t.calculator_key,
                "title": t.title,
                "price_display": t.price_display,
            }
        )
    return suggestions[:6]


def calculate_pricing(
    data: CalculatorInput,
    *,
    tariffs: list[PricingTariff] | None = None,
    countries: list[LivingAllowanceCountry] | None = None,
) -> dict[str, Any]:
    goal = (data.goal or "").strip()
    situation = (data.situation or "").strip()

    if goal not in VALID_GOALS:
        return {"ok": False, "error": "هدف نامعتبر است."}
    if situation not in VALID_SITUATIONS:
        return {"ok": False, "error": "وضعیت پرونده نامعتبر است."}

    if tariffs is None:
        tariffs = list(PricingTariff.objects.filter(is_active=True).select_related("category"))
    if countries is None:
        countries = list(LivingAllowanceCountry.objects.filter(is_active=True))

    tariffs_by_key = {t.calculator_key: t for t in tariffs}
    country = None
    if data.country_slug:
        country = next((c for c in countries if c.slug == data.country_slug), None)

    needs_country = any(
        tariffs_by_key.get(k) and tariffs_by_key[k].allowance_percent
        for k in _base_keys_for_path(goal, situation)
    )
    if needs_country and not country:
        return {
            "ok": False,
            "error": "برای محاسبه تعرفه، انتخاب کشور مقصد الزامی است.",
        }

    keys = _base_keys_for_path(goal, situation)
    keys |= set(data.extra_keys or [])
    keys -= set(data.excluded_keys or [])
    keys = _apply_situation_filters(keys, goal, situation)
    keys = _expand_package(keys)
    keys = _resolve_dependencies(keys, tariffs_by_key)

    reasons: dict[str, str] = {}
    if goal == GOAL_STUDY and situation == SITUATION_STARTING:
        reasons[KEY_ADMISSION] = "حداکثر ۴۰٪ یک‌ماه مقرری — اخذ پذیرش (ماده ۳-۲)"
        reasons[KEY_VISA] = "حداکثر ۲۰٪ — روادید (ماده ۳-۳)"
        reasons[KEY_REGISTRATION] = "حداکثر ۲۰٪ — ثبتنام (ماده ۳-۴)"
        reasons[KEY_RELOCATION] = "۲۰٪ — انتقال و اسکان (ماده ۳-۵)"

    line_items: list[dict[str, Any]] = []
    ordered_keys = sorted(
        keys,
        key=lambda k: tariffs_by_key[k].order if k in tariffs_by_key else 999,
    )

    study_for_consult = None
    if country:
        study_for_consult = (
            StudyCountry.objects.filter(is_active=True, allowance_country=country)
            .order_by("order", "id")
            .first()
        )

    for key in ordered_keys:
        t = tariffs_by_key.get(key)
        if not t:
            continue
        if key == KEY_CONSULTATION and study_for_consult:
            from .pricing_countries import _consultation_line

            consult_line = _consultation_line(study_for_consult, t, country)
            if reasons.get(key):
                consult_line["reason"] = reasons[key]
            line_items.append(consult_line)
        else:
            line_items.append(_tariff_line(t, country=country, reason=reasons.get(key, "")))

    totals = sum_by_currency(line_items)
    primary_currency = country.currency if country else (next(iter(totals), "") if totals else "")
    total_display = format_totals(totals) if totals else "کشور مقصد را انتخاب کنید"

    upfront_display = ""
    remainder_display = ""
    if totals and len(totals) == 1 and primary_currency:
        total_amt = totals[primary_currency]
        upfront_display = format_percent_of_total(total_amt, 40, primary_currency)
        remainder_display = format_percent_of_total(total_amt, 60, primary_currency)
    elif totals:
        upfront_parts = []
        remainder_parts = []
        for cur, amt in totals.items():
            upfront_parts.append(format_percent_of_total(amt, 40, cur))
            remainder_parts.append(format_percent_of_total(amt, 60, cur))
        upfront_display = " + ".join(p for p in upfront_parts if p)
        remainder_display = " + ".join(p for p in remainder_parts if p)

    living_info = None
    if country:
        living_info = {
            "slug": country.slug,
            "name": country.name,
            "amount": country.amount,
            "currency": country.currency,
            "currency_label": dict(LivingAllowanceCountry.CURRENCY_CHOICES).get(
                country.currency, country.currency
            ),
            "display": country.allowance_display,
            "region": country.region_group,
        }

    notes: list[str] = [CURRENCY_NOTE, CONTRACT_PAYMENT_NOTE, APPLICANT_COSTS_NOTE]
    if living_info:
        notes.insert(
            0,
            f"مقرری بانکی یک‌ماهه {country.name}: {country.allowance_display}",
        )

    return {
        "ok": True,
        "goal": goal,
        "situation": situation,
        "services": line_items,
        "totals_by_currency": totals,
        "primary_currency": primary_currency,
        "subtotal_display": total_display,
        "total_display": total_display,
        "upfront_display": upfront_display,
        "remainder_display": remainder_display,
        "living_allowance": living_info,
        "optional_extras": _suggest_extras(keys, goal, tariffs),
        "notes": notes,
    }


def get_calculator_steps(goal: str | None = None) -> list[dict[str, Any]]:
    steps = [
        {
            "id": "goal",
            "title": "هدف شما چیست؟",
            "subtitle": "خدمات قرارداد بر اساس مسیر شما پیشنهاد می‌شود",
            "type": "choice",
            "options": [
                {"value": GOAL_STUDY, "label": "مهاجرت تحصیلی", "icon": "ti-book"},
                {"value": GOAL_LANGUAGE, "label": "دوره زبان", "icon": "ti-world"},
                {"value": GOAL_VISA_ONLY, "label": "فقط روادید / ویزا", "icon": "ti-id-badge"},
                {"value": GOAL_DOCS_ONLY, "label": "فقط مشاوره", "icon": "ti-comments-smiley"},
            ],
        },
    ]

    if goal in VALID_GOALS and goal != GOAL_DOCS_ONLY:
        steps.append(
            {
                "id": "country",
                "title": "کشور مقصد",
                "subtitle": "تعرفه بر اساس ارز و مقرری همان کشور محاسبه می‌شود",
                "type": "country_search",
            }
        )

    situation_options = {
        GOAL_STUDY: [
            {"value": SITUATION_STARTING, "label": "شروع کامل پرونده", "icon": "ti-flag-alt"},
            {"value": SITUATION_HAS_ADMISSION, "label": "پذیرش دارم", "icon": "ti-check-box"},
            {"value": SITUATION_IN_PROGRESS, "label": "در حال اخذ پذیرش", "icon": "ti-reload"},
            {"value": SITUATION_VISA_STAGE, "label": "مرحله ویزا", "icon": "ti-id-badge"},
        ],
        GOAL_LANGUAGE: [
            {"value": SITUATION_STARTING, "label": "شروع پرونده", "icon": "ti-flag-alt"},
            {"value": SITUATION_IN_PROGRESS, "label": "در حال اپلای", "icon": "ti-reload"},
            {"value": SITUATION_HAS_ADMISSION, "label": "پذیرش دارم", "icon": "ti-check-box"},
        ],
        GOAL_VISA_ONLY: [
            {"value": SITUATION_VISA_STAGE, "label": "آماده اقدام ویزا", "icon": "ti-id-badge"},
            {"value": SITUATION_IN_PROGRESS, "label": "آماده‌سازی مدارک", "icon": "ti-files"},
        ],
    }
    if goal in situation_options:
        steps.append(
            {
                "id": "situation",
                "title": "در چه مرحله‌ای هستید؟",
                "subtitle": "تعرفه مطابق بندهای قرارداد تنظیم می‌شود",
                "type": "choice",
                "options": situation_options[goal],
            }
        )

    steps.append(
        {
            "id": "extras",
            "title": "خدمات اضافی (اختیاری)",
            "subtitle": "در صورت نیاز — می‌توانید رد کنید",
            "type": "extras",
            "skippable": True,
        }
    )
    steps.append({"id": "result", "title": "برآورد تعرفه (ارز کشور مقصد)", "type": "result"})
    return steps
