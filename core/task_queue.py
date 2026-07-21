"""صف کار پس‌زمینه — Celery در production، نخ daemon در توسعه."""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from typing import Any

from django.conf import settings

logger = logging.getLogger(__name__)


def celery_enabled() -> bool:
    return bool(getattr(settings, "CELERY_ENABLED", False))


def _thread(name: str, target: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
    threading.Thread(
        target=target,
        args=args,
        kwargs=kwargs,
        daemon=True,
        name=name,
    ).start()


def enqueue_evaluation_job(job_id: str) -> None:
    if celery_enabled():
        from core.tasks import evaluation_job_task

        evaluation_job_task.delay(job_id)
        return

    from core.evaluation_pipeline import process_evaluation_job

    _thread(f"eval-job-{job_id[:8]}", process_evaluation_job, job_id)


def enqueue_mhfa_footer_refresh(key: str) -> None:
    if celery_enabled():
        from core.tasks import mhfa_footer_refresh_task

        mhfa_footer_refresh_task.delay(key)
        return

    from core.mhfa_live import _footer_refresh_job

    _thread(f"mhfa-footer-{key[:12]}", _footer_refresh_job, key)


def enqueue_bale_text(text: str, *, blog: bool = False) -> None:
    if celery_enabled():
        from core.tasks import bale_text_task

        bale_text_task.delay(text, blog=blog)
        return

    from core.bale_notifier import send_bale_blog_text_if_configured, send_bale_text_if_configured

    sender = send_bale_blog_text_if_configured if blog else send_bale_text_if_configured
    _thread("bale-notify", sender, text)


def enqueue_mhfa_inbox(payload: dict[str, Any]) -> None:
    if celery_enabled():
        from core.tasks import mhfa_inbox_task

        mhfa_inbox_task.delay(payload)
        return

    from core.mhfa_live import deliver_inbox_event

    _thread("mhfa-inbox", deliver_inbox_event, payload)
