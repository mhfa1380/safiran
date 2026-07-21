"""
فیلترهای قالب برای نمایش تاریخ شمسی و اعداد فارسی.
"""
from django import template
from django.utils import timezone

from core.utils import JALALI_MONTH_NAMES, format_jalali_display, gregorian_to_jalali

register = template.Library()


def _to_local_date(value):
    if value is None:
        return None
    if hasattr(value, "date"):
        dt = value
        if hasattr(dt, "tzinfo") and dt.tzinfo:
            dt = timezone.localtime(dt)
        return dt.date()
    return value

PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹"


@register.filter
def persian_numbers(value):
    """تبدیل اعداد انگلیسی به فارسی. مثلاً: ۲۵۰ → ۲۵۰"""
    if value is None:
        return ""
    s = str(value)
    return s.translate(str.maketrans("0123456789", PERSIAN_DIGITS))


@register.filter
def jalali(value):
    """تبدیل تاریخ میلادی به شمسی برای نمایش در قالب. مثلاً: ۷ آذر ۱۴۰۴"""
    d = _to_local_date(value)
    if d is None:
        return ""
    return format_jalali_display(d)


@register.filter
def jalali_day(value):
    """روز شمسی برای کارت وبلاگ."""
    d = _to_local_date(value)
    if d is None:
        return ""
    _, _, jd = gregorian_to_jalali(d.year, d.month, d.day)
    return str(jd)


@register.filter
def jalali_month_year(value):
    """ماه و سال شمسی برای کارت وبلاگ. مثلاً: آذر ۱۴۰۴"""
    d = _to_local_date(value)
    if d is None:
        return ""
    jy, jm, _ = gregorian_to_jalali(d.year, d.month, d.day)
    month_name = JALALI_MONTH_NAMES[jm - 1] if 1 <= jm <= 12 else ""
    return f"{month_name} {jy}"
