"""
جستجو و پیشنهاد هوشمند دوره‌های تحصیلی — تطابق تقریبی و مترادف.
"""
from __future__ import annotations

from typing import Iterable

from django.db.models import Q, QuerySet
from django.utils.html import strip_tags

from .faq_search import (
    _SYNONYM_GROUPS,
    _fuzzy_ratio,
    _normalize_persian,
    _normalize_query,
    _token_matches,
    tokenize_query,
)
from .major_search import _FUZZY_TYPO_MIN, _best_query_match
from .models import Course

_COURSE_SYNONYMS: tuple[frozenset[str], ...] = _SYNONYM_GROUPS + (
    frozenset({"دوره", "دوره‌ها", "course", "کلاس", "برنامه", "آموزش"}),
    frozenset({"ielts", "آیلتس", "ایلتس", "toefl", "تافل", "تافل", "pte"}),
    frozenset({"زبان", "language", "انگلیسی", "english", "آمادگی", "prep", "preparation"}),
    frozenset({"حضوری", "آنلاین", "online", "in_person", "غیرحضوری"}),
    frozenset({"چین", "china", "کانادا", "canada", "اسپانیا", "spain"}),
)

_COURSE_LIST_ONLY = (
    "id",
    "title",
    "slug",
    "short_description",
    "description",
    "features",
    "country",
    "order",
    "is_active",
    "delivery_mode",
    "duration_hours",
    "price",
)

_COURSE_SEARCH_DB_LIMIT = 96
_COURSE_FUZZY_POOL_LIMIT = 80
_SQL_TOKEN_CAP = 10


def _expand_course_tokens(tokens: list[str]) -> list[str]:
    expanded: list[str] = []
    seen: set[str] = set()
    for token in tokens:
        if token not in seen:
            seen.add(token)
            expanded.append(token)
        for group in _COURSE_SYNONYMS:
            if token in group:
                for word in group:
                    if word not in seen:
                        seen.add(word)
                        expanded.append(word)
    return expanded


def _course_search_tokens(q: str) -> tuple[str, list[str], list[str]]:
    q = _normalize_query(q)
    tokens = tokenize_query(q)
    return q, tokens, _expand_course_tokens(tokens)


def active_course_queryset() -> QuerySet:
    return Course.objects.filter(is_active=True).only(*_COURSE_LIST_ONLY)


def _core_search_q(q: str, tokens: list[str], expanded: list[str]) -> Q:
    clause = (
        Q(title__icontains=q)
        | Q(slug__icontains=q)
        | Q(short_description__icontains=q)
        | Q(features__icontains=q)
    )
    slug_hint = q.replace(" ", "-")
    if slug_hint != q:
        clause |= Q(slug__icontains=slug_hint)
    seen: set[str] = set()
    for token in (*tokens, *expanded):
        if len(token) < 2 or token in seen:
            continue
        seen.add(token)
        clause |= Q(title__icontains=token) | Q(slug__icontains=token)
        if len(seen) <= _SQL_TOKEN_CAP:
            clause |= Q(short_description__icontains=token) | Q(features__icontains=token)
    return clause


def _extended_search_q(q: str, tokens: list[str], expanded: list[str]) -> Q:
    clause = Q(description__icontains=q)
    seen: set[str] = set()
    for token in (*tokens, *expanded):
        if len(token) < 2 or token in seen:
            continue
        seen.add(token)
        if len(seen) <= _SQL_TOKEN_CAP:
            clause |= Q(description__icontains=token)
    return clause


def _faq_search_q(tokens: list[str], expanded: list[str]) -> Q | None:
    clause = Q()
    seen: set[str] = set()
    for token in (*tokens, *expanded):
        if len(token) < 2 or token in seen:
            continue
        seen.add(token)
        if len(seen) > _SQL_TOKEN_CAP:
            break
        clause |= Q(faqs__question__icontains=token) | Q(faqs__answer__icontains=token)
    return clause if clause else None


def _course_fields_fast(course: Course) -> tuple[str, str, str, str]:
    title = _normalize_persian(course.title or "").lower()
    summary = _normalize_persian(course.short_description or "").lower()
    country_label = _normalize_persian(course.get_country_display() or "").lower()
    features = _normalize_persian(course.features or "").lower()
    slug_text = (course.slug or "").replace("-", " ").lower()
    haystack = f"{title} {summary} {features} {country_label} {slug_text}"
    return title, summary, country_label, haystack


def _course_fields(course: Course) -> tuple[str, str, str, str, str]:
    title, summary, country_label, features = _course_fields_fast(course)[:4]
    description = _normalize_persian(strip_tags(course.description or "")).lower()
    faq_parts: list[str] = []
    cache = getattr(course, "_prefetched_objects_cache", {})
    faqs = cache.get("faqs")
    if faqs is None and course.pk:
        faqs = course.faqs.filter(is_active=True)
    if faqs:
        for faq in faqs:
            faq_parts.append(faq.question or "")
            faq_parts.append(strip_tags(faq.answer or ""))
    faq_text = _normalize_persian(" ".join(faq_parts)).lower()
    slug_text = (course.slug or "").replace("-", " ").lower()
    haystack = f"{title} {summary} {description} {features} {faq_text} {country_label} {slug_text}"
    return title, summary, description, country_label, haystack


def _fuzzy_score_for_course(course: Course, q: str, *, fast: bool = False) -> float:
    if fast:
        title, summary, _country, haystack = _course_fields_fast(course)
    else:
        title, summary, _description, _country, haystack = _course_fields(course)
    q = _normalize_query(q)
    best = max(
        _best_query_match(q, title),
        _best_query_match(q, summary) * 0.92,
        _best_query_match(q, haystack) * 0.78,
        _fuzzy_ratio(q, title) * 0.85,
    )
    if best < _FUZZY_TYPO_MIN:
        return 0.0
    return best * 16.0


def _score_course(
    course: Course,
    tokens: list[str],
    full_q: str,
    *,
    fast: bool = False,
) -> float:
    if not tokens and not full_q:
        return 0.0

    if fast:
        title, summary, country_label, haystack = _course_fields_fast(course)
        description = ""
        faq_text = ""
    else:
        title, summary, description, country_label, haystack = _course_fields(course)
        faq_text = haystack

    score = 0.0
    full_lower = _normalize_query(full_q).lower()

    if full_lower:
        if full_lower in title:
            score += 15.0
        elif full_lower in haystack:
            score += 7.0
        else:
            q_ratio = _fuzzy_ratio(full_lower, title)
            if q_ratio >= 0.55:
                score += q_ratio * 8.0
            typo = _best_query_match(full_lower, title)
            if typo >= 0.62 and typo > q_ratio:
                score += typo * 7.0

    expanded = _expand_course_tokens(tokens)
    matched_tokens = 0
    for token in expanded:
        t_score = _token_matches(title, token)
        if t_score >= 0.78:
            score += 5.0 * t_score
            matched_tokens += 1
        elif _token_matches(summary, token) >= 0.78:
            score += 3.0
            matched_tokens += 1
        elif description and _token_matches(description, token) >= 0.78:
            score += 2.0
            matched_tokens += 1
        elif faq_text and _token_matches(faq_text, token) >= 0.78:
            score += 2.2
            matched_tokens += 1
        elif _token_matches(haystack, token) >= 0.65:
            score += 0.8

    if tokens and matched_tokens == len(tokens):
        score += 3.0
    elif tokens and matched_tokens > 0:
        score += matched_tokens * 0.5

    if country_label and tokens:
        for token in expanded:
            if token in country_label:
                score += 1.8

    if not fast:
        fuzzy_boost = _fuzzy_score_for_course(course, full_q, fast=False)
        if fuzzy_boost > 0 and score < fuzzy_boost * 0.45:
            score = max(score, fuzzy_boost * 0.55)
    else:
        fuzzy_boost = _fuzzy_score_for_course(course, full_q, fast=True)
        if fuzzy_boost > 0 and score < 2.0:
            score = max(score, fuzzy_boost * 0.5)

    return score


def _filtered_courses_for_search(
    q: str,
    *,
    country_code: str = "",
    limit: int = _COURSE_SEARCH_DB_LIMIT,
) -> list[Course]:
    qs = active_course_queryset()
    if country_code:
        qs = qs.filter(country=country_code)

    q_norm, tokens, expanded = _course_search_tokens(q)
    if not q_norm:
        return list(qs.order_by("order", "id")[: max(1, limit)])

    limit = max(1, limit)
    core_q = _core_search_q(q_norm, tokens, expanded)
    core = list(qs.filter(core_q).distinct().order_by("order", "id")[:limit])
    if len(core) >= max(12, limit // 2):
        return core[:limit]

    seen_ids = {c.id for c in core}
    need = limit - len(core)
    if need > 0:
        ext_q = _extended_search_q(q_norm, tokens, expanded)
        extra = list(
            qs.filter(ext_q)
            .exclude(id__in=seen_ids)
            .distinct()
            .order_by("order", "id")[:need]
        )
        core.extend(extra)
        seen_ids.update(c.id for c in extra)

    need = limit - len(core)
    if need > 0:
        faq_q = _faq_search_q(tokens, expanded)
        if faq_q:
            faq_extra = list(
                qs.filter(faq_q)
                .exclude(id__in=seen_ids)
                .distinct()
                .order_by("order", "id")[:need]
            )
            core.extend(faq_extra)
    return core[:limit]


def _fuzzy_fallback_courses(
    q: str,
    *,
    country_code: str = "",
    exclude_ids: set[int] | None = None,
    limit: int = 24,
) -> list[Course]:
    exclude_ids = exclude_ids or set()
    qs = active_course_queryset()
    if country_code:
        qs = qs.filter(country=country_code)

    q_norm, tokens, expanded = _course_search_tokens(q)
    pool_q = Q()
    if len(q_norm) >= 2:
        pool_q |= Q(title__icontains=q_norm[:2])
    for token in (*tokens, *expanded)[:5]:
        if len(token) >= 2:
            pool_q |= Q(title__icontains=token)
    pool: list[Course] = []
    if pool_q:
        pool = list(qs.filter(pool_q).distinct().order_by("order", "id")[:_COURSE_FUZZY_POOL_LIMIT])
    if len(pool) < limit:
        extra = list(
            qs.exclude(id__in=[c.id for c in pool])
            .order_by("order", "id")[: max(0, _COURSE_FUZZY_POOL_LIMIT - len(pool))]
        )
        pool.extend(extra)

    scored: list[tuple[float, Course]] = []
    for course in pool:
        if course.id in exclude_ids:
            continue
        fs = _fuzzy_score_for_course(course, q_norm, fast=True)
        if fs > 0:
            scored.append((fs, course))
    scored.sort(key=lambda x: (-x[0], x[1].order, x[1].id))
    return [c for _, c in scored[:limit]]


def rank_courses(
    courses: Iterable[Course],
    q: str,
    *,
    limit: int = 40,
    fast: bool = False,
) -> list[tuple[Course, float]]:
    q = _normalize_query(q)
    tokens = tokenize_query(q)
    course_list = list(courses)
    if not q:
        ranked = [(c, float(c.order)) for c in course_list]
        ranked.sort(key=lambda x: (x[0].order, x[0].id))
        return ranked[:limit]

    scored = [
        (_score_course(course, tokens, q, fast=fast), course) for course in course_list
    ]
    scored = [(s, c) for s, c in scored if s > 0]
    if not scored:
        fuzzy_scored = []
        for course in course_list:
            fs = _fuzzy_score_for_course(course, q, fast=fast)
            if fs > 0:
                fuzzy_scored.append((fs, course))
        scored = fuzzy_scored

    scored.sort(key=lambda x: (-x[0], x[1].order, x[1].id))
    return [(c, s) for s, c in scored[:limit]]


def smart_search_courses(
    q: str = "",
    *,
    country_code: str = "",
    limit: int = 60,
    min_score: float = 1.6,
) -> list[Course]:
    q = _normalize_query(q)
    if not q:
        qs = active_course_queryset()
        if country_code:
            qs = qs.filter(country=country_code)
        return list(qs.order_by("order", "id")[:limit])

    courses = _filtered_courses_for_search(q, country_code=country_code)
    if len(courses) < 6:
        extra = _fuzzy_fallback_courses(
            q,
            country_code=country_code,
            exclude_ids={c.id for c in courses},
            limit=max(20, limit),
        )
        seen = {c.id for c in courses}
        for course in extra:
            if course.id not in seen:
                courses.append(course)
                seen.add(course.id)

    ranked = rank_courses(courses, q, limit=max(limit, 50), fast=False)
    results = [(c, sc) for c, sc in ranked if sc >= min_score]
    if not results and ranked:
        results = ranked[: min(8, len(ranked))]
    return [c for c, _ in results[:limit]]


def suggest_courses_ranked(
    q: str = "",
    *,
    country_code: str = "",
    limit: int = 8,
) -> list[tuple[Course, float]]:
    q = _normalize_query(q)
    if not q or len(q) < 2:
        qs = active_course_queryset()
        if country_code:
            qs = qs.filter(country=country_code)
        items = list(qs.order_by("order", "id")[:limit])
        return [(c, float(c.order)) for c in items]

    courses = _filtered_courses_for_search(
        q,
        country_code=country_code,
        limit=min(_COURSE_SEARCH_DB_LIMIT, 48),
    )
    if len(courses) < 4:
        extra = _fuzzy_fallback_courses(
            q,
            country_code=country_code,
            exclude_ids={c.id for c in courses},
            limit=16,
        )
        seen = {c.id for c in courses}
        for course in extra:
            if course.id not in seen:
                courses.append(course)
                seen.add(course.id)

    return rank_courses(courses, q, limit=limit, fast=True)


def suggest_query_for_courses(q: str, *, country_code: str = "") -> str | None:
    """پیشنهاد اصلاح غلط املایی بر اساس عنوان نزدیک‌ترین دوره."""
    q = _normalize_query(q)
    if len(q) < 3:
        return None
    ranked = suggest_courses_ranked(q, country_code=country_code, limit=3)
    if not ranked:
        return None
    top_course, score = ranked[0]
    if score < 4.0:
        return None
    title = _normalize_persian(top_course.title or "").strip().lower()
    q_lower = q.lower()
    if q_lower in title or title in q_lower:
        return None
    ratio = _best_query_match(q_lower, title)
    if ratio < 0.58 or ratio >= 0.98:
        return None
    if len(q_lower) >= 5 and len(title) > len(q_lower) + 12:
        for word in title.split():
            if len(word) >= 3 and _best_query_match(q_lower, word) >= 0.72:
                return word
        return None
    return title if title != q_lower else None


def search_course_slugs(
    q: str = "",
    *,
    country_code: str = "",
) -> tuple[list[str], str | None]:
    """برگرداندن اسلاگ‌های دوره‌های منطبق + پیشنهاد اصلاح املا."""
    q = _normalize_query(q)
    if not q:
        qs = active_course_queryset()
        if country_code:
            qs = qs.filter(country=country_code)
        return [c.slug for c in qs.order_by("order", "id")], None

    courses = smart_search_courses(q, country_code=country_code)
    did_you_mean = None
    if courses:
        top = courses[0]
        title = _normalize_persian(top.title or "").lower()
        if q.lower() not in title and _best_query_match(q, title) >= 0.62:
            alt = suggest_query_for_courses(q, country_code=country_code)
            if alt and alt.lower() != q.lower():
                did_you_mean = alt
    return [c.slug for c in courses], did_you_mean
