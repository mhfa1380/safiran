"""
ساخت تایم ملاقات برای همیشه ۱ هفته آینده.
هر بار اجرا: اسلات‌های آینده حذف و دوباره ساخته می‌شوند (~۱۵٪ رندوم رزرو شده).
استفاده: python manage.py generate_consultation_slots
"""
import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import ConsultationSlot


TIME_LABELS = [
    "۰۹:۰۰ - ۰۹:۳۰",
    "۰۹:۳۰ - ۱۰:۰۰",
    "۱۰:۰۰ - ۱۰:۳۰",
    "۱۰:۳۰ - ۱۱:۰۰",
    "۱۱:۰۰ - ۱۱:۳۰",
    "۱۴:۰۰ - ۱۴:۳۰",
    "۱۴:۳۰ - ۱۵:۰۰",
    "۱۵:۰۰ - ۱۵:۳۰",
]


class Command(BaseCommand):
    help = (
        "ساخت تایم ملاقات برای ۱ هفته آینده. هر بار اجرا، اسلات‌های آینده حذف و دوباره ساخته می‌شوند. "
        "~۱۵٪ اسلات‌ها به‌صورت رندوم رزرو شده."
    )

    def handle(self, *args, **options):
        today = timezone.localdate()

        # حذف اسلات‌های آینده
        deleted, _ = ConsultationSlot.objects.filter(date__gte=today).delete()
        created = 0

        for day_offset in range(7):
            d = today + timedelta(days=day_offset)
            if d.weekday() < 5:  # شنبه تا چهارشنبه
                for order, label in enumerate(TIME_LABELS):
                    ConsultationSlot.objects.create(
                        date=d,
                        time_label=label,
                        order=order,
                        is_booked=random.random() < 0.15,  # ~۱۵٪ رندوم رزرو شده
                    )
                    created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Consultation slots: {created} created, {deleted} removed."
            )
        )

