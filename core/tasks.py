"""وظایف پس‌زمینه Celery — با CELERY_ENABLED=0 از task_queue در نخ اجرا می‌شوند."""

from __future__ import annotations

from celery import shared_task


@shared_task(name="safiran.evaluation_job", ignore_result=True)
def evaluation_job_task(job_id: str) -> None:
    from core.evaluation_pipeline import process_evaluation_job

    process_evaluation_job(job_id)


@shared_task(name="safiran.mhfa_footer_refresh", ignore_result=True)
def mhfa_footer_refresh_task(key: str = "default") -> None:
    from core.mhfa_live import _footer_refresh_job

    _footer_refresh_job(key)


@shared_task(name="safiran.bale_text", ignore_result=True)
def bale_text_task(text: str, *, blog: bool = False) -> None:
    from core.bale_notifier import send_bale_blog_text_if_configured, send_bale_text_if_configured

    if blog:
        send_bale_blog_text_if_configured(text)
    else:
        send_bale_text_if_configured(text)


@shared_task(name="safiran.mhfa_inbox", ignore_result=True)
def mhfa_inbox_task(payload: dict) -> None:
    from core.mhfa_live import deliver_inbox_event

    deliver_inbox_event(payload)
