"""
یادگیری تطبیقی موتور ارزیابی — وزن‌دهی پویا از پرونده‌های واقعی سایت.

هر بار فرم ارزیابی ثبت می‌شود یا وضعیت پرونده عوض می‌شود، آمار به‌روز می‌شود
و پیشنهادهای بعدی دقیق‌تر می‌شوند (بدون نیاز به مدل خارجی).
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from django.core.cache import cache
from django.utils import timezone

from .faq_search import _normalize_persian, tokenize_query
from .models import EvaluationRequest

logger = logging.getLogger(__name__)

LEARNING_CACHE_KEY = "eval_adaptive_weights_v1"
LEARNING_META_KEY = "eval_adaptive_meta_v1"
POPULAR_MAJORS_CACHE_KEY = "majors_popularity_v1"
LEARNING_CACHE_SECONDS = 6 * 3600
POPULAR_MAJORS_MIN_SAMPLES = 6
LEARNING_MIN_SAMPLES = 8
LEARNING_LOOKBACK_DAYS = 540
LEARNING_MAX_ROWS = 600
PENDING_COUNTER_KEY = "eval_learning_pending_count"

# حداکثر تقویت/تضعیف از یادگیری
MAX_COUNTRY_LEARN_BOOST = 14.0
MAX_MAJOR_LEARN_BOOST = 12.0
MAX_UNI_LEARN_BOOST = 10.0


def format_learning_sample_phrase(count: int) -> str:
    """برچسب تعداد پرونده برای نمایش عمومی — بدون عدد دقیق روزانه."""
    n = max(int(count or 0), 0)
    if n >= 1_000:
        thousands = n // 1_000
        return f"بیش از {thousands:,} هزار".replace(",", "٬")
    return "هزاران"


@dataclass
class AdaptiveWeights:
    """وزن‌های استخراج‌شده از پرونده‌های گذشته."""

    version: int = 1
    sample_count: int = 0
    weighted_samples: float = 0.0
    updated_at: str = ""
    active: bool = False
    # field_signature -> country_code -> boost
    field_country: dict[str, dict[str, float]] = field(default_factory=dict)
    degree_country: dict[str, dict[str, float]] = field(default_factory=dict)
    cluster_country: dict[str, dict[str, float]] = field(default_factory=dict)
    field_major: dict[str, dict[str, float]] = field(default_factory=dict)
    field_uni: dict[str, dict[str, dict[str, float]]] = field(default_factory=dict)
    top_country_global: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "sample_count": self.sample_count,
            "weighted_samples": round(self.weighted_samples, 2),
            "updated_at": self.updated_at,
            "active": self.active,
            "field_country": self.field_country,
            "degree_country": self.degree_country,
            "cluster_country": self.cluster_country,
            "field_major": self.field_major,
            "field_uni": self.field_uni,
            "top_country_global": self.top_country_global,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AdaptiveWeights:
        if not data:
            return cls()
        return cls(
            version=int(data.get("version", 1)),
            sample_count=int(data.get("sample_count", 0)),
            weighted_samples=float(data.get("weighted_samples", 0)),
            updated_at=str(data.get("updated_at", "")),
            active=bool(data.get("active")),
            field_country=dict(data.get("field_country") or {}),
            degree_country=dict(data.get("degree_country") or {}),
            cluster_country=dict(data.get("cluster_country") or {}),
            field_major=dict(data.get("field_major") or {}),
            field_uni=dict(data.get("field_uni") or {}),
            top_country_global=dict(data.get("top_country_global") or {}),
        )


def _gpa_band(eval_req: EvaluationRequest) -> str:
    from .evaluation_engine import parse_average_grade_detail

    gpa, uncertain, _ = parse_average_grade_detail(eval_req.average_grade or "")
    if gpa is None:
        return "u" if uncertain else "x"
    if gpa >= 17:
        return "h"
    if gpa >= 15:
        return "m"
    return "l"


def _lang_band(eval_req: EvaluationRequest) -> str:
    from .evaluation_engine import language_to_ielts_equiv, parse_language_score

    test_type = eval_req.language_test_type or EvaluationRequest.TEST_NONE
    raw = parse_language_score(eval_req.language_score or "")
    ielts = language_to_ielts_equiv(test_type, raw)
    if ielts is None:
        return "x"
    if ielts >= 7.0:
        return "h"
    if ielts >= 6.0:
        return "m"
    return "l"


def _field_signature(eval_req: EvaluationRequest) -> str:
    raw = " ".join(
        filter(
            None,
            [
                eval_req.field_of_study or "",
                eval_req.desired_major or "",
            ],
        )
    )
    tokens = tokenize_query(raw)
    if not tokens:
        core = "_general"
    else:
        core = "|".join(sorted(set(tokens))[:4])
    return f"{core}:{eval_req.current_degree or '_'}:gpa{_gpa_band(eval_req)}:lang{_lang_band(eval_req)}"


def _outcome_weight(eval_req: EvaluationRequest) -> float:
    """وزن نمونه بر اساس نتیجه پیگیری — پرونده‌های موفق اثر بیشتر."""
    w = 1.0
    if eval_req.status == EvaluationRequest.STATUS_COMPLETED:
        w = max(w, 2.6)
    elif eval_req.status == EvaluationRequest.STATUS_IN_PROGRESS:
        w = max(w, 1.5)
    elif eval_req.status == EvaluationRequest.STATUS_FOLLOW_UP:
        w = max(w, 1.25)
    elif eval_req.status == EvaluationRequest.STATUS_LOST:
        w = min(w, 0.35)

    cr = eval_req.contact_result or ""
    if cr == EvaluationRequest.CONTACT_CONVERTED:
        w = max(w, 3.2)
    elif cr == EvaluationRequest.CONTACT_ANSWERED:
        w = max(w, 1.9)
    elif cr in (EvaluationRequest.CONTACT_CALLBACK, EvaluationRequest.CONTACT_WHATSAPP):
        w = max(w, 1.15)
    elif cr in (EvaluationRequest.CONTACT_NO_ANSWER, EvaluationRequest.CONTACT_BUSY):
        w = min(w, 0.75)
    elif cr == EvaluationRequest.CONTACT_NOT_INTERESTED:
        w = min(w, 0.25)
    return w


def _extract_snapshot_targets(snap: dict[str, Any]) -> tuple[str, str, str]:
    if not snap or not snap.get("has_data"):
        return "", "", ""
    top = snap.get("top_pick") or {}
    country = ((top.get("country") or {}).get("code") or "").strip().lower()
    major = top.get("major") or {}
    uni = top.get("university") or {}
    major_slug = (major.get("slug") or "").strip()
    uni_slug = (uni.get("slug") or "").strip()
    if not country:
        c2 = (snap.get("countries") or [{}])[0]
        country = (c2.get("code") or "").strip().lower()
    return country, major_slug, uni_slug


def _accumulate(
    table: dict[str, dict[str, float]],
    key: str,
    country: str,
    weight: float,
) -> None:
    if not key or not country:
        return
    bucket = table.setdefault(key, {})
    bucket[country] = bucket.get(country, 0.0) + weight


def _boosts_from_counts(counts: dict[str, float], *, cap: float) -> dict[str, float]:
    if not counts:
        return {}
    total = sum(counts.values())
    if total <= 0:
        return {}
    n = len(counts)
    baseline = 1.0 / max(n, 1)
    out: dict[str, float] = {}
    for code, val in counts.items():
        share = val / total
        delta = share - baseline
        boost = max(-cap * 0.45, min(cap, delta * cap * 2.8))
        if abs(boost) >= 0.8:
            out[code] = round(boost, 2)
    return out


def _merge_boost_tables(tables: list[dict[str, float]], cap: float) -> dict[str, float]:
    merged: dict[str, float] = {}
    for tbl in tables:
        for code, b in tbl.items():
            merged[code] = merged.get(code, 0.0) + b
    return {k: round(max(-cap, min(cap, v)), 2) for k, v in merged.items() if abs(v) >= 0.6}


def build_adaptive_weights(*, force: bool = False) -> AdaptiveWeights:
    """بازسازی آمار یادگیری از پرونده‌های ارزیابی."""
    if not force:
        cached = cache.get(LEARNING_CACHE_KEY)
        if cached:
            return AdaptiveWeights.from_dict(cached)

    cutoff = timezone.now() - timedelta(days=LEARNING_LOOKBACK_DAYS)
    qs = (
        EvaluationRequest.objects.filter(created_at__gte=cutoff)
        .exclude(recommendation_snapshot__isnull=True)
        .order_by("-created_at")
        .only(
            "field_of_study",
            "desired_major",
            "current_degree",
            "target_country",
            "desired_countries",
            "status",
            "contact_result",
            "recommendation_snapshot",
        )[:LEARNING_MAX_ROWS]
    )

    field_country_raw: dict[str, dict[str, float]] = {}
    degree_country_raw: dict[str, dict[str, float]] = {}
    cluster_country_raw: dict[str, dict[str, float]] = {}
    field_major_raw: dict[str, dict[str, float]] = {}
    field_uni_raw: dict[str, dict[str, dict[str, float]]] = {}
    global_country: dict[str, float] = {}

    from .evaluation_engine import _detect_clusters

    sample_count = 0
    weighted_total = 0.0

    for ev in qs:
        snap = ev.recommendation_snapshot
        if not isinstance(snap, dict) or not snap.get("has_data"):
            continue
        country, major_slug, uni_slug = _extract_snapshot_targets(snap)
        if not country:
            continue

        w = _outcome_weight(ev)
        sample_count += 1
        weighted_total += w

        sig = _field_signature(ev)
        _accumulate(field_country_raw, sig, country, w)
        _accumulate(degree_country_raw, ev.current_degree or "_", country, w)
        _accumulate(global_country, "_all", country, w)

        study = _normalize_persian(
            f"{ev.field_of_study or ''} {ev.desired_major or ''}"
        )
        for cluster in _detect_clusters(study):
            _accumulate(cluster_country_raw, cluster, country, w)

        if major_slug:
            bucket = field_major_raw.setdefault(sig, {})
            bucket[major_slug] = bucket.get(major_slug, 0.0) + w

        if uni_slug and country:
            by_country = field_uni_raw.setdefault(sig, {})
            uni_bucket = by_country.setdefault(country, {})
            uni_bucket[uni_slug] = uni_bucket.get(uni_slug, 0.0) + w

    active = sample_count >= LEARNING_MIN_SAMPLES

    weights = AdaptiveWeights(
        sample_count=sample_count,
        weighted_samples=weighted_total,
        updated_at=timezone.now().isoformat(),
        active=active,
        field_country={
            sig: _boosts_from_counts(cnt, cap=MAX_COUNTRY_LEARN_BOOST)
            for sig, cnt in field_country_raw.items()
        },
        degree_country={
            deg: _boosts_from_counts(cnt, cap=MAX_COUNTRY_LEARN_BOOST)
            for deg, cnt in degree_country_raw.items()
        },
        cluster_country={
            cl: _boosts_from_counts(cnt, cap=MAX_COUNTRY_LEARN_BOOST * 0.85)
            for cl, cnt in cluster_country_raw.items()
        },
        field_major={
            sig: _boosts_from_counts(cnt, cap=MAX_MAJOR_LEARN_BOOST)
            for sig, cnt in field_major_raw.items()
        },
        field_uni={
            sig: {
                c: _boosts_from_counts(u, cap=MAX_UNI_LEARN_BOOST)
                for c, u in countries.items()
            }
            for sig, countries in field_uni_raw.items()
        },
        top_country_global=_boosts_from_counts(global_country.get("_all", {}), cap=6.0),
    )

    payload = weights.to_dict()
    cache.set(LEARNING_CACHE_KEY, payload, LEARNING_CACHE_SECONDS)
    cache.set(LEARNING_META_KEY, {"updated_at": weights.updated_at, "samples": sample_count}, LEARNING_CACHE_SECONDS)
    cache.delete(PENDING_COUNTER_KEY)
    logger.info(
        "Adaptive evaluation weights rebuilt: samples=%s active=%s",
        sample_count,
        active,
    )
    return weights


def get_adaptive_weights() -> AdaptiveWeights:
    pending = cache.get(PENDING_COUNTER_KEY) or 0
    cached = cache.get(LEARNING_CACHE_KEY)
    if cached and pending < 3:
        return AdaptiveWeights.from_dict(cached)
    return build_adaptive_weights(force=pending >= 3 or not cached)


def mark_learning_stale() -> None:
    try:
        cache.incr(PENDING_COUNTER_KEY)
    except ValueError:
        cache.set(PENDING_COUNTER_KEY, 1, LEARNING_CACHE_SECONDS)
    cache.delete(POPULAR_MAJORS_CACHE_KEY)


@dataclass
class PopularMajorRankings:
    """رتبه‌بندی رشته‌ها از خروجی موتور ارزیابی (پرونده‌های واقعی)."""

    sample_count: int = 0
    active: bool = False
    global_scores: dict[str, float] = field(default_factory=dict)
    by_country: dict[str, dict[str, float]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "sample_count": self.sample_count,
            "active": self.active,
            "global_scores": self.global_scores,
            "by_country": self.by_country,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PopularMajorRankings:
        if not data:
            return cls()
        return cls(
            sample_count=int(data.get("sample_count", 0)),
            active=bool(data.get("active")),
            global_scores=dict(data.get("global_scores") or {}),
            by_country={
                str(country): dict(scores or {})
                for country, scores in (data.get("by_country") or {}).items()
            },
        )


def _majors_from_snapshot(snap: dict[str, Any], weight: float) -> list[tuple[str, str, float]]:
    """استخراج (slug, country, امتیاز) از گزارش ارزیابی."""
    if not snap or not snap.get("has_data") or weight <= 0:
        return []
    hits: list[tuple[str, str, float]] = []

    top = snap.get("top_pick") or {}
    major = top.get("major") or {}
    slug = (major.get("slug") or "").strip()
    country = (major.get("country") or "").strip().lower()
    if not country:
        country = ((top.get("country") or {}).get("code") or "").strip().lower()
    if slug:
        hits.append((slug, country, 3.0 * weight))

    for index, item in enumerate(snap.get("majors") or []):
        if not isinstance(item, dict):
            continue
        sl = (item.get("slug") or "").strip()
        if not sl:
            continue
        c = (item.get("country") or "").strip().lower()
        mult = 2.0 if index == 0 else 1.35 * (0.88 ** index)
        hits.append((sl, c, mult * weight))

    return hits


def _accumulate_major_score(
    table: dict[str, float],
    slug: str,
    score: float,
) -> None:
    if slug and score > 0:
        table[slug] = table.get(slug, 0.0) + score


def build_popular_major_rankings(*, force: bool = False) -> PopularMajorRankings:
    """بازسازی رتبه پرطرفدار رشته‌ها از snapshotهای ارزیابی."""
    if not force:
        cached = cache.get(POPULAR_MAJORS_CACHE_KEY)
        if cached:
            return PopularMajorRankings.from_dict(cached)

    cutoff = timezone.now() - timedelta(days=LEARNING_LOOKBACK_DAYS)
    qs = (
        EvaluationRequest.objects.filter(created_at__gte=cutoff)
        .exclude(recommendation_snapshot__isnull=True)
        .order_by("-created_at")
        .only("status", "contact_result", "recommendation_snapshot")[:LEARNING_MAX_ROWS]
    )

    global_scores: dict[str, float] = {}
    by_country: dict[str, dict[str, float]] = {}
    sample_count = 0

    for ev in qs:
        snap = ev.recommendation_snapshot
        if not isinstance(snap, dict) or not snap.get("has_data"):
            continue
        weight = _outcome_weight(ev)
        majors = _majors_from_snapshot(snap, weight)
        if not majors:
            continue
        sample_count += 1
        for slug, country, score in majors:
            _accumulate_major_score(global_scores, slug, score)
            if country:
                _accumulate_major_score(by_country.setdefault(country, {}), slug, score)

    rankings = PopularMajorRankings(
        sample_count=sample_count,
        active=sample_count >= POPULAR_MAJORS_MIN_SAMPLES,
        global_scores={k: round(v, 3) for k, v in global_scores.items()},
        by_country={
            c: {k: round(v, 3) for k, v in scores.items()}
            for c, scores in by_country.items()
        },
    )
    cache.set(POPULAR_MAJORS_CACHE_KEY, rankings.to_dict(), LEARNING_CACHE_SECONDS)
    logger.info(
        "Popular major rankings rebuilt: samples=%s active=%s majors=%s",
        sample_count,
        rankings.active,
        len(global_scores),
    )
    return rankings


def get_popular_major_rankings() -> PopularMajorRankings:
    pending = cache.get(PENDING_COUNTER_KEY) or 0
    cached = cache.get(POPULAR_MAJORS_CACHE_KEY)
    if cached and pending < 3:
        return PopularMajorRankings.from_dict(cached)
    return build_popular_major_rankings(force=pending >= 3 or not cached)


def country_learning_boost(
    weights: AdaptiveWeights,
    profile,
    country_code: str,
) -> tuple[float, list[str]]:
    if not weights.active or not country_code:
        return 0.0, []

    ev = profile.eval_req
    sig = _field_signature(ev)
    parts: list[dict[str, float]] = [
        weights.field_country.get(sig, {}),
        weights.degree_country.get(ev.current_degree or "", {}),
        weights.top_country_global,
    ]
    for cluster in profile.clusters:
        parts.append(weights.cluster_country.get(cluster, {}))

    merged = _merge_boost_tables(parts, MAX_COUNTRY_LEARN_BOOST)
    boost = merged.get(country_code, 0.0)
    reasons: list[str] = []
    if boost >= 2.0:
        reasons.append(
            f"بر اساس {format_learning_sample_phrase(weights.sample_count)} پرونده مشابه اخیر، "
            "این کشور نتیجه بهتری داشته"
        )
    elif boost >= 0.8:
        reasons.append("هم‌خوان با روند پرونده‌های موفق مشابه شما")
    elif boost <= -2.0:
        reasons.append("در پرونده‌های مشابه، مقاصد دیگر نتیجه بهتری داشته‌اند")

    try:
        from .evaluation_section_feedback import section_country_boost

        fb_boost, fb_reasons = section_country_boost(profile, country_code)
        boost += fb_boost
        reasons.extend(fb_reasons)
    except Exception:
        pass

    return boost, reasons


def major_learning_boost(
    weights: AdaptiveWeights,
    profile,
    major_slug: str,
) -> tuple[float, list[str]]:
    if not weights.active or not major_slug:
        return 0.0, []
    sig = _field_signature(profile.eval_req)
    tbl = weights.field_major.get(sig, {})
    boost = tbl.get(major_slug, 0.0)
    reasons = []
    if boost >= 1.5:
        reasons.append("این رشته در پرونده‌های موفق مشابه شما تکرار شده")
    try:
        from .evaluation_section_feedback import section_major_boost

        fb_boost, fb_reasons = section_major_boost(profile, major_slug)
        boost += fb_boost
        reasons.extend(fb_reasons)
    except Exception:
        pass
    return boost, reasons


def university_learning_boost(
    weights: AdaptiveWeights,
    profile,
    country_code: str,
    uni_slug: str,
) -> tuple[float, list[str]]:
    if not weights.active or not uni_slug or not country_code:
        return 0.0, []
    sig = _field_signature(profile.eval_req)
    tbl = (weights.field_uni.get(sig) or {}).get(country_code, {})
    boost = tbl.get(uni_slug, 0.0)
    reasons = []
    if boost >= 1.2:
        reasons.append("دانشگاهی که پرونده‌های مشابه به آن هدایت شده‌اند")
    try:
        from .evaluation_section_feedback import section_university_boost

        fb_boost, fb_reasons = section_university_boost(profile, country_code, uni_slug)
        boost += fb_boost
        reasons.extend(fb_reasons)
    except Exception:
        pass
    return boost, reasons


def learning_report_meta(weights: AdaptiveWeights) -> dict[str, Any]:
    label = format_learning_sample_phrase(weights.sample_count)
    return {
        "active": weights.active,
        "sample_count": weights.sample_count,
        "sample_label": label,
        "weighted_samples": round(weights.weighted_samples, 1),
        "updated_at": weights.updated_at[:10] if weights.updated_at else "",
    }


def learning_insight(weights: AdaptiveWeights) -> str | None:
    if not weights.active:
        return None
    label = format_learning_sample_phrase(weights.sample_count)
    return (
        f"پیشنهاد این گزارش با یادگیری از {label} پرونده ارزیابی "
        f"اخیر سایت تنظیم شده و روزبه‌روز دقیق‌تر می‌شود."
    )
