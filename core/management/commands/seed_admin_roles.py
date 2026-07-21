from django.core.management.base import BaseCommand

from core.admin_roles import seed_admin_staff_roles


class Command(BaseCommand):
    help = "ایجاد یا بروزرسانی گروه‌های نقش کارمند و دسترسی‌های پنل ادمین"

    def handle(self, *args, **options):
        result = seed_admin_staff_roles()
        for name, count in result.items():
            self.stdout.write(self.style.SUCCESS(f"  {name}: {count} perms"))
        self.stdout.write(self.style.SUCCESS("Admin staff roles ready."))
