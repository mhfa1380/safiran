from django.core.management.base import BaseCommand

from panel.services import setup_demo_users, sync_consultation_appointments, sync_contact_messages, sync_leads_to_cases


class Command(BaseCommand):
    help = "ساخت یوزر مدیر/پرسنل پنل و همگام‌سازی لیدها به پرونده"

    def add_arguments(self, parser):
        parser.add_argument("--skip-sync", action="store_true")
        parser.add_argument("--limit", type=int, default=None)

    def handle(self, *args, **options):
        creds = setup_demo_users()
        self.stdout.write(self.style.SUCCESS("Panel users ready:"))
        self.stdout.write(f"  manager: {creds.get('manager_username')} (also panel_manager)")
        self.stdout.write(f"  staff:   {creds.get('staff_username')} (also panel_staff)")
        self.stdout.write(f"  fallback password: {creds.get('fallback_password')}")
        if not options["skip_sync"]:
            stats = sync_leads_to_cases(limit=options["limit"])
            self.stdout.write(
                self.style.SUCCESS(
                    f"sync: evaluations={stats['evaluations']} consultations={stats['consultations']} skipped={stats['skipped']}"
                )
            )
            appts = sync_consultation_appointments()
            contacts = sync_contact_messages(limit=options["limit"])
            self.stdout.write(self.style.SUCCESS(f"appointments={appts} contacts={contacts}"))
