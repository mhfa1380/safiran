"""آمار تجمیعی «از کجا با ما آشنا شدید؟» — ارزیابی + مشاوره."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any

from django.db.models import Count, QuerySet
from django.utils import timezone

from core.referral_source import (
    REFERRAL_SOCIAL,
    REFERRAL_SOCIAL_CHOICES,
    REFERRAL_SOURCE_CHOICES,
)


def _parse_date_param(raw: str) -> datetime | None:
    raw = (raw or "").strip()
    if not raw:
        return None
    try:
        dt = datetime.strptime(raw, "%Y-%m-%d")
    except ValueError:
        return None
    if timezone.is_naive(dt):
        return timezone.make_aware(dt, timezone.get_current_timezone())
    return dt


def _filter_qs(qs: QuerySet, *, date_from: datetime | None, date_to: datetime | None) -> QuerySet:
    if date_from:
        qs = qs.filter(created_at__gte=date_from)
    if date_to:
        qs = qs.filter(created_at__lt=date_to)
    return qs


def _counts_by_field(qs: QuerySet, field: str) -> dict[str, int]:
    out: dict[str, int] = defaultdict(int)
    for row in qs.values(field).annotate(c=Count("id")):
        key = (row[field] or "").strip()
        out[key] += row["c"]
    return dict(out)


def build_referral_statistics(
    *,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> dict[str, Any]:
    from core.models import ConsultationRequest, EvaluationRequest

    eval_qs = _filter_qs(EvaluationRequest.objects.all(), date_from=date_from, date_to=date_to)
    consult_qs = _filter_qs(
        ConsultationRequest.objects.all(), date_from=date_from, date_to=date_to
    )

    eval_sources = _counts_by_field(eval_qs, "referral_source")
    consult_sources = _counts_by_field(consult_qs, "referral_source")

    eval_social = _counts_by_field(
        eval_qs.filter(referral_source=REFERRAL_SOCIAL), "referral_social_platform"
    )
    consult_social = _counts_by_field(
        consult_qs.filter(referral_source=REFERRAL_SOCIAL), "referral_social_platform"
    )

    eval_total = sum(eval_sources.values())
    consult_total = sum(consult_sources.values())
    total = eval_total + consult_total

    merged_sources: dict[str, int] = defaultdict(int)
    for d in (eval_sources, consult_sources):
        for k, v in d.items():
            merged_sources[k] += v

    no_source = merged_sources.get("", 0)

    source_rows: list[dict[str, Any]] = []
    for code, label in REFERRAL_SOURCE_CHOICES:
        count = merged_sources.get(code, 0)
        source_rows.append(
            {
                "code": code,
                "label": label,
                "count": count,
                "eval_count": eval_sources.get(code, 0),
                "consult_count": consult_sources.get(code, 0),
                "pct": round(count / total * 100, 1) if total else 0.0,
            }
        )

    merged_social: dict[str, int] = defaultdict(int)
    for d in (eval_social, consult_social):
        for k, v in d.items():
            merged_social[k] += v

    social_total = merged_sources.get(REFERRAL_SOCIAL, 0)
    social_rows: list[dict[str, Any]] = []
    for code, label in REFERRAL_SOCIAL_CHOICES:
        count = merged_social.get(code, 0)
        social_rows.append(
            {
                "code": code,
                "label": label,
                "count": count,
                "eval_count": eval_social.get(code, 0),
                "consult_count": consult_social.get(code, 0),
                "pct": round(count / social_total * 100, 1) if social_total else 0.0,
            }
        )

    social_unspecified = merged_social.get("", 0)

    return {
        "total": total,
        "eval_total": eval_total,
        "consult_total": consult_total,
        "with_source": total - no_source,
        "no_source": no_source,
        "sources": source_rows,
        "social_total": social_total,
        "social_unspecified": social_unspecified,
        "social": social_rows,
        "date_from": date_from,
        "date_to": date_to,
    }


def referral_stats_from_request(request) -> dict[str, Any]:
    """فیلتر اختیاری ?from=YYYY-MM-DD&to=YYYY-MM-DD (to غیرشمول)."""
    date_from = _parse_date_param(request.GET.get("from", ""))
    date_to = _parse_date_param(request.GET.get("to", ""))
    return build_referral_statistics(date_from=date_from, date_to=date_to)
