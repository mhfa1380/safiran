"""
بازخورد بخش‌های گزارش ارزیابی (لایک / دیسلایک) — یادگیری تدریجی پیشنهادها.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from .evaluation_learning import _field_signature, mark_learning_stale
from .models import EvaluationReportShare, EvaluationSectionFeedback

logger = logging.getLogger(__name__)

SECTION_FEEDBACK_CACHE_KEY = "eval_section_feedback_weights_v1"
SECTION_FEEDBACK_META_KEY = "eval_section_feedback_meta_v1"
SECTION_FEEDBACK_CACHE_SECONDS = 6 * 3600
SECTION_FEEDBACK_MIN_VOTES = 6
SECTION_FEEDBACK_MAX_ROWS = 2000

MAX_SECTION_COUNTRY_BOOST = 8.0
MAX_SECTION_MAJOR_BOOST = 7.0
MAX_SECTION_UNI_BOOST = 6.0

VALID_SECTIONS = frozenset(
    {
        "top_pick",
        "university",
        "scholarships",
        "insights",
        "countries",
        "pricing",
        "majors",
        "universities_alt",
        "language",
        "blogs",
    }
)


@dataclass
class SectionFeedbackWeights:
    sample_count: int = 0
    active: bool = False
    updated_at: str = ""
    field_country: dict[str, dict[str, float]] = field(default_factory=dict)
    field_major: dict[str, dict[str, float]] = field(default_factory=dict)
    field_uni: dict[str, dict[str, dict[str, float]]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "sample_count": self.sample_count,
            "active": self.active,
            "updated_at": self.updated_at,
            "field_country": self.field_country,
            "field_major": self.field_major,
            "field_uni": self.field_uni,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SectionFeedbackWeights:
        if not data:
            return cls()
        return cls(
            sample_count=int(data.get("sample_count", 0)),
            active=bool(data.get("active")),
            updated_at=str(data.get("updated_at", "")),
            field_country=dict(data.get("field_country") or {}),
            field_major=dict(data.get("field_major") or {}),
            field_uni={
                sig: {c: dict(u) for c, u in countries.items()}
                for sig, countries in (data.get("field_uni") or {}).items()
            },
        )


def _vote_key(section: str, item_key: str = "") -> str:
    section = (section or "").strip()
    item_key = (item_key or "").strip()
    return f"{section}:{item_key}" if item_key else section


def _parse_item_key(item_key: str) -> tuple[str, str]:
    raw = (item_key or "").strip()
    if ":" in raw:
        kind, value = raw.split(":", 1)
        return kind.strip().lower(), value.strip()
    return "", raw


def _targets_from_report(report: dict[str, Any]) -> dict[str, str]:
    top = (report or {}).get("top_pick") or {}
    country = ((top.get("country") or {}).get("code") or "").strip().lower()
    major = top.get("major") or {}
    uni = top.get("university") or {}
    return {
        "country": country,
        "major_slug": (major.get("slug") or "").strip(),
        "uni_slug": (uni.get("slug") or "").strip(),
    }


def _context_for_feedback(
    share: EvaluationReportShare,
    section: str,
    item_key: str,
) -> dict[str, str]:
    report = share.report if isinstance(share.report, dict) else {}
    targets = _targets_from_report(report)
    kind, value = _parse_item_key(item_key)
    ctx = dict(targets)
    if kind == "country" and value:
        ctx["country"] = value.lower()
    elif kind == "major" and value:
        ctx["major_slug"] = value
    elif kind == "university" and value:
        ctx["uni_slug"] = value
    elif kind == "course" and value:
        ctx["course_slug"] = value
    elif section == "top_pick":
        pass
    return {k: v for k, v in ctx.items() if v}


def get_feedback_map_for_share(share: EvaluationReportShare) -> dict[str, int]:
    rows = EvaluationSectionFeedback.objects.filter(share=share).only(
        "section", "item_key", "vote"
    )
    return {_vote_key(r.section, r.item_key): int(r.vote) for r in rows}


def build_feedback_context(share: EvaluationReportShare, request) -> dict[str, Any]:
    from django.urls import reverse

    return {
        "token": str(share.token),
        "url": reverse("evaluation_result_feedback", kwargs={"token": share.token}),
        "votes": get_feedback_map_for_share(share),
    }


@transaction.atomic
def save_section_feedback(
    share: EvaluationReportShare,
    *,
    section: str,
    vote: int,
    item_key: str = "",
) -> EvaluationSectionFeedback:
    section = (section or "").strip()[:32]
    if section not in VALID_SECTIONS:
        raise ValueError("invalid_section")
    if vote not in (1, -1):
        raise ValueError("invalid_vote")

    item_key = (item_key or "").strip()[:120]
    context = _context_for_feedback(share, section, item_key)
    weight = 1.0 if vote == 1 else -0.85

    row, _created = EvaluationSectionFeedback.objects.update_or_create(
        share=share,
        section=section,
        item_key=item_key,
        defaults={
            "evaluation_id": share.evaluation_id,
            "vote": vote,
            "weight": weight,
            "context": context,
        },
    )
    cache.delete(SECTION_FEEDBACK_CACHE_KEY)
    cache.delete(SECTION_FEEDBACK_META_KEY)
    mark_learning_stale()
    logger.info(
        "eval section feedback share=%s section=%s item=%s vote=%s",
        share.token,
        section,
        item_key or "-",
        vote,
    )
    return row


def _accumulate_boost(
    table: dict[str, dict[str, float]],
    sig: str,
    key: str,
    delta: float,
) -> None:
    if not sig or not key or not delta:
        return
    bucket = table.setdefault(sig, {})
    bucket[key] = bucket.get(key, 0.0) + delta


def _normalize_boosts(raw: dict[str, float], cap: float) -> dict[str, float]:
    if not raw:
        return {}
    out: dict[str, float] = {}
    for key, val in raw.items():
        scaled = max(-cap, min(cap, val))
        if abs(scaled) >= 0.35:
            out[key] = round(scaled, 2)
    return out


def build_section_feedback_weights(*, force: bool = False) -> SectionFeedbackWeights:
    if not force:
        cached = cache.get(SECTION_FEEDBACK_CACHE_KEY)
        if cached:
            return SectionFeedbackWeights.from_dict(cached)

    from .models import EvaluationRequest

    rows = (
        EvaluationSectionFeedback.objects.select_related("evaluation")
        .order_by("-updated_at")[:SECTION_FEEDBACK_MAX_ROWS]
    )

    field_country_raw: dict[str, dict[str, float]] = {}
    field_major_raw: dict[str, dict[str, float]] = {}
    field_uni_raw: dict[str, dict[str, dict[str, float]]] = {}
    sample_count = 0

    for fb in rows:
        ev = fb.evaluation
        if not ev:
            continue
        sig = _field_signature(ev)
        vote_w = float(fb.weight or (1.0 if fb.vote == 1 else -0.85))
        ctx = fb.context if isinstance(fb.context, dict) else {}
        country = (ctx.get("country") or "").strip().lower()
        major_slug = (ctx.get("major_slug") or "").strip()
        uni_slug = (ctx.get("uni_slug") or "").strip()

        sample_count += 1

        if fb.section == "countries" and country:
            _accumulate_boost(field_country_raw, sig, country, vote_w * 1.2)
        elif fb.section in ("top_pick", "university", "countries", "insights", "scholarships") and country:
            mult = {
                "top_pick": 1.5,
                "insights": 1.15,
                "scholarships": 0.95,
            }.get(fb.section, 1.0)
            _accumulate_boost(field_country_raw, sig, country, vote_w * mult)
        if fb.section in ("top_pick", "majors", "insights") and major_slug:
            mult = 1.4 if fb.section == "top_pick" else (1.1 if fb.section == "insights" else 1.0)
            _accumulate_boost(field_major_raw, sig, major_slug, vote_w * mult)
        if fb.section in ("top_pick", "university", "universities_alt", "insights") and uni_slug and country:
            mult = 1.3 if fb.section == "top_pick" else (1.05 if fb.section == "insights" else 1.0)
            by_country = field_uni_raw.setdefault(sig, {})
            uni_bucket = by_country.setdefault(country, {})
            uni_bucket[uni_slug] = uni_bucket.get(uni_slug, 0.0) + vote_w * mult

    sig_votes: dict[str, int] = {}
    for fb in rows:
        ev = fb.evaluation
        if ev:
            sig = _field_signature(ev)
            sig_votes[sig] = sig_votes.get(sig, 0) + 1

    def scale_table(
        raw: dict[str, dict[str, float]],
        cap: float,
    ) -> dict[str, dict[str, float]]:
        out: dict[str, dict[str, float]] = {}
        for sig, counts in raw.items():
            scale = min(1.0, sig_votes.get(sig, 0) / 8.0)
            normalized = _normalize_boosts(
                {k: v * scale for k, v in counts.items()},
                cap,
            )
            if normalized:
                out[sig] = normalized
        return out

    weights = SectionFeedbackWeights(
        sample_count=sample_count,
        active=sample_count >= SECTION_FEEDBACK_MIN_VOTES,
        updated_at=timezone.now().isoformat(),
        field_country=scale_table(field_country_raw, MAX_SECTION_COUNTRY_BOOST),
        field_major=scale_table(field_major_raw, MAX_SECTION_MAJOR_BOOST),
        field_uni={},
    )
    for sig, countries in field_uni_raw.items():
        scale = min(1.0, sig_votes.get(sig, 0) / 8.0)
        by_country: dict[str, dict[str, float]] = {}
        for country, uni_counts in countries.items():
            normed = _normalize_boosts(
                {k: v * scale for k, v in uni_counts.items()},
                MAX_SECTION_UNI_BOOST,
            )
            if normed:
                by_country[country] = normed
        if by_country:
            weights.field_uni[sig] = by_country
    payload = weights.to_dict()
    cache.set(SECTION_FEEDBACK_CACHE_KEY, payload, SECTION_FEEDBACK_CACHE_SECONDS)
    cache.set(
        SECTION_FEEDBACK_META_KEY,
        {"updated_at": weights.updated_at, "samples": sample_count},
        SECTION_FEEDBACK_CACHE_SECONDS,
    )
    return weights


def get_section_feedback_weights() -> SectionFeedbackWeights:
    cached = cache.get(SECTION_FEEDBACK_CACHE_KEY)
    if cached:
        return SectionFeedbackWeights.from_dict(cached)
    return build_section_feedback_weights()


def _gradual_scale(weights: SectionFeedbackWeights, sig: str) -> float:
    if not weights.active:
        return 0.0
    n = 0
    if sig in weights.field_country:
        n = max(n, len(weights.field_country.get(sig, {})))
    if sig in weights.field_major:
        n = max(n, len(weights.field_major.get(sig, {})))
    return min(1.0, weights.sample_count / 40.0) * min(1.0, max(n, 1) / 4.0)


def section_country_boost(profile, country_code: str) -> tuple[float, list[str]]:
    weights = get_section_feedback_weights()
    if not weights.active or not country_code:
        return 0.0, []
    sig = _field_signature(profile.eval_req)
    boost = (weights.field_country.get(sig) or {}).get(country_code, 0.0)
    boost *= _gradual_scale(weights, sig)
    reasons: list[str] = []
    if boost >= 1.0:
        reasons.append("بر اساس بازخورد مثبت کاربران با پروفایل مشابه")
    elif boost <= -1.0:
        reasons.append("بر اساس بازخورد منفی، این کشور برای پروفایل مشابه کمتر پیشنهاد می‌شود")
    elif boost <= -0.6:
        reasons.append("برخی کاربران مشابه این بخش را کمتر مفید دانسته‌اند")
    return boost, reasons


def section_major_boost(profile, major_slug: str) -> tuple[float, list[str]]:
    weights = get_section_feedback_weights()
    if not weights.active or not major_slug:
        return 0.0, []
    sig = _field_signature(profile.eval_req)
    boost = (weights.field_major.get(sig) or {}).get(major_slug, 0.0)
    boost *= _gradual_scale(weights, sig)
    reasons = []
    if boost >= 0.8:
        reasons.append("رشته‌ای که کاربران مشابه بیشتر پسندیده‌اند")
    return boost, reasons


def section_university_boost(
    profile,
    country_code: str,
    uni_slug: str,
) -> tuple[float, list[str]]:
    weights = get_section_feedback_weights()
    if not weights.active or not uni_slug or not country_code:
        return 0.0, []
    sig = _field_signature(profile.eval_req)
    boost = ((weights.field_uni.get(sig) or {}).get(country_code) or {}).get(uni_slug, 0.0)
    boost *= _gradual_scale(weights, sig)
    reasons = []
    if boost >= 0.7:
        reasons.append("دانشگاهی با بازخورد مثبت از کاربران مشابه")
    return boost, reasons
