"""
نگهداری دوره‌ای دیتابیس — پاکسازی داده غیرضروری + VACUUM.

cron (روزی یک‌بار):
  0 3 * * * cd /path/to/safiran_site && python manage.py maintain_database
"""

from django.core.management.base import BaseCommand
from django.utils import timezone

from core.db_maintenance import get_database_size_bytes, run_database_maintenance


class Command(BaseCommand):
    help = "پاکسازی داده‌های قدیمی غیرضروری و بهینه‌سازی SQLite (VACUUM)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="فقط نمایش تعداد رکوردهای قابل حذف، بدون حذف",
        )
        parser.add_argument(
            "--no-vacuum",
            action="store_true",
            help="بدون اجرای VACUUM پس از پاکسازی",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        vacuum = not options["no_vacuum"]

        if dry_run:
            counts = self._dry_run_counts()
            for key, count in counts.items():
                self.stdout.write(f"  {key}: {count}")
            self.stdout.write(
                self.style.WARNING(
                    f"جمع قابل حذف: {sum(counts.values())} (dry-run — حذف نشد)"
                )
            )
            size_mb = get_database_size_bytes() / (1024 * 1024)
            self.stdout.write(f"حجم فعلی دیتابیس: {size_mb:.2f} MB")
            return

        size_before = get_database_size_bytes() / (1024 * 1024)
        self.stdout.write(
            f"شروع نگهداری — {timezone.now():%Y-%m-%d %H:%M} | حجم قبل: {size_before:.2f} MB"
        )
        report = run_database_maintenance(vacuum=vacuum)

        for key, count in report.deleted.items():
            style = self.style.SUCCESS if count else self.style.NOTICE
            self.stdout.write(style(f"  {key}: {count}"))

        if report.vacuum_ran:
            self.stdout.write(self.style.SUCCESS("  VACUUM: انجام شد"))

        if report.errors:
            for err in report.errors:
                self.stdout.write(self.style.ERROR(f"  خطا: {err}"))

        after_mb = report.db_size_bytes / (1024 * 1024)
        before_mb = report.db_size_before_bytes / (1024 * 1024)
        saved_mb = max(0, before_mb - after_mb)
        self.stdout.write(
            self.style.SUCCESS(
                f"پایان — {report.total_deleted} رکورد حذف شد | "
                f"حجم: {before_mb:.2f} → {after_mb:.2f} MB"
                + (f" (کاهش {saved_mb:.2f} MB)" if saved_mb > 0.01 else "")
            )
        )
        if report.total_deleted and not report.vacuum_ran and vacuum:
            self.stdout.write(
                self.style.WARNING(
                    "  VACUUM اجرا نشد — فضای دیسک ممکن است تا اجرای بعدی آزاد نشود."
                )
            )

    def _dry_run_counts(self) -> dict[str, int]:
        from datetime import timedelta

        from django.conf import settings
        from django.contrib.admin.models import LogEntry
        from django.contrib.sessions.models import Session
        from django.utils import timezone

        from core.models import (
            ConsultationSlot,
            ContactMessage,
            EvaluationReportShare,
            EvaluationRequest,
        )

        retention = getattr(settings, "DB_RETENTION", {})
        now = timezone.now()

        def days(key: str, default: int) -> int:
            return max(0, int(retention.get(key, default)))

        counts = {}

        counts["sessions"] = Session.objects.filter(expire_date__lt=now).count()

        grace = days("expired_shares_grace_days", 7)
        counts["expired_report_shares"] = EvaluationReportShare.objects.filter(
            expires_at__lt=now - timedelta(days=grace)
        ).count()

        replied_days = days("contact_replied_days", 365)
        read_days = days("contact_read_days", 180)
        cm = 0
        if replied_days:
            cm += ContactMessage.objects.filter(
                status=ContactMessage.STATUS_REPLIED,
                created_at__lt=now - timedelta(days=replied_days),
            ).count()
        if read_days:
            cm += ContactMessage.objects.filter(
                status=ContactMessage.STATUS_READ,
                admin_seen_at__isnull=False,
                created_at__lt=now - timedelta(days=read_days),
            ).count()
        counts["contact_messages"] = cm

        consult_days = days("consultation_done_days", 365)
        if consult_days:
            from core.models import ConsultationRequest

            counts["consultation_done"] = ConsultationRequest.objects.filter(
                status=ConsultationRequest.STATUS_DONE,
                updated_at__lt=now - timedelta(days=consult_days),
            ).count()
        else:
            counts["consultation_done"] = 0

        lost_days = days("evaluation_lost_days", 365)
        if lost_days:
            counts["evaluation_lost"] = EvaluationRequest.objects.filter(
                status=EvaluationRequest.STATUS_LOST,
                updated_at__lt=now - timedelta(days=lost_days),
            ).count()
        else:
            counts["evaluation_lost"] = 0

        slot_days = days("past_slots_days", 90)
        if slot_days:
            cutoff_date = timezone.localdate() - timedelta(days=slot_days)
            counts["past_slots"] = (
                ConsultationSlot.objects.filter(
                    date__lt=cutoff_date,
                    consultation_requests__isnull=True,
                )
                .distinct()
                .count()
            )
        else:
            counts["past_slots"] = 0

        log_days = days("admin_log_days", 30)
        if log_days:
            counts["admin_logs"] = LogEntry.objects.filter(
                action_time__lt=now - timedelta(days=log_days)
            ).count()
        else:
            counts["admin_logs"] = 0

        from core.models import AdminChangeLog

        audit_days = days("audit_log_days", 30)
        if audit_days:
            counts["audit_logs"] = AdminChangeLog.objects.filter(
                created_at__lt=now - timedelta(days=audit_days)
            ).count()
        else:
            counts["audit_logs"] = 0

        return counts
