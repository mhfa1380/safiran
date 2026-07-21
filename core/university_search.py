"""
جستجو و پیشنهاد هوشمند دانشگاه‌ها — الگوی مشابه major_search با فیلتر DB محدود.
"""
from __future__ import annotations

from typing import Iterable

from django.db.models import Q, QuerySet

from core.study_destinations import WORLD_STUDY_COUNTRY_CODES
from core.browse_cache import count_for_queryset

from .faq_search import (
    _fuzzy_ratio,
    _normalize_persian,
    _normalize_query,
    _token_matches,
    _words,
    tokenize_query,
)

_UNI_SEARCH_DB_LIMIT = 72
_UNI_SUGGEST_DB_LIMIT = 36
_UNI_FUZZY_POOL_LIMIT = 80
_SQL_TOKEN_CAP = 8
_FUZZY_TYPO_MIN = 0.42
_FUZZY_TYPO_STRONG = 0.62

_UNI_LIST_ONLY = (
    "id",
    "slug",
    "image",
    "name_fa",
    "name_en",
    "city",
    "country",
    "type",
    "world_rank",
    "short_description",
    "is_approved_by_mo_science",
    "is_approved_by_mo_health",
)

_COUNTRY_ALIASES: dict[str, tuple[str, ...]] = {
    "china": ("چین", "china", "پکن", "شانگهای", "peking", "beijing", "shanghai"),
    "canada": ("کانادا", "canada", "تورنتو", "ونکوور", "toronto", "vancouver"),
    "spain": ("اسپانیا", "spain", "بارسلونا", "مادرید", "barcelona", "madrid"),
}

from .models import University


def filter_universities_by_country(qs: QuerySet, country_code: str) -> QuerySet:
    code = (country_code or "").strip()
    if not code:
        return qs
    if code == "other":
        return qs.filter(country__in=WORLD_STUDY_COUNTRY_CODES)
    return qs.filter(country=code)


def _best_query_match(query: str, text: str) -> float:
    query = _normalize_query(query).lower()
    text = _normalize_persian(text or "").lower()
    if not query or not text:
        return 0.0
    if query in text:
        return 1.0
    best = _fuzzy_ratio(query, text)
    q_len = len(query)
    for word in _words(text):
        if len(word) < 2:
            continue
        if len(word) > 48:
            word = word[:48]
        best = max(best, _fuzzy_ratio(query, word))
        for prefix_len in range(3, min(len(word), q_len + 3) + 1):
            best = max(best, _fuzzy_ratio(query, word[:prefix_len]))
    return best


def _expand_uni_tokens(tokens: list[str]) -> list[str]:
    expanded: list[str] = []
    seen: set[str] = set()
    for token in tokens:
        if token not in seen:
            seen.add(token)
            expanded.append(token)
        for aliases in _COUNTRY_ALIASES.values():
            if token in aliases:
                for word in aliases:
                    if word not in seen:
                        seen.add(word)
                        expanded.append(word)
    return expanded


def _core_search_q(q: str, tokens: list[str], expanded: list[str]) -> Q:
    clause = (
        Q(name_fa__icontains=q)
        | Q(name_en__icontains=q)
        | Q(city__icontains=q)
        | Q(slug__icontains=q)
        | Q(short_description__icontains=q)
    )
    slug_hint = q.replace(" ", "-")
    if slug_hint != q:
        clause |= Q(slug__icontains=slug_hint)
    seen: set[str] = set()
    for token in (*tokens, *expanded):
        if len(token) < 2 or token in seen:
            continue
        seen.add(token)
        clause |= (
            Q(name_fa__icontains=token)
            | Q(name_en__icontains=token)
            | Q(city__icontains=token)
        )
        if len(seen) <= _SQL_TOKEN_CAP:
            clause |= Q(short_description__icontains=token)
    return clause


def _filter_universities_by_major(qs: QuerySet, major_slug: str = "") -> QuerySet:
    slug = (major_slug or "").strip()
    if not slug:
        return qs
    return qs.filter(major_links__major__slug=slug, major_links__major__is_active=True).distinct()


SCHOOLS_TIER_OTHER = "other"


def _browse_queryset(
    *,
    country_code: str = "",
    utype: str = "",
    major_slug: str = "",
    tier_code: str = "",
) -> QuerySet:
    qs = University.objects.only(*_UNI_LIST_ONLY).order_by(
        "country", "world_rank_num", "name_fa"
    )
    if country_code:
        qs = filter_universities_by_country(qs, country_code)
    if utype:
        qs = qs.filter(type=utype)
    if tier_code == SCHOOLS_TIER_OTHER:
        qs = qs.filter(world_rank_num__gt=30)
    qs = _filter_universities_by_major(qs, major_slug)
    return qs


def _browse_count_key_parts(
    *,
    country_code: str = "",
    utype: str = "",
    major_slug: str = "",
    tier_code: str = "",
) -> tuple[str, ...]:
    return (country_code or "-", utype or "-", major_slug or "-", tier_code or "-")


def _uni_fields_fast(uni: University) -> tuple[str, str, str, str, str]:
    name_fa = _normalize_persian(uni.name_fa or "").lower()
    name_en = _normalize_persian(uni.name_en or "").lower()
    city = _normalize_persian(uni.city or "").lower()
    summary = _normalize_persian(uni.short_description or "").lower()
    country_label = _normalize_persian(uni.get_country_display() or "").lower()
    slug_text = (uni.slug or "").replace("-", " ").lower()
    haystack = f"{name_fa} {name_en} {city} {summary} {country_label} {slug_text}"
    return name_fa, name_en, city, country_label, haystack


def _score_university(uni: University, tokens: list[str], full_q: str, *, fast: bool = True) -> float:
    if not tokens and not full_q:
        return 0.0
    name_fa, name_en, city, country_label, haystack = _uni_fields_fast(uni)
    summary = _normalize_persian(uni.short_description or "").lower() if not fast else ""
    score = 0.0
    full_lower = _normalize_query(full_q).lower()

    if full_lower:
        if name_fa.startswith(full_lower):
            score += 24.0
        elif full_lower in name_fa:
            score += 18.0
        elif full_lower in name_en:
            score += 16.0
        elif full_lower in city:
            score += 14.0
        elif full_lower in haystack:
            score += 8.0
        else:
            for part, weight in ((name_fa, 14.0), (name_en, 12.0), (city, 10.0)):
                fuzzy = _best_query_match(full_lower, part)
                if fuzzy >= _FUZZY_TYPO_STRONG:
                    score += fuzzy * weight
                    break
                if fuzzy >= _FUZZY_TYPO_MIN:
                    score += fuzzy * (weight * 0.7)
                    break

    expanded = _expand_uni_tokens(tokens)
    core_tokens = tokens or tokenize_query(full_q)
    core_matched = 0
    for token in core_tokens:
        if _token_matches(name_fa, token) >= 0.78 or _token_matches(name_en, token) >= 0.78:
            score += 6.5
            core_matched += 1
        elif _token_matches(city, token) >= 0.78:
            score += 5.0
            core_matched += 1
        elif _token_matches(haystack, token) >= 0.72:
            score += 1.5
            core_matched += 1
        elif summary and _token_matches(summary, token) >= 0.72:
            score += 1.2
            core_matched += 1

    for token in expanded:
        if token in core_tokens:
            continue
        if _token_matches(haystack, token) >= 0.72:
            score += 0.8

    if core_tokens and core_matched == len(core_tokens):
        score += 4.0

    if uni.country and core_tokens:
        for token in core_tokens:
            if token in country_label:
                score += 2.0

    if uni.world_rank_num and uni.world_rank_num <= 100:
        score += max(0.0, 2.5 - uni.world_rank_num * 0.02)

    return score


def _filtered_universities_for_search(
    q: str,
    *,
    country_code: str = "",
    utype: str = "",
    major_slug: str = "",
    tier_code: str = "",
    limit: int = _UNI_SEARCH_DB_LIMIT,
) -> list[University]:
    qs = _browse_queryset(
        country_code=country_code,
        utype=utype,
        major_slug=major_slug,
        tier_code=tier_code,
    )
    q_norm = _normalize_query(q)
    tokens = tokenize_query(q_norm)
    expanded = _expand_uni_tokens(tokens)
    if not q_norm:
        return list(qs[: max(1, limit)])

    limit = max(1, limit)
    core_q = _core_search_q(q_norm, tokens, expanded)
    core = list(qs.filter(core_q).distinct()[:limit])
    if len(core) >= max(12, limit // 2):
        return core[:limit]

    seen_ids = {u.id for u in core}
    need = limit - len(core)
    if need > 0:
        pool_q = Q()
        if len(q_norm) >= 2:
            pool_q |= Q(name_fa__icontains=q_norm[:2]) | Q(city__icontains=q_norm[:2])
        for token in (*tokens, *expanded)[:6]:
            if len(token) >= 2:
                pool_q |= Q(name_fa__icontains=token) | Q(city__icontains=token)
        if pool_q:
            extra = list(
                qs.filter(pool_q)
                .exclude(id__in=seen_ids)
                .distinct()[:need]
            )
            core.extend(extra)
    return core[:limit]


def _fuzzy_fallback_universities(
    q: str,
    *,
    country_code: str = "",
    utype: str = "",
    tier_code: str = "",
    exclude_ids: set[int] | None = None,
    limit: int = 20,
) -> list[University]:
    exclude_ids = exclude_ids or set()
    q_norm = _normalize_query(q)
    pool = _filtered_universities_for_search(
        q,
        country_code=country_code,
        utype=utype,
        tier_code=tier_code,
        limit=_UNI_FUZZY_POOL_LIMIT,
    )
    if len(pool) < limit:
        qs = _browse_queryset(country_code=country_code, utype=utype, tier_code=tier_code)
        extra = list(
            qs.exclude(id__in=[u.id for u in pool]).distinct()[: max(0, _UNI_FUZZY_POOL_LIMIT - len(pool))]
        )
        pool.extend(extra)

    scored: list[tuple[float, University]] = []
    for uni in pool:
        if uni.id in exclude_ids:
            continue
        name_fa, name_en, city, _country, _hay = _uni_fields_fast(uni)
        best = max(
            _best_query_match(q_norm, name_fa),
            _best_query_match(q_norm, name_en) * 0.95,
            _best_query_match(q_norm, city) * 0.9,
        )
        if best >= _FUZZY_TYPO_MIN:
            scored.append((best * 16.0, uni))
    scored.sort(key=lambda x: (-x[0], x[1].name_fa))
    return [u for _, u in scored[:limit]]


def rank_universities(
    universities: Iterable[University],
    q: str,
    *,
    limit: int = 12,
) -> list[tuple[University, float]]:
    q = _normalize_query(q)
    tokens = tokenize_query(q)
    uni_list = list(universities)
    if not q:
        return [(u, 1.0) for u in uni_list[:limit]]

    scored = [
        (_score_university(uni, tokens, q, fast=True), uni) for uni in uni_list
    ]
    scored = [(s, u) for s, u in scored if s > 0]
    if not scored:
        fallback = _fuzzy_fallback_universities(
            q,
            exclude_ids={u.id for u in uni_list},
            limit=limit,
        )
        scored = [(12.0, u) for u in fallback]
    scored.sort(key=lambda x: (-x[0], x[1].name_fa))
    return [(u, s) for s, u in scored[:limit]]


def suggest_universities_ranked(
    q: str = "",
    *,
    country_code: str = "",
    utype: str = "",
    tier_code: str = "",
    limit: int = 8,
) -> list[tuple[University, float]]:
    q = _normalize_query(q)
    if not q or len(q) < 2:
        featured = get_featured_universities(
            country_code=country_code,
            utype=utype,
            tier_code=tier_code,
            limit=limit,
        )
        return [(u, 1.0) for u in featured]

    universities = _filtered_universities_for_search(
        q,
        country_code=country_code,
        utype=utype,
        tier_code=tier_code,
        limit=_UNI_SUGGEST_DB_LIMIT,
    )
    if len(universities) < limit:
        extra = _fuzzy_fallback_universities(
            q,
            country_code=country_code,
            utype=utype,
            tier_code=tier_code,
            exclude_ids={u.id for u in universities},
            limit=limit,
        )
        seen = {u.id for u in universities}
        for u in extra:
            if u.id not in seen:
                universities.append(u)
                seen.add(u.id)
    return rank_universities(universities, q, limit=limit)


def split_search_results(
    q: str,
    *,
    country_code: str = "",
    utype: str = "",
    major_slug: str = "",
    tier_code: str = "",
    primary_limit: int = 1,
    related_limit: int = 8,
    min_score: float = 1.8,
) -> tuple[list[University], list[University], str | None]:
    q = _normalize_query(q)
    if not q:
        return [], [], None

    adaptive_min = 1.15 if len(q) <= 3 else min_score
    universities = _filtered_universities_for_search(
        q,
        country_code=country_code,
        utype=utype,
        major_slug=major_slug,
        tier_code=tier_code,
        limit=_UNI_SEARCH_DB_LIMIT,
    )
    if len(universities) < 10:
        universities.extend(
            _fuzzy_fallback_universities(
                q,
                country_code=country_code,
                utype=utype,
                tier_code=tier_code,
                exclude_ids={u.id for u in universities},
                limit=24,
            )
        )
    ranked = rank_universities(
        universities,
        q,
        limit=max(related_limit + primary_limit + 10, 36),
    )
    ranked = [(u, sc) for u, sc in ranked if sc >= adaptive_min]
    if not ranked:
        return [], [], None

    best_score = ranked[0][1]
    strong_cutoff = max(min_score * 1.1, best_score * 0.82, best_score - 2.5)
    related_cutoff = max(min_score * 1.05, best_score * 0.68)

    primary: list[University] = []
    related: list[University] = []
    for uni, score in ranked:
        if score >= strong_cutoff and len(primary) < 8:
            primary.append(uni)
        elif score >= related_cutoff and len(related) < min(related_limit, 8):
            related.append(uni)

    if not primary:
        primary = [ranked[0][0]]
        related = [u for u, _ in ranked[1 : min(related_limit, 7) + 1]]

    primary_ids = {u.id for u in primary}
    related = [u for u in related if u.id not in primary_ids]
    best_slug = primary[0].slug if primary else None
    return primary, related, best_slug


SCHOOLS_PAGE_SIZE = 20
SCHOOLS_PAGE_SIZE_MAX = 40
FEATURED_UNIVERSITIES_LIMIT = 6


def get_featured_universities(
    *,
    country_code: str = "",
    utype: str = "",
    tier_code: str = "",
    limit: int = FEATURED_UNIVERSITIES_LIMIT,
) -> list[University]:
    uni_fields = _UNI_LIST_ONLY
    featured_qs = (
        University.objects.only(*uni_fields)
        .exclude(world_rank="")
        .order_by("world_rank_num", "name_fa")
    )
    if country_code:
        featured_qs = filter_universities_by_country(featured_qs, country_code)
    if utype:
        featured_qs = featured_qs.filter(type=utype)
    if tier_code == SCHOOLS_TIER_OTHER:
        featured_qs = featured_qs.filter(world_rank_num__gt=30)
    featured = list(featured_qs[:limit])
    if len(featured) >= limit:
        return featured

    seen = {u.slug for u in featured}
    browse = _browse_queryset(country_code=country_code, utype=utype, tier_code=tier_code)
    for uni in browse[: limit * 2]:
        if uni.slug not in seen:
            featured.append(uni)
            seen.add(uni.slug)
        if len(featured) >= limit:
            break
    return featured


def list_universities_browse(
    *,
    country_code: str = "",
    utype: str = "",
    major_slug: str = "",
    tier_code: str = "",
    offset: int = 0,
    limit: int = SCHOOLS_PAGE_SIZE,
) -> tuple[list[University], int, bool]:
    limit = max(1, min(int(limit or SCHOOLS_PAGE_SIZE), SCHOOLS_PAGE_SIZE_MAX))
    offset = max(0, int(offset or 0))
    qs = _browse_queryset(
        country_code=country_code,
        utype=utype,
        major_slug=major_slug,
        tier_code=tier_code,
    )
    key_parts = _browse_count_key_parts(
        country_code=country_code,
        utype=utype,
        major_slug=major_slug,
        tier_code=tier_code,
    )
    total = count_for_queryset("uni", key_parts, qs)
    items = list(qs[offset : offset + limit])
    has_more = offset + len(items) < total
    return items, total, has_more
