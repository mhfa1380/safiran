"""بازسازی فوری وزن‌های یادگیری تطبیقی موتور ارزیابی."""

from django.core.management.base import BaseCommand

from core.evaluation_learning import build_adaptive_weights


class Command(BaseCommand):
    help = "بازسازی آمار یادگیری از پرونده‌های ارزیابی برای پیشنهاد هوشمندتر"

    def handle(self, *args, **options):
        weights = build_adaptive_weights(force=True)
        self.stdout.write(
            self.style.SUCCESS(
                f"یادگیری تطبیقی: {weights.sample_count} پرونده | "
                f"فعال={'بله' if weights.active else 'خیر (حداقل نمونه لازم)'} | "
                f"به‌روز: {weights.updated_at[:19] if weights.updated_at else '-'}"
            )
        )
