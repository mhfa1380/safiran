"""
فیلترهای قالب برای نمایش تاریخ شمسی و اعداد فارسی.
"""
from django import template
from django.utils import timezone

from core.utils import format_jalali_display

register = template.Library()

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
    if value is None:
        return ""
    if hasattr(value, "date"):
        dt = value
        if hasattr(dt, "tzinfo") and dt.tzinfo:
            dt = timezone.localtime(dt)
        value = dt.date()
    return format_jalali_display(value)
