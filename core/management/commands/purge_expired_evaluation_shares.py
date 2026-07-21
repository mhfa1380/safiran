from django.core.management.base import BaseCommand

from core.evaluation_share import purge_expired_evaluation_shares


class Command(BaseCommand):
    help = "حذف لینک‌های منقضی‌شده نتیجه ارزیابی (بیش از ۷ روز)"

    def handle(self, *args, **options):
        n = purge_expired_evaluation_shares()
        self.stdout.write(self.style.SUCCESS(f"Deleted {n} expired evaluation share(s)."))
