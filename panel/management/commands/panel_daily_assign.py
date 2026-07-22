from django.core.management.base import BaseCommand

from panel.services import maybe_run_daily_distribution


class Command(BaseCommand):
    help = "اجرای توزیع روزانهٔ پرونده‌های پنل (برای cron)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="حتی اگر امروز قبلاً اجرا شده باشد دوباره اجرا کن",
        )

    def handle(self, *args, **options):
        result = maybe_run_daily_distribution(force=options["force"])
        if result is None:
            self.stdout.write(self.style.WARNING("توزیع روزانه خاموش است یا امروز اجرا شده."))
            return
        self.stdout.write(
            self.style.SUCCESS(
                f"assigned={result.get('assigned', 0)} skipped={result.get('skipped', 0)} ran_on={result.get('ran_on')}"
            )
        )
