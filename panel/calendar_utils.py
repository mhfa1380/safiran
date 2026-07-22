"""تقویم شمسی و جلسات پنل."""
from __future__ import annotations

from datetime import date, datetime, time, timedelta

from django.utils import timezone

from core.utils import JALALI_MONTH_NAMES, gregorian_to_jalali, jalali_to_gregorian


def jalali_today() -> tuple[int, int, int]:
    d = timezone.localdate()
    return gregorian_to_jalali(d.year, d.month, d.day)


def jalali_month_length(jy: int, jm: int) -> int:
    if jm <= 6:
        return 31
    if jm <= 11:
        return 30
    # اسفند: سال کبیسه شمسی تقریبی
    return 30 if _is_jalali_leap(jy) else 29


def _is_jalali_leap(jy: int) -> bool:
    # تقریب رایج: باقیمانده بر ۳۳
    breaks = (1, 5, 9, 13, 17, 22, 26, 30)
    return (jy % 33) in breaks


def jalali_month_bounds(jy: int, jm: int) -> tuple[date, date]:
    gy1, gm1, gd1 = jalali_to_gregorian(jy, jm, 1)
    last = jalali_month_length(jy, jm)
    gy2, gm2, gd2 = jalali_to_gregorian(jy, jm, last)
    return date(gy1, gm1, gd1), date(gy2, gm2, gd2)


def shift_jalali_month(jy: int, jm: int, delta: int) -> tuple[int, int]:
    jm += delta
    while jm > 12:
        jm -= 12
        jy += 1
    while jm < 1:
        jm += 12
        jy -= 1
    return jy, jm


def build_month_cells(jy: int, jm: int) -> list[dict]:
    """سلول‌های ماه برای گرید ۷ستونه (شنبه اول)."""
    start_g, _ = jalali_month_bounds(jy, jm)
    # weekday: Mon=0 ... Sun=6 — در ایران شنبه اول هفته است
    # Python: Monday=0 ... Sunday=6
    # شنبه = 5
    first_wd = start_g.weekday()  # 0=Mon
    # فاصله از شنبه: Sat=5 -> 0, Sun=6 -> 1, Mon=0 -> 2, ...
    offset = (first_wd - 5) % 7
    length = jalali_month_length(jy, jm)
    cells: list[dict] = []
    # روزهای خالی قبل
    for _ in range(offset):
        cells.append({"empty": True})
    today = timezone.localdate()
    ty, tm, td = gregorian_to_jalali(today.year, today.month, today.day)
    for jd in range(1, length + 1):
        gy, gm, gd = jalali_to_gregorian(jy, jm, jd)
        gdate = date(gy, gm, gd)
        cells.append(
            {
                "empty": False,
                "jd": jd,
                "gdate": gdate,
                "is_today": (jy == ty and jm == tm and jd == td),
                "weekday": gdate.weekday(),
            }
        )
    while len(cells) % 7:
        cells.append({"empty": True})
    return cells


def parse_jalali_date(value: str) -> date | None:
    raw = (value or "").strip().translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789"))
    raw = raw.replace("-", "/").replace(".", "/")
    parts = [p for p in raw.split("/") if p]
    if len(parts) != 3:
        return None
    try:
        jy, jm, jd = int(parts[0]), int(parts[1]), int(parts[2])
        gy, gm, gd = jalali_to_gregorian(jy, jm, jd)
        return date(gy, gm, gd)
    except (ValueError, TypeError):
        return None


def parse_time_hm(value: str) -> time | None:
    raw = (value or "").strip().translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789"))
    try:
        h, m = map(int, raw.split(":")[:2])
        return time(h, m)
    except (ValueError, TypeError):
        return None


def combine_local(d: date, t: time):
    return timezone.make_aware(datetime.combine(d, t))


def month_title(jy: int, jm: int) -> str:
    name = JALALI_MONTH_NAMES[jm - 1] if 1 <= jm <= 12 else ""
    return f"{name} {jy}"
