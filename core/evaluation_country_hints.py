"""پیشنهاد کشور مقصد وقتی کاربر «سایر» یا «مطمئن نیستم» انتخاب کرده."""
from __future__ import annotations

from core.study_destinations import (
    ALL_DESTINATION_LABELS,
    PRIMARY_STUDY_COUNTRY_CODES,
    WORLD_STUDY_COUNTRY_CODES,
    country_flag_static,
)

_SUGGESTION_COUNTRIES = tuple(
    sorted(
        PRIMARY_STUDY_COUNTRY_CODES | set(WORLD_STUDY_COUNTRY_CODES),
        key=lambda c: (0 if c in PRIMARY_STUDY_COUNTRY_CODES else 1, ALL_DESTINATION_LABELS.get(c, c)),
    )
)

_STEM_KEYWORDS = (
    "مهندسی",
    "کامپیوتر",
    "نرم",
    "برق",
    "مکانیک",
    "عمران",
    "شیمی",
    "فیزیک",
    "ریاضی",
    "engineer",
    "computer",
    "software",
    "it",
    "data",
)
_MEDICAL_KEYWORDS = ("پزشک", "پزشکی", "دندان", "پرستاری", "medic", "health", "nursing", "pharm")
_BUSINESS_KEYWORDS = ("مدیریت", "MBA", "business", "account", "اقتصاد", "finance", "marketing")
_ARTS_KEYWORDS = ("هنر", "طراحی", "معماری", "architect", "design", "art")


def _field_category(field: str) -> str:
    f = (field or "").lower()
    if any(k in f for k in _STEM_KEYWORDS):
        return "stem"
    if any(k in f for k in _MEDICAL_KEYWORDS):
        return "medical"
    if any(k in f for k in _BUSINESS_KEYWORDS):
        return "business"
    if any(k in f for k in _ARTS_KEYWORDS):
        return "arts"
    return "general"


def _parse_gpa(raw: str) -> float | None:
    from .numeric_normalize import first_number_float

    if not (raw or "").strip():
        return None
    val = first_number_float(raw)
    if val is None:
        return None
    try:
        val = float(val)
    except (TypeError, ValueError):
        return None
    if val <= 0:
        return None
    if val > 20:
        val = val / 100 * 20
    return min(val, 20.0)


def _score_country_for_profile(
    code: str,
    *,
    gpa: float | None,
    field_cat: str,
    degree: str,
    has_lang: bool,
    lang_score: float | None,
    budget_limited: bool,
) -> tuple[float, str]:
    score = 40.0
    reason = ALL_DESTINATION_LABELS.get(code, code)

    if code == "canada":
        score += 12.0
        reason = "مسیر PGWP و اقامت پس از تحصیل — مناسب برنامه‌ریزی بلندمدت"
        if gpa and gpa >= 16:
            score += 6.0
        if field_cat == "stem":
            score += 5.0
    elif code == "germany":
        score += 10.0
        reason = "شهریه پایین در دانشگاه‌های دولتی و کیفیت آموزشی بالا"
        if budget_limited:
            score += 8.0
        if field_cat == "stem":
            score += 4.0
    elif code == "china":
        score += 9.0
        reason = "بورسیه CSC و هزینه مناسب‌تر نسبت به غرب"
        if budget_limited:
            score += 10.0
    elif code == "spain":
        score += 8.0
        reason = "هزینه زندگی متعادل‌تر در اروپا"
        if budget_limited:
            score += 6.0
    elif code == "italy":
        score += 7.0
        reason = "شهریه و هزینه زندگی مناسب در جنوب اروپا"
        if budget_limited:
            score += 5.0
    elif code == "uk":
        score += 8.0
        reason = "دانشگاه‌های رتبه‌برتر جهان — مناسب رزومه قوی"
        if gpa and gpa >= 17:
            score += 5.0
    elif code == "usa":
        score += 7.0
        reason = "تنوع برنامه و بورسیه تحقیقاتی — رقابتی برای معدل بالا"
        if gpa and gpa >= 17:
            score += 6.0
        if field_cat == "stem":
            score += 4.0
    elif code == "australia":
        score += 7.0
        reason = "مسیر مهاجرت و بازار کار برای فارغ‌التحصیلان"
    elif code == "netherlands":
        score += 6.0
        reason = "برنامه‌های انگلیسی‌زبان فراوان در اروپا"
        if field_cat in ("stem", "business"):
            score += 3.0
    elif code == "france":
        score += 5.0
        reason = "دانشگاه‌های معتبر با شهریه دولتی پایین"
    elif code == "malaysia":
        score += 6.0
        reason = "هزینه پایین و پذیرش نسبتاً آسان‌تر"
        if budget_limited:
            score += 8.0
    elif code == "uae":
        score += 4.0
        reason = "پردیس‌های بین‌المللی و موقعیت کاری منطقه‌ای"
    elif code == "turkey":
        score += 5.0
        reason = "هزینه مناسب و برنامه‌های انگلیسی‌زبان"
        if budget_limited:
            score += 5.0

    if field_cat == "medical" and code in ("germany", "china", "uk", "canada"):
        score += 4.0
        reason = "مسیرهای شناخته‌شده برای رشته‌های پزشکی و علوم سلامت"

    if not has_lang and code in ("china", "malaysia", "turkey"):
        score += 3.0
        reason = "گزینه‌های پذیرش مشروط زبان بیشتر"

    if has_lang and lang_score and lang_score >= 6.5 and code in ("uk", "usa", "canada", "australia"):
        score += 4.0

    grad = degree in ("master", "phd", "postdoc", "کارشناسی ارشد", "دکتری")
    if grad and code in ("germany", "canada", "usa", "uk"):
        score += 3.0

    return score, reason


def profile_ready_for_country_suggestions(
    *,
    field_of_study: str = "",
    average_grade: str = "",
    current_degree: str = "",
) -> bool:
    """حداقل رشته + معدل (یا مدرک) برای پیشنهاد هوشمند — نه بلافاصله پس از «سایر»."""
    field = (field_of_study or "").strip()
    if len(field) < 2:
        return False
    if _parse_gpa(average_grade) is not None:
        return True
    return bool((current_degree or "").strip())


def suggest_destination_countries(
    *,
    field_of_study: str = "",
    current_degree: str = "",
    average_grade: str = "",
    language_test: str = "",
    language_score: str = "",
    budget_limited: bool = False,
    limit: int = 6,
) -> list[dict]:
    """برگرداندن لیست کشورهای پیشنهادی با دلیل کوتاه."""
    if not profile_ready_for_country_suggestions(
        field_of_study=field_of_study,
        average_grade=average_grade,
        current_degree=current_degree,
    ):
        return []

    gpa = _parse_gpa(average_grade)
    field_cat = _field_category(field_of_study)
    has_lang = (language_test or "").strip() not in ("", "none", "ندارم")
    lang_val = _parse_gpa(language_score)

    scored: list[tuple[float, str, str]] = []
    for code in _SUGGESTION_COUNTRIES:
        s, reason = _score_country_for_profile(
            code,
            gpa=gpa,
            field_cat=field_cat,
            degree=current_degree,
            has_lang=has_lang,
            lang_score=lang_val,
            budget_limited=budget_limited,
        )
        scored.append((s, code, reason))

    scored.sort(key=lambda x: -x[0])
    out: list[dict] = []
    for score, code, reason in scored[:limit]:
        out.append(
            {
                "code": code,
                "label": ALL_DESTINATION_LABELS.get(code, code),
                "flag": country_flag_static(code),
                "score": round(score, 1),
                "reason": reason,
            }
        )
    return out
