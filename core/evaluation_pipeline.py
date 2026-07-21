"""
پایپ‌لاین چندمرحله ارزیابی — پیشرفت در DB (مشترک بین workerهای گونیکورن).
"""
from __future__ import annotations

import contextvars
import hashlib
import logging
import random
import uuid
from datetime import timedelta
from typing import Any, Callable

from django.db import transaction
from django.utils import timezone

from .evaluation_engine import build_evaluation_report
from .evaluation_share import create_evaluation_share
from .models import EvaluationProcessingJob, EvaluationRequest

logger = logging.getLogger(__name__)

EVAL_JOB_TTL = 900
EVAL_JOB_LOCK_STALE = timedelta(minutes=12)

eval_async_submit_ctx: contextvars.ContextVar[bool] = contextvars.ContextVar(
    "eval_async_submit", default=False
)


def skip_sync_evaluation_snapshot() -> bool:
    """ثبت AJAX ارزیابی — اسنپ‌شات و اعلان در job پس‌زمینه ساخته می‌شود."""
    return eval_async_submit_ctx.get()

PIPELINE_STEPS: tuple[tuple[str, int, str], ...] = (
    ("validate", 8, "بررسی و اعتبارسنجی اطلاعات فرم"),
    ("profile", 18, "ساخت پروفایل تحصیلی و زبانی"),
    ("countries", 35, "تحلیل کشورها، رشته‌ها و دانشگاه‌ها"),
    ("scholarships", 52, "بررسی بورسیه‌ها و فاندها"),
    ("blogs", 68, "جستجو در وبلاگ و تجربیات موفق"),
    ("pricing", 82, "برآورد هزینه از تعرفه خدمات"),
    ("match", 94, "محاسبه درصد تطابق و اطمینان"),
    ("finalize", 100, "آماده‌سازی گزارش نهایی"),
)


def _initial_job_state() -> dict[str, Any]:
    return {
        "status": "running",
        "percent": 8,
        "step_id": "validate",
        "step_label": "بررسی و اعتبارسنجی اطلاعات فرم…",
        "redirect_url": "",
        "error": "",
        "ui_compact": False,
        "report_has_data": None,
        "queue_ahead_initial": 0,
        "queue_plan": [],
    }


def _queue_plan_delays(job_id: str, initial: int) -> list[int]:
    """فواصل تصادفی (ms) برای کم شدن صف — ثابت برای هر job."""
    if initial <= 0:
        return []
    seed = int(hashlib.sha256(str(job_id).encode()).hexdigest()[:12], 16)
    rng = random.Random(seed)
    budget = min(4800, 1100 + initial * 260 + rng.randint(0, 650))
    delays: list[int] = []
    remaining = budget
    for i in range(initial):
        left = initial - i
        if left == 1:
            delays.append(max(160, remaining))
            break
        chunk = rng.randint(200, max(260, remaining // left + 100))
        chunk = min(chunk, remaining - 140 * (left - 1))
        delays.append(chunk)
        remaining -= chunk
    return delays


def _compute_queue_ahead(row: EvaluationProcessingJob, state: dict[str, Any]) -> int:
    initial = int(state.get("queue_ahead_initial") or 0)
    if initial <= 0:
        return 0
    percent = int(state.get("percent") or 0)
    step_id = state.get("step_id") or "validate"
    if percent > 12 or step_id not in ("validate", ""):
        return 0
    if row.processing_lock and percent >= 8:
        return 0
    plan = state.get("queue_plan") or []
    if not plan:
        return 0
    elapsed_ms = (timezone.now() - row.created_at).total_seconds() * 1000
    ahead = initial
    for delay in plan:
        elapsed_ms -= delay
        if elapsed_ms < 0:
            break
        ahead -= 1
    return max(0, ahead)


def queue_ahead_initial_for_job(job_id: str) -> int:
    row = _job_row(job_id)
    if not row:
        return 0
    state = row.state or {}
    return int(state.get("queue_ahead_initial") or 0)


def _job_row(job_id: str) -> EvaluationProcessingJob | None:
    try:
        return EvaluationProcessingJob.objects.get(job_id=job_id)
    except (EvaluationProcessingJob.DoesNotExist, ValueError):
        return None


def _save_job_state(row: EvaluationProcessingJob, state: dict[str, Any]) -> None:
    row.state = state
    row.save(update_fields=["state", "updated_at"])


def create_evaluation_job(
    instance: EvaluationRequest,
    *,
    scholarship_target: str = "",
) -> str:
    job_id = uuid.uuid4()
    job_id_str = str(job_id)
    queue_initial = random.randint(0, 10)
    state = _initial_job_state()
    state["queue_ahead_initial"] = queue_initial
    state["queue_plan"] = _queue_plan_delays(job_id_str, queue_initial)
    EvaluationProcessingJob.objects.create(
        job_id=job_id,
        evaluation=instance,
        scholarship_target=scholarship_target or "",
        state=state,
    )
    return job_id_str


def get_job_state(job_id: str) -> dict[str, Any] | None:
    row = _job_row(job_id)
    if not row:
        return None
    state = dict(row.state or {})
    state["pk"] = row.evaluation_id
    state["scholarship_target"] = row.scholarship_target or ""
    return state


def update_job_progress(
    job_id: str,
    *,
    step_id: str,
    percent: int,
    step_label: str,
    status: str = "running",
    ui_compact: bool | None = None,
) -> None:
    row = _job_row(job_id)
    if not row:
        return
    state = dict(row.state or {})
    state["step_id"] = step_id
    state["percent"] = min(100, max(0, int(percent)))
    state["step_label"] = step_label
    state["status"] = status
    if ui_compact is not None:
        state["ui_compact"] = bool(ui_compact)
    _save_job_state(row, state)


def job_needs_processing(job_id: str) -> bool:
    """آیا worker دیگری باید تحلیل را شروع یا از سر بگیرد؟"""
    row = _job_row(job_id)
    if not row:
        return False
    state = row.state or {}
    if state.get("status") in ("done", "error"):
        return False
    if row.processing_lock and row.locked_at:
        if row.locked_at > timezone.now() - EVAL_JOB_LOCK_STALE:
            return False
    return state.get("status") == "running"


def _step_progress_callback(job_id: str) -> Callable[..., None]:
    def _cb(step_id: str, percent: int, label: str, **extra: Any) -> None:
        update_job_progress(
            job_id,
            step_id=step_id,
            percent=percent,
            step_label=label,
            **extra,
        )

    return _cb


def run_evaluation_pipeline(
    instance: EvaluationRequest,
    *,
    scholarship_target: str = "",
    job_id: str | None = None,
    progress_callback: Callable[[str, int, str], None] | None = None,
) -> dict[str, Any]:
    """اجرای تحلیل و ذخیره گزارش — با به‌روزرسانی پیشرفت."""
    cb = progress_callback
    if job_id and not cb:
        cb = _step_progress_callback(job_id)

    def tick(step_id: str, percent: int, label: str, **extra: Any) -> None:
        if cb:
            cb(step_id, percent, label, **extra)

    report = build_evaluation_report(
        instance,
        scholarship_target=scholarship_target,
        progress_callback=tick,
    )

    instance.recommendation_snapshot = report
    instance.save(update_fields=["recommendation_snapshot", "updated_at"])

    tick("finalize", 98, "ایجاد لینک اختصاصی نتیجه…")
    share = create_evaluation_share(instance, report)

    from django.urls import reverse

    redirect_url = reverse("evaluation_result", kwargs={"token": share.token})
    tick("finalize", 100, "در حال ساخت خروجی…")

    has_data = bool(report.get("has_data"))
    return {
        "status": "done",
        "percent": 100,
        "step_id": "done",
        "step_label": "در حال ساخت خروجی",
        "redirect_url": redirect_url,
        "error": "",
        "report_has_data": has_data,
        "ui_compact": not has_data,
    }


def _try_acquire_processing_lock(job_id: str) -> EvaluationProcessingJob | None:
    """قفل DB — فقط یک worker تحلیل را اجرا می‌کند."""
    now = timezone.now()
    stale_before = now - EVAL_JOB_LOCK_STALE
    with transaction.atomic():
        row = (
            EvaluationProcessingJob.objects.select_for_update()
            .filter(job_id=job_id)
            .first()
        )
        if not row:
            return None
        state = row.state or {}
        if state.get("status") in ("done", "error"):
            return None
        if row.processing_lock and row.locked_at and row.locked_at >= stale_before:
            return None
        row.processing_lock = True
        row.locked_at = now
        row.save(update_fields=["processing_lock", "locked_at", "updated_at"])
        return row


def _release_processing_lock(job_id: str) -> None:
    EvaluationProcessingJob.objects.filter(job_id=job_id).update(
        processing_lock=False,
        locked_at=None,
    )


def start_evaluation_job_async(job_id: str) -> None:
    """اجرای تحلیل در پس‌زمینه (Celery یا thread) تا polling پیشرفت واقعی ببیند."""
    from core.task_queue import enqueue_evaluation_job

    enqueue_evaluation_job(job_id)


def process_evaluation_job(job_id: str) -> dict[str, Any]:
    """اجرای job — فقط یک بار (قفل DB)."""
    state = get_job_state(job_id)
    if not state:
        return {"ok": False, "error": "job_not_found", "status": "error"}

    if state.get("status") in ("done", "error"):
        return {"ok": state.get("status") != "error", **state}

    row = _try_acquire_processing_lock(job_id)
    if not row:
        fresh = get_job_state(job_id) or state
        return {"ok": True, **fresh}

    state = dict(row.state or {})
    state["status"] = "running"
    state["step_id"] = "validate"
    state["percent"] = 8
    state["step_label"] = "بررسی و اعتبارسنجی اطلاعات فرم…"
    _save_job_state(row, state)

    try:
        instance = EvaluationRequest.objects.get(pk=row.evaluation_id)
        result = run_evaluation_pipeline(
            instance,
            scholarship_target=row.scholarship_target or "",
            job_id=job_id,
        )
        state.update(result)
        state["status"] = "done"
    except EvaluationRequest.DoesNotExist:
        state["status"] = "error"
        state["error"] = "پرونده یافت نشد. لطفاً فرم را دوباره ارسال کنید."
        state["percent"] = 0
    except Exception:
        logger.exception("Evaluation job failed job_id=%s", job_id)
        state["status"] = "error"
        state["error"] = "خطا در تحلیل. لطفاً چند لحظه بعد دوباره تلاش کنید."
        state["percent"] = 0
    finally:
        _release_processing_lock(job_id)

    row = _job_row(job_id)
    if row:
        _save_job_state(row, state)
    return {"ok": state.get("status") != "error", **state}


def read_evaluation_job(job_id: str) -> dict[str, Any]:
    """وضعیت job برای polling — بدون اجرای مجدد."""
    row = _job_row(job_id)
    if not row:
        return {"ok": False, "error": "job_not_found", "status": "error"}
    state = dict(row.state or {})
    queue_ahead = _compute_queue_ahead(row, state)
    payload = {k: v for k, v in state.items() if k not in ("pk", "scholarship_target", "queue_plan")}
    payload["queue_ahead"] = queue_ahead
    payload["queue_active"] = queue_ahead > 0
    payload["job_id"] = str(row.job_id)
    return {"ok": state.get("status") != "error", **payload}


def purge_stale_evaluation_jobs() -> int:
    """حذف jobهای قدیمی (نگهداری DB)."""
    cutoff = timezone.now() - timedelta(seconds=EVAL_JOB_TTL * 4)
    deleted, _ = EvaluationProcessingJob.objects.filter(updated_at__lt=cutoff).delete()
    return deleted
