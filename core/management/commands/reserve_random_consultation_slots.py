"""
ساخت تایم ملاقات برای همیشه ۱ هفته آینده (۹ صبح تا ۱۷).
هر روز اجرا می‌شود؛ اگر تاریخ قبلاً اسلات دارد، فقط آن‌چه کم است اضافه می‌شود.
بیش از ۱ هفته اسلات ساخته نمی‌شود.

استفاده:
  python manage.py reserve_random_consultation_slots
  یا اجرای مستقیم از هر مسیر: python path/to/reserve_random_consultation_slots.py
"""
import os
import subprocess
import sys

# اجرای مستقیم: قبل از importهای Django، manage.py را صدا بزن
if __name__ == "__main__":
    _dir = os.path.dirname(os.path.abspath(__file__))
    _root = os.path.dirname(os.path.dirname(os.path.dirname(_dir)))
    sys.exit(subprocess.run([sys.executable, "manage.py", "reserve_random_consultation_slots"], cwd=_root).returncode)

import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import ConsultationSlot


# ۹ صبح تا ۱۷ — هر ۳۰ دقیقه یک اسلات
TIME_LABELS = [
    "۰۹:۰۰ - ۰۹:۳۰",
    "۰۹:۳۰ - ۱۰:۰۰",
    "۱۰:۰۰ - ۱۰:۳۰",
    "۱۰:۳۰ - ۱۱:۰۰",
    "۱۱:۰۰ - ۱۱:۳۰",
    "۱۱:۳۰ - ۱۲:۰۰",
    "۱۲:۰۰ - ۱۲:۳۰",
    "۱۲:۳۰ - ۱۳:۰۰",
    "۱۳:۰۰ - ۱۳:۳۰",
    "۱۳:۳۰ - ۱۴:۰۰",
    "۱۴:۰۰ - ۱۴:۳۰",
    "۱۴:۳۰ - ۱۵:۰۰",
    "۱۵:۰۰ - ۱۵:۳۰",
    "۱۵:۳۰ - ۱۶:۰۰",
    "۱۶:۰۰ - ۱۶:۳۰",
    "۱۶:۳۰ - ۱۷:۰۰",
]


def run_reserve_random_slots() -> dict:
    """
    ساخت اسلات‌های ۱ هفته (۹ تا ۱۷).
    اسلات‌های ناقص هر روز تکمیل می‌شوند؛ اسلات‌های beyond ۱ هفته حذف می‌شوند.
    جمعه تعطیل است (weekday=4).
    """
    today = timezone.localdate()
    end_date = today + timedelta(days=6)

    # حذف اسلات‌های بعد از ۱ هفته
    deleted, _ = ConsultationSlot.objects.filter(date__gt=end_date).delete()

    created = 0
    for day_offset in range(7):
        d = today + timedelta(days=day_offset)
        if d.weekday() == 4:  # جمعه تعطیل
            continue
        # اسلات‌های موجود این تاریخ
        existing_labels = set(
            ConsultationSlot.objects.filter(date=d).values_list("time_label", flat=True)
        )
        # فقط اسلات‌های کم‌شده را اضافه کن
        for order, label in enumerate(TIME_LABELS):
            if label in existing_labels:
                continue
            ConsultationSlot.objects.create(
                date=d,
                time_label=label,
                order=order,
                is_booked=random.random() < 0.15,  # ~۱۵٪ رندوم رزرو شده
            )
            created += 1

    return {"created": created, "deleted": deleted}


def _format_message(result: dict, lang: str = "en") -> str:
    c, d = result["created"], result["deleted"]
    if lang == "fa":
        parts = []
        if c > 0:
            parts.append(f"{c} اسلات ساخته شد")
        if d > 0:
            parts.append(f"{d} اسلات حذف شد")
        if not parts:
            return "هیچ تغییری لازم نبود؛ همه اسلات‌ها تا ۱ هفته آینده موجود است."
        return "؛ ".join(parts) + "."
    parts = []
    if c > 0:
        parts.append(f"{c} slots created")
    if d > 0:
        parts.append(f"{d} slots removed")
    if not parts:
        return "No change needed; all slots for the next week exist."
    return "; ".join(parts) + "."


class Command(BaseCommand):
    help = (
        "ساخت تایم ملاقات برای ۱ هفته آینده (۹ تا ۱۷). "
        "هر روز اجرا کنید؛ اگر تاریخ قبلاً اسلات دارد، دوباره ساخته نمی‌شود."
    )

    def handle(self, *args, **options):
        result = run_reserve_random_slots()
        message = _format_message(result, lang="en")
        self.stdout.write(self.style.SUCCESS(message))
