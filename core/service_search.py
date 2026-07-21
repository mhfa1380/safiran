"""
جستجو و پیشنهاد هوشمند خدمات موسسه.
"""
import difflib
import math
import re
from typing import Iterable

from django.db.models import Q, QuerySet

from .faq_search import (
    _ARABIC_TO_PERSIAN,
    _PERSIAN_STOP,
    _SYNONYM_GROUPS,
    _expand_tokens,
    _fuzzy_ratio,
    _normalize_persian,
    _normalize_query,
    _token_matches,
    tokenize_query,
)
from .models import Service

_SERVICE_SYNONYMS: tuple[frozenset[str], ...] = _SYNONYM_GROUPS + (
    frozenset({"خدمت", "خدمات", "service", "پکیج", "پشتیبانی"}),
    frozenset({"اپلای", "apply", "application", "پذیرش", "ثبت نام"}),
    frozenset({"انگیزه", "sop", "motivation", "رزومه", "cv"}),
    frozenset({"اسکان", "اقامت", "خوابگاه", "سکونت"}),
)


def _expand_service_tokens(tokens: list[str]) -> list[str]:
    expanded: list[str] = []
    seen: set[str] = set()
    for token in tokens:
        if token not in seen:
            seen.add(token)
            expanded.append(token)
        for group in _SERVICE_SYNONYMS:
            if token in group:
                for word in group:
                    if word not in seen:
                        seen.add(word)
                        expanded.append(word)
    return expanded


def _score_service(service: Service, tokens: list[str], full_q: str) -> float:
    if not tokens and not full_q:
        return 0.0

    title = _normalize_persian(service.title or "").lower()
    summary = _normalize_persian(service.get_display_summary()).lower()
    description = _normalize_persian(service.description or "").lower()
    highlights = _normalize_persian(service.highlights or "").lower()
    keywords_raw = " ".join(service.get_keywords_list())
    keywords = _normalize_persian(keywords_raw).lower()
    haystack = f"{title} {keywords} {summary} {description} {highlights}"

    score = 0.0
    full_lower = _normalize_query(full_q).lower()

    if full_lower:
        if full_lower in title:
            score += 15.0
        elif full_lower in keywords:
            score += 10.0
        elif full_lower in haystack:
            score += 7.0
        else:
            q_ratio = _fuzzy_ratio(full_lower, title)
            if q_ratio >= 0.55:
                score += q_ratio * 8.0

    expanded = _expand_service_tokens(tokens)
    matched_tokens = 0
    for token in expanded:
        t_score = _token_matches(title, token)
        if t_score >= 0.78:
            score += 5.0 * t_score
            matched_tokens += 1
        elif _token_matches(keywords, token) >= 0.78:
            score += 3.5
            matched_tokens += 1
        elif _token_matches(summary, token) >= 0.78 or _token_matches(description, token) >= 0.78:
            score += 2.0
            matched_tokens += 1
        elif _token_matches(haystack, token) >= 0.65:
            score += 0.8

    if tokens and matched_tokens == len(tokens):
        score += 3.0
    elif tokens and matched_tokens > 0:
        score += matched_tokens * 0.5

    if service.category and tokens:
        cat_name = _normalize_persian(service.category.name).lower()
        for token in tokens:
            if token in cat_name:
                score += 1.5

    if service.is_featured:
        score += 1.2
    if service.view_count:
        score += min(2.5, math.log1p(service.view_count))

    return score


_SERVICE_LIST_FIELDS = (
    "id",
    "title",
    "slug",
    "short_description",
    "description",
    "highlights",
    "icon",
    "search_keywords",
    "order",
    "is_active",
    "is_featured",
    "view_count",
    "category_id",
)


def active_service_queryset() -> QuerySet:
    return (
        Service.objects.filter(is_active=True)
        .select_related("category")
        .only(*_SERVICE_LIST_FIELDS, "category__id", "category__name", "category__slug", "category__order", "category__is_active")
    )


def _service_candidates(*, category_slug: str = "") -> list[Service]:
    qs = active_service_queryset()
    if category_slug:
        qs = qs.filter(category__slug=category_slug, category__is_active=True)
    return list(qs[:500])


def filter_services(
    queryset: QuerySet | None = None,
    *,
    q: str = "",
    category_slug: str = "",
) -> QuerySet:
    qs = queryset if queryset is not None else active_service_queryset()
    if category_slug:
        qs = qs.filter(category__slug=category_slug, category__is_active=True)
    q = _normalize_query(q)
    if q:
        expanded = _expand_service_tokens(tokenize_query(q))
        token_q = Q()
        for token in expanded[:12]:
            token_q |= (
                Q(title__icontains=token)
                | Q(description__icontains=token)
                | Q(short_description__icontains=token)
                | Q(search_keywords__icontains=token)
            )
        qs = qs.filter(
            Q(title__icontains=q)
            | Q(description__icontains=q)
            | Q(short_description__icontains=q)
            | token_q
        )
    return qs.order_by("category__order", "order", "id")


def rank_services(services: Iterable[Service], q: str, *, limit: int = 12) -> list[tuple[Service, float]]:
    q = _normalize_query(q)
    tokens = tokenize_query(q)
    if not q:
        ranked = []
        for service in services:
            score = (2.0 if service.is_featured else 0.0) + min(3.0, math.log1p(service.view_count))
            ranked.append((service, score))
        ranked.sort(key=lambda x: (-x[1], x[0].order, x[0].id))
        return ranked[:limit]

    scored = [(_score_service(service, tokens, q), service) for service in services]
    scored = [(s, svc) for s, svc in scored if s > 0]
    scored.sort(key=lambda x: (-x[0], x[1].order, x[1].id))
    return [(svc, s) for s, svc in scored[:limit]]


def smart_search_services(
    q: str = "",
    *,
    category_slug: str = "",
    limit: int = 30,
    min_score: float = 2.0,
) -> list[Service]:
    services = _service_candidates(category_slug=category_slug)
    q = _normalize_query(q)
    if not q:
        ranked = rank_services(services, "", limit=limit)
        return [s for s, _ in ranked]

    ranked = rank_services(services, q, limit=max(limit, 50))
    results = [(s, sc) for s, sc in ranked if sc >= min_score]
    if not results and ranked:
        results = ranked[: min(5, len(ranked))]
    return [s for s, _ in results[:limit]]


def get_featured_services(*, category_slug: str = "", limit: int = 8) -> list[Service]:
    qs = active_service_queryset().filter(is_featured=True)
    if category_slug:
        qs = qs.filter(category__slug=category_slug, category__is_active=True)
    return list(qs.order_by("order", "id")[:limit])


def suggest_services(
    q: str = "",
    *,
    category_slug: str = "",
    limit: int = 8,
) -> list[Service]:
    q = _normalize_query(q)
    if not q or len(q) < 2:
        services = _service_candidates(category_slug=category_slug)
        featured = [s for s in services if s.is_featured]
        if featured:
            featured.sort(key=lambda s: (-s.view_count, s.order, s.id))
            return featured[:limit]
        services.sort(key=lambda s: (-s.view_count, s.order, s.id))
        return services[:limit]

    return smart_search_services(
        q,
        category_slug=category_slug,
        limit=limit,
        min_score=1.5,
    )


def split_search_results(
    q: str,
    *,
    category_slug: str = "",
    primary_limit: int = 1,
    related_limit: int = 6,
    min_score: float = 2.0,
) -> tuple[list[Service], list[Service], str | None]:
    q = _normalize_query(q)
    if not q:
        return [], [], None

    services = _service_candidates(category_slug=category_slug)
    ranked = rank_services(services, q, limit=max(primary_limit + related_limit + 5, 30))
    ranked = [(s, sc) for s, sc in ranked if sc >= min_score]

    if not ranked:
        related = related_services_for_query(q, category_slug=category_slug, limit=related_limit)
        return [], related, None

    primary = [s for s, _ in ranked[:primary_limit]]
    primary_ids = {s.id for s in primary}
    related = [
        s
        for s, _ in ranked[primary_limit : primary_limit + related_limit]
        if s.id not in primary_ids
    ]

    if len(related) < related_limit:
        for s in related_services_for_query(q, category_slug=category_slug, limit=related_limit + 3):
            if s.id in primary_ids or any(r.id == s.id for r in related):
                continue
            related.append(s)
            if len(related) >= related_limit:
                break

    best_slug = primary[0].slug if primary else None
    return primary, related, best_slug


def related_services_for_query(q: str, *, category_slug: str = "", limit: int = 5) -> list[Service]:
    items = smart_search_services(q, category_slug=category_slug, limit=limit, min_score=1.0)
    if items:
        return items
    services = _service_candidates(category_slug=category_slug)
    return [s for s, _ in rank_services(services, q, limit=limit)]
