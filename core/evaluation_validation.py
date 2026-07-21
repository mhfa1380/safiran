"""
اعتبارسنجی فیلدهای فرم ارزیابی — مشترک بین فرم Django و اعتبارسنجی لایو (JS از همان قواعد پیروی می‌کند).
"""
from __future__ import annotations

import re

from .evaluation_engine import parse_average_grade_detail
from .evaluation_form_countries import EVAL_FORM_REAL_COUNTRY_CODES
from .numeric_normalize import (
    _has_percent_marker,
    digits_to_en,
    first_number_float,
    normalize_average_grade_for_storage,
    normalize_language_score_for_storage,
)

_REAL_COUNTRY_CODES = frozenset(EVAL_FORM_REAL_COUNTRY_CODES)

# محدوده نمره خام بر اساس نوع آزمون (حداقل، حداکثر، برچسب)
_LANG_SCORE_RANGES: dict[str, tuple[float, float, str]] = {
    "ielts": (0.0, 9.0, "IELTS"),
    "toefl": (0.0, 120.0, "TOEFL iBT"),
    "duolingo": (0.0, 160.0, "Duolingo"),
    "pte": (0.0, 90.0, "PTE"),
    "delf": (1.0, 4.0, "DELF/DALF (سطح ۱–۴)"),
    "testdaf": (1.0, 5.0, "TestDaF (سطح ۱–۵)"),
    "sat": (400.0, 1600.0, "SAT"),
    "yos": (0.0, 100.0, "YOS"),
}


def validate_average_grade(raw: str) -> dict[str, str]:
    """
    وضعیت: ok | warn | error | neutral
    message: متن راهنما یا خطا
    """
    text = (raw or "").strip()
    if not text:
        return {
            "status": "neutral",
            "message": "معدل از ۰ تا ۲۰ وارد کنید (مثلاً ۱۷.۵). برای درصد از علامت ٪ استفاده کنید.",
        }

    if _has_percent_marker(text):
        gpa, uncertain, note = parse_average_grade_detail(text)
        if gpa is None:
            return {"status": "error", "message": note or "فرمت درصد معدل نامعتبر است."}
        return {
            "status": "warn",
            "message": note or f"معادل {gpa:.1f} از ۲۰ محاسبه شد.",
        }

    s = digits_to_en(text)
    val = first_number_float(s)
    if val is None:
        return {"status": "error", "message": "فقط عدد وارد کنید (مثلاً ۱۷.۵)."}

    if val <= 4.5:
        converted = round(val * 5.0, 2)
        return {
            "status": "ok",
            "message": f"مقیاس ۴ نمره‌ای → معادل {converted:g} از ۲۰.",
        }

    if 5.0 <= val <= 20.0:
        return {"status": "ok", "message": f"معدل {val:g} از ۲۰ — معتبر است."}

    if 20.0 < val <= 100.0:
        converted = round(val * 0.2, 2)
        return {
            "status": "warn",
            "message": (
                f"عدد {val:g} بالاتر از ۲۰ است — به‌عنوان درصد ({val:g}٪) تفسیر می‌شود "
                f"(معادل {converted:g} از ۲۰). اگر معدل ۰–۲۰ مدنظر است، عدد را اصلاح کنید."
            ),
        }

    return {
        "status": "error",
        "message": (
            f"معدل در مقیاس ایرانی بیش از ۲۰ نیست. مقدار {val:g} نامعتبر است؛ "
            "برای درصد حداکثر ۱۰۰٪ با علامت ٪ وارد کنید."
        ),
    }


def validate_phone(raw: str) -> dict[str, str]:
    text = digits_to_en((raw or "").strip())
    digits = re.sub(r"\D", "", text)
    if not digits:
        return {"status": "neutral", "message": "شماره موبایل ۱۱ رقمی با ۰۹ شروع شود."}
    if digits.startswith("98") and len(digits) >= 12:
        digits = "0" + digits[2:]
    if not digits.startswith("09"):
        return {"status": "error", "message": "شماره باید با ۰۹ شروع شود (مثلاً ۰۹۱۲۳۴۵۶۷۸۹)."}
    if len(digits) != 11:
        return {
            "status": "error",
            "message": f"شماره باید ۱۱ رقم باشد (فعلاً {len(digits)} رقم).",
        }
    return {"status": "ok", "message": "شماره تماس معتبر است."}


def validate_language_score(test_type: str, raw: str) -> dict[str, str]:
    if not test_type or test_type == "none":
        return {"status": "neutral", "message": ""}
    text = (raw or "").strip()
    if not text:
        return {"status": "neutral", "message": "نمره آزمون را وارد کنید (اختیاری ولی توصیه می‌شود)."}

    val = first_number_float(text)
    if val is None:
        return {"status": "error", "message": "فقط عدد نمره را وارد کنید."}
    bounds = _LANG_SCORE_RANGES.get(test_type)
    if not bounds:
        return {"status": "ok", "message": "نمره ثبت شد."}

    lo, hi, label = bounds
    if val < lo or val > hi:
        return {
            "status": "error",
            "message": f"برای {label} بازه معتبر حدود {lo:g} تا {hi:g} است.",
        }
    return {"status": "ok", "message": f"نمره {val:g} برای {label} در بازه معتبر است."}


def extract_jalali_year(text: str) -> int | None:
    """سال شمسی چهاررقمی را از متن ترم/سال استخراج می‌کند."""
    s = digits_to_en((text or "").strip())
    m = re.search(r"(13\d{2}|14\d{2})", s)
    if not m:
        return None
    return int(m.group(1))


def validate_preferred_intake(raw: str, min_jalali_year: int) -> dict[str, str]:
    text = (raw or "").strip()
    if not text:
        return {"status": "neutral", "message": ""}
    year = extract_jalali_year(text)
    if year is None:
        return {"status": "error", "message": "فرمت ترم / سال شروع نامعتبر است."}
    if year < min_jalali_year:
        return {
            "status": "error",
            "message": f"سال شروع نمی‌تواند قبل از {min_jalali_year} (امسال) باشد.",
        }
    return {"status": "ok", "message": "ترم / سال شروع معتبر است."}


def pick_target_country_from_desired(desired_csv: str) -> str:
    codes = [p.strip() for p in (desired_csv or "").split(",") if p.strip()]
    for code in codes:
        if code in _REAL_COUNTRY_CODES:
            return code
    if "other" in codes:
        return "other"
    return ""
