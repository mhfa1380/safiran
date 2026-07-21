"""
تنظیمات و ابزارهای SQLite برای کاهش «database is locked» و خطای 5xx هنگام خزیدن همزمان.
"""
from __future__ import annotations

import logging
import random
import time
from typing import TYPE_CHECKING

from django.conf import settings
from django.db import connections

if TYPE_CHECKING:
    from django.db.backends.base.base import BaseDatabaseWrapper

logger = logging.getLogger(__name__)

_RETRYABLE_TOKENS = (
    "database is locked",
    "database table is locked",
    "database schema is locked",
    "sqlite_busy",
    "sqlite_locked",
    "disk i/o error",
    "cannot commit",
    "cannot start a transaction",
    "locked",
    "busy",
)


def uses_sqlite() -> bool:
    return connections["default"].settings_dict["ENGINE"] == "django.db.backends.sqlite3"


def busy_timeout_ms() -> int:
    return int(getattr(settings, "DB_SQLITE_BUSY_TIMEOUT_MS", 60_000))


def retry_attempts() -> int:
    return int(getattr(settings, "DB_SQLITE_RETRY_ATTEMPTS", 8))


def retry_base_delay() -> float:
    return float(getattr(settings, "DB_SQLITE_RETRY_BASE_DELAY", 0.05))


def retry_max_delay() -> float:
    return float(getattr(settings, "DB_SQLITE_RETRY_MAX_DELAY", 1.5))


def is_retryable_db_error(exc: BaseException) -> bool:
    message = str(exc).lower()
    return any(token in message for token in _RETRYABLE_TOKENS)


def close_all_connections() -> None:
    connections.close_all()


def configure_sqlite_connection(connection: BaseDatabaseWrapper) -> None:
    """PRAGMAهای توصیه‌شده برای WAL + خواندن/نوشتن همزمان."""
    if connection.vendor != "sqlite":
        return
    timeout_ms = busy_timeout_ms()
    with connection.cursor() as cursor:
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA synchronous=NORMAL;")
        cursor.execute("PRAGMA foreign_keys=ON;")
        cursor.execute(f"PRAGMA busy_timeout={timeout_ms};")
        cursor.execute("PRAGMA cache_size=-16000;")
        cursor.execute("PRAGMA temp_store=MEMORY;")
        cursor.execute("PRAGMA mmap_size=268435456;")
        cursor.execute("PRAGMA wal_autocheckpoint=1000;")
        cursor.execute("PRAGMA locking_mode=NORMAL;")


def retry_delay_before_attempt(attempt: int) -> float:
    """تأخیر نمایی با jitter کوچک — attempt از ۰ شروع می‌شود."""
    base = retry_base_delay()
    delay = min(retry_max_delay(), base * (2**attempt))
    jitter = random.uniform(0, base)
    return delay + jitter


def run_with_sqlite_retry(
    callback,
    *,
    attempts: int | None = None,
    operation: str = "db",
):
    """
    اجرای callback با تلاش مجدد روی قفل SQLite.
    برای seed و نوشتن‌های دسته‌ای.
    """
    max_attempts = attempts if attempts is not None else retry_attempts()
    last_exc: BaseException | None = None
    for attempt in range(max_attempts):
        try:
            return callback()
        except Exception as exc:
            last_exc = exc
            if not is_retryable_db_error(exc) or attempt >= max_attempts - 1:
                raise
            close_all_connections()
            delay = retry_delay_before_attempt(attempt)
            logger.warning(
                "SQLite busy during %s, retry %s/%s in %.2fs: %s",
                operation,
                attempt + 1,
                max_attempts,
                delay,
                exc,
            )
            time.sleep(delay)
    if last_exc:
        raise last_exc
    raise RuntimeError(f"SQLite retry failed for {operation}")
