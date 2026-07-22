from datetime import date as _date, datetime, time


def gregorian_to_jalali(gy: int, gm: int, gd: int):
    """تبدیل تاریخ میلادی به شمسی (هجری شمسی). الگوریتم استاندارد، بدون وابستگی خارجی."""
    g_d_m = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    if gy > 1600:
        jy = 979
        gy -= 1600
    else:
        jy = 0
        gy -= 621
    if gm > 2:
        gy2 = gy + 1
    else:
        gy2 = gy
    days = (
        365 * gy
        + (gy2 + 3) // 4
        - (gy2 + 99) // 100
        + (gy2 + 399) // 400
        - 80
        + gd
        + g_d_m[gm - 1]
    )
    jy += 33 * (days // 12053)
    days %= 12053
    jy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        jy += (days - 1) // 365
        days = (days - 1) % 365
    if days < 186:
        jm = 1 + days // 31
        jd = 1 + days % 31
    else:
        jm = 7 + (days - 186) // 30
        jd = 1 + (days - 186) % 30
    return jy, jm, jd


def jalali_to_gregorian(jy: int, jm: int, jd: int):
    """تبدیل تاریخ شمسی به میلادی."""
    if jy > 979:
        gy = 1600
        jy -= 979
    else:
        gy = 621
    days = (365 * jy) + ((jy // 33) * 8) + (((jy % 33) + 3) // 4) + 78 + jd
    if jm < 7:
        days += (jm - 1) * 31
    else:
        days += ((jm - 7) * 30) + 186
    gy += 400 * (days // 146097)
    days %= 146097
    if days > 36524:
        days -= 1
        gy += 100 * (days // 36524)
        days %= 36524
        if days >= 365:
            days += 1
    gy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        gy += (days - 1) // 365
        days = (days - 1) % 365
    gd = days + 1
    sal_a = [
        0,
        31,
        29 if (gy % 4 == 0 and gy % 100 != 0) or (gy % 400 == 0) else 28,
        31,
        30,
        31,
        30,
        31,
        31,
        30,
        31,
        30,
        31,
    ]
    gm = 1
    while gm <= 12 and gd > sal_a[gm]:
        gd -= sal_a[gm]
        gm += 1
    return gy, gm, gd


def slot_has_started(slot, now) -> bool:
    """
    اگر اسلات امروز باشد و زمان شروعش گذشته یا در حال اجرا باشد، True برمی‌گرداند.
    چنین اسلاتی نباید برای انتخاب نمایش داده شود.
    """
    from django.utils import timezone as tz

    now_local = tz.localtime(now)
    if slot.date != now_local.date():
        return False
    # تبدیل اعداد فارسی به انگلیسی برای پارس
    persian_to_arabic = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")
    normalized = slot.time_label.translate(persian_to_arabic)
    parts = normalized.split("-")
    if len(parts) < 2:
        return False
    start_str = parts[0].strip()
    try:
        h, m = map(int, start_str.split(":"))
        slot_start = datetime.combine(slot.date, time(h, m))
        slot_start_aware = tz.make_aware(slot_start, tz.get_current_timezone())
        return slot_start_aware <= now
    except (ValueError, TypeError):
        return False


JALALI_MONTH_NAMES = (
    "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
    "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند",
)

_PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹"
_ASCII_DIGITS = "0123456789"
_EN_TO_FA_DIGITS = str.maketrans(_ASCII_DIGITS, _PERSIAN_DIGITS)
_FA_TO_EN_DIGITS = str.maketrans(_PERSIAN_DIGITS, _ASCII_DIGITS)


def to_persian_digits(value) -> str:
    """تبدیل ارقام انگلیسی به فارسی در رشته."""
    return str(value).translate(_EN_TO_FA_DIGITS)


def format_time_label_persian(label: str) -> str:
    """بازه زمانی مشاوره با ارقام فارسی، مثلاً ۱۰:۰۰ - ۱۰:۳۰."""
    if not label:
        return ""
    normalized = str(label).strip().translate(_FA_TO_EN_DIGITS)
    return to_persian_digits(normalized)


def format_jalali_day_label(d: _date) -> str:
    """برچسب روز برای انتخاب تاریخ: ۷ آذر ۱۴۰۴."""
    if d is None:
        return ""
    return to_persian_digits(format_jalali_display(d))


def format_jalali_date(d: _date) -> str:
    """تاریخ شمسی را به صورت ۱۳۸۰/۰۱/۰۵ برمی‌گرداند."""
    if d is None:
        return ""
    jy, jm, jd = gregorian_to_jalali(d.year, d.month, d.day)
    return f"{jy:04d}/{jm:02d}/{jd:02d}"


def format_jalali_display(d) -> str:
    """تاریخ شمسی برای نمایش: مثلاً ۷ آذر ۱۴۰۴."""
    if d is None:
        return ""
    if hasattr(d, "date"):
        d = d.date()
    jy, jm, jd = gregorian_to_jalali(d.year, d.month, d.day)
    month_name = JALALI_MONTH_NAMES[jm - 1] if 1 <= jm <= 12 else ""
    return f"{jd} {month_name} {jy}"


def format_date_both(d) -> str:
    """تاریخ میلادی و شمسی کنار هم برای ادمین."""
    if d is None:
        return ""
    if hasattr(d, "date"):
        d = d.date()
    j_str = format_jalali_date(d)
    m_str = d.strftime("%Y-%m-%d")
    return f"{j_str} ({m_str})"


def format_datetime_both(dt) -> str:
    """تاریخ و زمان میلادی و شمسی کنار هم برای ادمین."""
    if dt is None:
        return ""
    from django.utils import timezone as tz

    dt_local = tz.localtime(dt) if hasattr(dt, "tzinfo") and dt.tzinfo else dt
    d = dt_local.date() if isinstance(dt_local, datetime) else dt_local
    t_str = dt_local.strftime("%H:%M") if isinstance(dt_local, datetime) else ""
    j_str = format_jalali_date(d)
    m_str = d.strftime("%Y-%m-%d")
    return f"{j_str} {t_str} ({m_str} {t_str})" if t_str else f"{j_str} ({m_str})"


def get_client_ip(request) -> str:
    """
    IP کاربر برای rate limit — اول X-Forwarded-For بعد REMOTE_ADDR.
    """
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        parts = [p.strip() for p in xff.split(",") if p.strip()]
        if parts:
            return parts[0]
    return request.META.get("REMOTE_ADDR") or "unknown"


def is_rate_limited(request, key_prefix: str, limit: int, window_seconds: int) -> bool:
    """
    rate limit بسیار ساده بر اساس IP و cache پیش‌فرض Django.
    اگر تعداد درخواست‌ها در بازه مشخص از حد مجاز بیشتر شود، True برمی‌گرداند.
    """
    from django.core.cache import cache

    ip = get_client_ip(request)
    cache_key = f"rl:{key_prefix}:{ip}"

    # اولین درخواست: مقدار را روی ۱ ست می‌کنیم با انقضای window_seconds
    added = cache.add(cache_key, 1, window_seconds)
    if added:
        return False

    try:
        current = cache.incr(cache_key)
    except ValueError:
        # در صورت مشکل، امن‌تر این است که درخواست را محدود کنیم
        return True

    return current > limit


# --- فشرده‌سازی خودکار تصاویر ---
# تنظیمات استاندارد برای وب: کیفیت خوب، حجم مناسب، بدون افت محسوس

import os

IMAGE_MAX_WIDTH = 1920
IMAGE_MAX_HEIGHT = 1920
IMAGE_QUALITY_JPEG = 85
IMAGE_PNG_COMPRESS = 9  # 0-9، بیشتر = فشرده‌تر


def compress_image_file(file_field, max_width=IMAGE_MAX_WIDTH, max_height=IMAGE_MAX_HEIGHT):
    """
    فشرده‌سازی خودکار تصویر آپلودشده.
    - تغییر اندازه اگر بزرگتر از max_width/max_height باشد (حفظ نسبت)
    - JPEG: کیفیت 85
    - PNG: فشرده‌سازی سطح 9
    - اصلاح جهت بر اساس EXIF
    """
    if not file_field:
        return

    try:
        from PIL import Image, ImageOps
    except ImportError:
        return

    try:
        path = file_field.path
    except (ValueError, AttributeError):
        return

    if not path or not os.path.exists(path):
        return

    try:
        with Image.open(path) as img:
            if img.format not in ("JPEG", "PNG", "GIF", "WEBP"):
                return

            # اصلاح جهت بر اساس EXIF
            try:
                img = ImageOps.exif_transpose(img)
            except Exception:
                pass

            orig_w, orig_h = img.size

            # تغییر اندازه در صورت نیاز (حفظ نسبت)
            if orig_w > max_width or orig_h > max_height:
                img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)

            ext = os.path.splitext(path)[1].lower()

            if ext in (".png",):
                if img.mode == "RGBA":
                    img.save(path, "PNG", compress_level=IMAGE_PNG_COMPRESS, optimize=True)
                else:
                    img = img.convert("RGB")
                    img.save(path, "PNG", compress_level=IMAGE_PNG_COMPRESS, optimize=True)
            else:
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                img.save(path, "JPEG", quality=IMAGE_QUALITY_JPEG, optimize=True)

    except Exception:
        pass
