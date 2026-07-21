"""
نگهداری و بهینه‌سازی دیتابیس — حذف داده غیرضروری، VACUUM، آمار حجم.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from django.conf import settings
from django.contrib.admin.models import LogEntry
from django.contrib.sessions.models import Session
from django.db import connection, transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


@dataclass
class CleanupReport:
    """خلاصه عملیات پاکسازی."""

    deleted: dict[str, int] = field(default_factory=dict)
    vacuum_ran: bool = False
    db_size_before_bytes: int = 0
    db_size_bytes: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def total_deleted(self) -> int:
        return sum(self.deleted.values())

    def to_dict(self) -> dict[str, Any]:
        return {
            "deleted": self.deleted,
            "total_deleted": self.total_deleted,
            "vacuum_ran": self.vacuum_ran,
            "db_size_before_mb": round(self.db_size_before_bytes / (1024 * 1024), 2),
            "db_size_mb": round(self.db_size_bytes / (1024 * 1024), 2),
            "size_saved_mb": round(
                max(0, self.db_size_before_bytes - self.db_size_bytes) / (1024 * 1024), 2
            ),
            "errors": self.errors,
        }


def _days(name: str, default: int) -> int:
    return max(0, int(getattr(settings, "DB_RETENTION", {}).get(name, default)))


def _cutoff(days: int):
    if days <= 0:
        return None
    return timezone.now() - timedelta(days=days)


def cleanup_expired_sessions() -> int:
    """حذف سشن‌های منقضی‌شده."""
    return Session.objects.filter(expire_date__lt=timezone.now()).delete()[0]


def cleanup_expired_report_shares() -> int:
    """لینک‌های نتیجه ارزیابی منقضی‌شده (+ مهلت اضافه)."""
    from core.models import EvaluationReportShare

    grace_days = _days("expired_shares_grace_days", 7)
    cutoff = timezone.now() - timedelta(days=grace_days)
    return EvaluationReportShare.objects.filter(expires_at__lt=cutoff).delete()[0]


def cleanup_old_contact_messages() -> int:
    """
    پیام تماس پاسخ‌داده‌شده یا خوانده‌شده قدیمی.
    پیام‌های خوانده‌نشده حذف نمی‌شوند.
    """
    from core.models import ContactMessage

    total = 0
    replied_days = _days("contact_replied_days", 365)
    read_days = _days("contact_read_days", 180)

    if replied_days > 0:
        cutoff = _cutoff(replied_days)
        total += ContactMessage.objects.filter(
            status=ContactMessage.STATUS_REPLIED,
            created_at__lt=cutoff,
        ).delete()[0]

    if read_days > 0:
        cutoff = _cutoff(read_days)
        total += ContactMessage.objects.filter(
            status=ContactMessage.STATUS_READ,
            admin_seen_at__isnull=False,
            created_at__lt=cutoff,
        ).delete()[0]

    return total


def cleanup_old_consultations() -> int:
    """
    رزروهای انجام‌شده قدیمی — رکورد نگه داشته نمی‌شود.
    درخواست‌های new/contacted و موارد اخیر حذف نمی‌شوند.
    """
    from core.models import ConsultationRequest

    days = _days("consultation_done_days", 365)
    cutoff = _cutoff(days)
    if not cutoff:
        return 0
    return ConsultationRequest.objects.filter(
        status=ConsultationRequest.STATUS_DONE,
        updated_at__lt=cutoff,
    ).delete()[0]


def cleanup_lost_evaluations() -> int:
    """پرونده ارزیابی منصرف/بسته — با لاگ‌های وابسته (CASCADE)."""
    from core.models import EvaluationRequest

    days = _days("evaluation_lost_days", 365)
    cutoff = _cutoff(days)
    if not cutoff:
        return 0
    return EvaluationRequest.objects.filter(
        status=EvaluationRequest.STATUS_LOST,
        updated_at__lt=cutoff,
    ).delete()[0]


def cleanup_past_consultation_slots() -> int:
    """زمان‌های گذشته بدون درخواست مرتبط (بعد از حذف رزروهای قدیمی)."""
    from core.models import ConsultationSlot

    days = _days("past_slots_days", 90)
    if days <= 0:
        return 0
    cutoff_date = timezone.localdate() - timedelta(days=days)
    return (
        ConsultationSlot.objects.filter(
            date__lt=cutoff_date,
            consultation_requests__isnull=True,
        )
        .distinct()
        .delete()[0]
    )


def cleanup_admin_log_entries() -> int:
    days = _days("admin_log_days", 30)
    cutoff = _cutoff(days)
    if not cutoff:
        return 0
    return LogEntry.objects.filter(action_time__lt=cutoff).delete()[0]


def cleanup_admin_change_logs() -> int:
    """حذف لاگ تغییرات ادمین قدیمی‌تر از مهلت نگهداری."""
    from core.models import AdminChangeLog

    days = _days("audit_log_days", 30)
    cutoff = _cutoff(days)
    if not cutoff:
        return 0
    return AdminChangeLog.objects.filter(created_at__lt=cutoff).delete()[0]


def run_sqlite_vacuum() -> bool:
    """
    آزاد کردن فضای دیسک پس از DELETE — بدون VACUUM حجم فایل کم نمی‌شود.
    اتصال‌های وب را می‌بندد تا قفل کوتاه‌تر و اختلال کمتر باشد (ترجیحاً ساعت ۳ بامداد).
    """
    if connection.vendor != "sqlite":
        return False
    try:
        from django.db import connections

        connections.close_all()
        with connection.cursor() as cursor:
            cursor.execute("PRAGMA wal_checkpoint(TRUNCATE);")
            cursor.execute("VACUUM;")
            cursor.execute("PRAGMA optimize;")
        connections.close_all()
        return True
    except Exception as exc:
        logger.warning("SQLite VACUUM failed: %s", exc)
        return False


def get_database_size_bytes() -> int:
    if connection.vendor == "sqlite":
        db_path = settings.DATABASES["default"].get("NAME")
        if db_path and os.path.exists(db_path):
            size = os.path.getsize(db_path)
            for suffix in ("-wal", "-shm"):
                wal = f"{db_path}{suffix}"
                if os.path.exists(wal):
                    size += os.path.getsize(wal)
            return size
    return 0


def run_database_maintenance(*, vacuum: bool | None = None) -> CleanupReport:
    """اجرای پاکسازی دوره‌ای."""
    report = CleanupReport()
    if not getattr(settings, "DB_MAINTENANCE_ENABLED", True):
        report.errors.append("DB_MAINTENANCE_ENABLED is off")
        return report

    report.db_size_before_bytes = get_database_size_bytes()

    steps: list[tuple[str, callable]] = [
        ("sessions", cleanup_expired_sessions),
        ("expired_report_shares", cleanup_expired_report_shares),
        ("contact_messages", cleanup_old_contact_messages),
        ("consultation_done", cleanup_old_consultations),
        ("evaluation_lost", cleanup_lost_evaluations),
        ("past_slots", cleanup_past_consultation_slots),
        ("admin_logs", cleanup_admin_log_entries),
        ("audit_logs", cleanup_admin_change_logs),
    ]

    try:
        with transaction.atomic():
            for key, func in steps:
                try:
                    report.deleted[key] = func()
                except Exception as exc:
                    logger.exception("cleanup step %s failed", key)
                    report.errors.append(f"{key}: {exc}")

        should_vacuum = vacuum if vacuum is not None else getattr(
            settings, "DB_MAINTENANCE_VACUUM", True
        )
        if should_vacuum and report.total_deleted > 0:
            report.vacuum_ran = run_sqlite_vacuum()
    finally:
        report.db_size_bytes = get_database_size_bytes()

    try:
        from core.evaluation_learning import build_adaptive_weights

        weights = build_adaptive_weights(force=True)
        report.deleted["eval_learning_rebuild"] = 1 if weights.active else 0
    except Exception as exc:
        logger.exception("evaluation learning rebuild failed")
        report.errors.append(f"eval_learning: {exc}")

    warn_mb = getattr(settings, "DB_SIZE_WARN_MB", 400)
    if report.db_size_bytes > warn_mb * 1024 * 1024:
        logger.warning(
            "Database size %.1f MB exceeds warn threshold %s MB",
            report.db_size_bytes / (1024 * 1024),
            warn_mb,
        )

    return report
