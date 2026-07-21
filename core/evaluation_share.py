"""لینک اشتراک‌گذاری و انقضای نتایج ارزیابی."""
from __future__ import annotations

import uuid
from datetime import timedelta

from django.urls import reverse
from django.utils import timezone

from .evaluation_engine import build_evaluation_report
from .models import EvaluationReportShare, EvaluationRequest

SHARE_TTL = timedelta(days=EvaluationReportShare.SHARE_TTL_DAYS)


def purge_expired_evaluation_shares() -> int:
    deleted, _ = EvaluationReportShare.objects.filter(
        expires_at__lte=timezone.now()
    ).delete()
    return deleted


def create_evaluation_share(
    evaluation: EvaluationRequest,
    report: dict | None = None,
) -> EvaluationReportShare:
    purge_expired_evaluation_shares()
    if report is None:
        report = build_evaluation_report(evaluation)
    now = timezone.now()
    return EvaluationReportShare.objects.create(
        evaluation=evaluation,
        token=uuid.uuid4(),
        report=report,
        expires_at=now + SHARE_TTL,
    )


def get_valid_evaluation_share(token) -> EvaluationReportShare | None:
    """لینک معتبر — بدون purge سنگین روی هر بازدید."""
    try:
        share = EvaluationReportShare.objects.select_related("evaluation").get(
            token=token
        )
    except (EvaluationReportShare.DoesNotExist, ValueError):
        return None
    if share.is_expired:
        share.delete()
        return None
    return share


def build_share_absolute_url(request, share: EvaluationReportShare) -> str:
    path = reverse("evaluation_result", kwargs={"token": share.token})
    return request.build_absolute_uri(path)


def get_active_evaluation_share(
    evaluation: EvaluationRequest,
) -> EvaluationReportShare | None:
    """آخرین لینک معتبر نتیجه برای یک پرونده."""
    now = timezone.now()
    return (
        evaluation.report_shares.filter(expires_at__gt=now)
        .order_by("-created_at")
        .first()
    )


def ensure_evaluation_share(evaluation: EvaluationRequest) -> EvaluationReportShare:
    """لینک فعال نتیجه — در صورت انقضا لینک تازه می‌سازد."""
    share = get_active_evaluation_share(evaluation)
    if share:
        return share
    return create_evaluation_share(evaluation)
