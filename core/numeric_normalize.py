"""تبدیل ارقام فارسی/عربی و جداکننده اعشار به فرم انگلیسی برای ذخیره و اعتبارسنجی."""
from __future__ import annotations

import re

_PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹"
_ARABIC_INDIC_DIGITS = "٠١٢٣٤٥٦٧٨٩"
_EN_DIGITS = "0123456789"


def digits_to_en(text: str) -> str:
    """ارقام فارسی و عربی‌ـهندی → 0-9؛ جداکننده اعشار یکسان."""
    if not text:
        return ""
    s = str(text).translate(
        str.maketrans(_PERSIAN_DIGITS + _ARABIC_INDIC_DIGITS, _EN_DIGITS * 2)
    )
    return s.replace("٫", ".").replace("،", ".").replace(",", ".")


def first_number_match(text: str) -> re.Match[str] | None:
    normalized = digits_to_en(text)
    return re.search(r"(\d+(?:\.\d+)?)", normalized)


def first_number_float(text: str) -> float | None:
    m = first_number_match(text)
    return float(m.group(1)) if m else None


def _has_percent_marker(text: str) -> bool:
    return "%" in text or "٪" in text or "درصد" in text


def normalize_average_grade_for_storage(raw: str) -> str:
    """مقدار نهایی معدل با ارقام انگلیسی (مثلاً 17.5 یا 85%)."""
    text = (raw or "").strip()
    if not text:
        return ""
    normalized = digits_to_en(text)
    has_percent = _has_percent_marker(text) or _has_percent_marker(normalized)
    m = first_number_match(normalized)
    if not m:
        return normalized.strip()
    num = m.group(1)
    if has_percent:
        return f"{num}%"
    return num


def normalize_language_score_for_storage(raw: str) -> str:
    """نمره زبان با ارقام انگلیسی."""
    text = (raw or "").strip()
    if not text:
        return ""
    m = first_number_match(text)
    if m:
        return m.group(1)
    return digits_to_en(text).strip()
