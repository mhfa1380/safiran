"""
برآورد هزینه خدمات از تعرفه — برای گزارش ارزیابی.
"""
from __future__ import annotations

from typing import Any

from django.urls import reverse

from .evaluation_engine import _COUNTRY_LABELS
from .models import EvaluationRequest
from .pricing_calculator import CalculatorInput, calculate_pricing
from .pricing_countries import DEFAULT_ALLOWANCE_SLUG

_COUNTRY_TO_ALLOWANCE = dict(DEFAULT_ALLOWANCE_SLUG)


def _situation_for_profile(profile) -> str:
    ev = profile.eval_req
    if ev.apply_timeline == EvaluationRequest.APPLY_SOON:
        return "starting"
    return "in_progress"


def build_pricing_insights_for_report(
    profile,
    country_code: str,
    *,
    scholarship_target: str = "",
) -> dict[str, Any] | None:
    """پیشنهاد بسته خدمات و برآورد هزینه بر اساس تعرفه موسسه."""
    allowance_slug = _COUNTRY_TO_ALLOWANCE.get(country_code, "")
    if not allowance_slug:
        return None

    goal = "study"
    if scholarship_target:
        goal = "study"

    result = calculate_pricing(
        CalculatorInput(
            goal=goal,
            situation=_situation_for_profile(profile),
            country_slug=allowance_slug,
        )
    )
    if not result.get("ok"):
        return None

    lines = result.get("lines") or []
    selected = [ln for ln in lines if ln.get("selected")]
    if not selected:
        selected = lines[:4]

    totals = result.get("totals") or []
    total_display = " — ".join(t.get("display", "") for t in totals if t.get("display")) or ""

    reasons: list[str] = []
    country_name = _COUNTRY_LABELS.get(country_code, country_code)
    if total_display:
        reasons.append(
            f"برآورد اولیه خدمات موسسه برای مسیر {country_name}: {total_display}"
        )
    else:
        reasons.append(f"تعرفه خدمات {country_name} در صفحه تعرفه قابل مشاهده است.")

    if scholarship_target:
        reasons.append("با تمرکز بورسیه، هزینه مشاوره و پرونده پذیرش جداگانه بررسی می‌شود.")

    if not profile.eval_req.has_financial_capacity:
        reasons.append(
            "با توجه به بودجه، کشورهایی با شهریه پایین‌تر و بورسیه قوی‌تر در اولویت قرار گرفتند."
        )

    return {
        "country_code": country_code,
        "country_name": country_name,
        "summary": result.get("summary") or "",
        "total_display": total_display,
        "totals": totals,
        "services": [
            {
                "title": ln.get("title", ""),
                "price_display": ln.get("price_display", ""),
                "reason": ln.get("reason", ""),
            }
            for ln in selected[:5]
        ],
        "payment_note": result.get("payment_note", ""),
        "applicant_note": result.get("applicant_note", ""),
        "reasons": reasons,
        "url": reverse("pricing"),
    }
