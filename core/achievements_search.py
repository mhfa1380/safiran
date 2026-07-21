"""
جستجو و پیشنهاد هوشمند دستاوردهای ماه — یافتن تجربه‌های مشابه (کشور، مقطع، مسیر).
"""

from __future__ import annotations

import math
import re
from datetime import datetime
from typing import Iterable

from django.db.models import Q, QuerySet
from django.utils import timezone

from .faq_search import (
    _expand_tokens,
    _fuzzy_ratio,
    _normalize_persian,
    _normalize_query,
    _token_matches,
    tokenize_query,
)
from .models import MonthlyAchievement


def _created_at_sort_key(dt: datetime | None) -> float:
    """کلید عددی برای مرتب‌سازی نزولی بر اساس تاریخ (datetime منفی ندارد)."""
    if dt is None:
        return 0.0
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt)
    return -dt.timestamp()


_EXTRA_SYNONYM_GROUPS: tuple[frozenset[str], ...] = (
    frozenset({"کانادا", "canada", "تورنتو", "ونکوور", "مونترال"}),
    frozenset({"آلمان", "germany", "برلین", "مونیخ"}),
    frozenset({"چین", "china", "پکن", "شانگهای"}),
    frozenset({"اسپانیا", "spain", "بارسلونا", "مادرید"}),
    frozenset({"ویزا", "visa", "سفارت", "embassy", "اقامت"}),
    frozenset({"بورسیه", "اسکالرشیپ", "scholarship", "فاند"}),
    frozenset({"کارشناسی", "لیسانس", "bachelor", "undergraduate"}),
    frozenset({"ارشد", "کارشناسی ارشد", "master", "mba", "ام‌بی‌ای"}),
    frozenset({"دکتری", "phd", "دکترا"}),
    frozenset({"کالج", "college", "co-op", "کوآپ"}),
    frozenset({"پذیرش", "اپلای", "apply", "admission"}),
    frozenset({"پرستاری", "nursing", "معماری", "architecture", "نرم‌افزار", "software"}),
)


def _expand_achievement_tokens(tokens: list[str]) -> list[str]:
    expanded = _expand_tokens(tokens)
    seen = set(expanded)
    for token in list(tokens):
        for group in _EXTRA_SYNONYM_GROUPS:
            if token in group:
                for word in group:
                    if word not in seen:
                        seen.add(word)
                        expanded.append(word)
    return expanded


def _achievement_haystack(item: MonthlyAchievement) -> str:
    parts = [
        item.person_name,
        item.person_role,
        item.title,
        item.description,
        item.detail_content,
        item.month_label,
        item.search_keywords,
    ]
    return _normalize_persian(" ".join(p for p in parts if p)).lower()


def _score_achievement(item: MonthlyAchievement, tokens: list[str], full_q: str) -> float:
    if not tokens and not full_q:
        return 0.0

    title = _normalize_persian(item.title or "").lower()
    role = _normalize_persian(item.person_role or "").lower()
    name = _normalize_persian(item.person_name or "").lower()
    haystack = _achievement_haystack(item)

    score = 0.0
    full_lower = _normalize_query(full_q).lower()

    if full_lower:
        if full_lower in role:
            score += 16.0
        elif full_lower in title:
            score += 14.0
        elif full_lower in name:
            score += 12.0
        elif full_lower in haystack:
            score += 8.0
        else:
            for part in (role, title, name):
                ratio = _fuzzy_ratio(full_lower, part)
                if ratio >= 0.55:
                    score += ratio * 9.0
                    break

    expanded = _expand_achievement_tokens(tokens)
    matched = 0
    for token in expanded:
        if _token_matches(role, token) >= 0.78:
            score += 6.0
            matched += 1
        elif _token_matches(title, token) >= 0.78:
            score += 5.0
            matched += 1
        elif _token_matches(name, token) >= 0.78:
            score += 3.5
            matched += 1
        elif _token_matches(haystack, token) >= 0.72:
            score += 2.2
            matched += 1
        elif _token_matches(haystack, token) >= 0.55:
            score += 0.6

    if tokens and matched == len(tokens):
        score += 4.0
    elif tokens and matched > 0:
        score += matched * 0.6

    if item.is_featured:
        score += 1.5
    if item.view_count:
        score += min(2.0, math.log1p(item.view_count))

    return score


def active_achievement_queryset() -> QuerySet:
    return MonthlyAchievement.objects.filter(is_active=True)


def _candidates(*, month_label: str = "") -> list[MonthlyAchievement]:
    qs = active_achievement_queryset()
    if month_label:
        qs = qs.filter(month_label=month_label)
    return list(qs[:300])


def filter_achievements(
    queryset: QuerySet | None = None,
    *,
    q: str = "",
    month_label: str = "",
) -> QuerySet:
    qs = queryset if queryset is not None else active_achievement_queryset()
    if month_label:
        qs = qs.filter(month_label=month_label)
    q = _normalize_query(q)
    if q:
        expanded = _expand_achievement_tokens(tokenize_query(q))
        token_q = Q()
        for token in expanded[:12]:
            token_q |= (
                Q(person_name__icontains=token)
                | Q(title__icontains=token)
                | Q(description__icontains=token)
                | Q(person_role__icontains=token)
                | Q(search_keywords__icontains=token)
            )
        qs = qs.filter(
            Q(person_name__icontains=q)
            | Q(title__icontains=q)
            | Q(person_role__icontains=q)
            | token_q
        )
    return qs.order_by("-is_featured", "order", "-created_at")


def rank_achievements(
    items: Iterable[MonthlyAchievement],
    q: str,
    *,
    limit: int = 12,
) -> list[tuple[MonthlyAchievement, float]]:
    q = _normalize_query(q)
    tokens = tokenize_query(q)
    if not q:
        ranked = []
        for item in items:
            score = (2.0 if item.is_featured else 0.0) + min(2.5, math.log1p(item.view_count))
            ranked.append((item, score))
        ranked.sort(key=lambda x: (-x[1], x[0].order, _created_at_sort_key(x[0].created_at)))
        return ranked[:limit]

    scored = [(_score_achievement(item, tokens, q), item) for item in items]
    scored = [(s, i) for s, i in scored if s > 0]
    scored.sort(key=lambda x: (-x[0], x[1].order, _created_at_sort_key(x[1].created_at)))
    return [(i, s) for s, i in scored[:limit]]


def smart_search_achievements(
    q: str = "",
    *,
    month_label: str = "",
    limit: int = 24,
    min_score: float = 2.0,
) -> list[MonthlyAchievement]:
    items = _candidates(month_label=month_label)
    q = _normalize_query(q)
    if not q:
        return [i for i, _ in rank_achievements(items, "", limit=limit)]

    ranked = rank_achievements(items, q, limit=max(limit, 40))
    results = [i for i, s in ranked if s >= min_score]
    if not results and ranked:
        results = [i for i, _ in ranked[: min(5, len(ranked))]]
    return results[:limit]


def suggest_achievements(
    q: str = "",
    *,
    month_label: str = "",
    limit: int = 8,
) -> list[MonthlyAchievement]:
    q = _normalize_query(q)
    if not q or len(q) < 2:
        items = _candidates(month_label=month_label)
        featured = [i for i in items if i.is_featured]
        if featured:
            featured.sort(key=lambda x: (-x.view_count, x.order))
            return featured[:limit]
        items.sort(key=lambda x: (-x.view_count, x.order))
        return items[:limit]
    return smart_search_achievements(q, month_label=month_label, limit=limit, min_score=1.5)


def split_search_results(
    q: str,
    *,
    month_label: str = "",
    primary_limit: int = 1,
    related_limit: int = 5,
    min_score: float = 2.0,
) -> tuple[list[MonthlyAchievement], list[MonthlyAchievement], str | None]:
    q = _normalize_query(q)
    if not q:
        return [], [], None

    items = _candidates(month_label=month_label)
    ranked = rank_achievements(items, q, limit=primary_limit + related_limit + 8)
    ranked = [(i, s) for i, s in ranked if s >= min_score]

    if not ranked:
        related = related_for_query(q, month_label=month_label, limit=related_limit)
        return [], related, None

    primary = [i for i, _ in ranked[:primary_limit]]
    primary_ids = {i.id for i in primary}
    related = [i for i, _ in ranked[primary_limit : primary_limit + related_limit] if i.id not in primary_ids]

    if len(related) < related_limit:
        for i in related_for_query(q, month_label=month_label, limit=related_limit + 3):
            if i.id in primary_ids or any(r.id == i.id for r in related):
                continue
            related.append(i)
            if len(related) >= related_limit:
                break

    best_slug = primary[0].slug if primary else None
    return primary, related, best_slug


def related_for_query(
    q: str,
    *,
    month_label: str = "",
    limit: int = 5,
) -> list[MonthlyAchievement]:
    items = smart_search_achievements(q, month_label=month_label, limit=limit, min_score=1.0)
    if items:
        return items
    return list(_candidates(month_label=month_label)[:limit])


def related_achievements(item: MonthlyAchievement, *, limit: int = 4) -> list[MonthlyAchievement]:
    """تجربه‌های مشابه بر اساس مقصد، عنوان و کلمات کلیدی."""
    seed = " ".join(
        filter(
            None,
            [item.person_role, item.title, item.search_keywords, item.person_name],
        )
    )
    qs = active_achievement_queryset().exclude(pk=item.pk)
    ranked = rank_achievements(list(qs[:80]), seed, limit=limit + 2)
    results = [i for i, _ in ranked if i.pk != item.pk]
    if len(results) >= limit:
        return results[:limit]

    same_month = list(
        qs.filter(month_label=item.month_label).order_by("order", "-created_at")[:limit]
    )
    for other in same_month:
        if other.pk not in {r.pk for r in results}:
            results.append(other)
        if len(results) >= limit:
            break
    return results[:limit]
