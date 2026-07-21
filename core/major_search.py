"""
جستجو و پیشنهاد هوشمند رشته‌های تحصیلی.
"""
from __future__ import annotations

from typing import Iterable

from django.db.models import Prefetch, Q, QuerySet
from django.utils.html import strip_tags

from .faq_search import (
    _SYNONYM_GROUPS,
    _fuzzy_ratio,
    _normalize_persian,
    _normalize_query,
    _token_matches,
    _words,
    tokenize_query,
)

# آستانه تطابق تقریبی برای غلط‌های املایی (مثلاً «دتندون» → دندانپزشکی)
_FUZZY_TYPO_MIN = 0.42
_FUZZY_TYPO_STRONG = 0.62

# حداکثر رکورد از DB قبل از امتیازدهی پایتون — جلوگیری از بارگذاری ده‌ها هزار ردیف
_MAJOR_SEARCH_DB_LIMIT = 96
_MAJOR_SUGGEST_DB_LIMIT = 40
_MAJOR_FUZZY_POOL_LIMIT = 100
_SQL_TOKEN_CAP = 8

_MAJOR_BROWSE_ONLY = (
    "id",
    "title",
    "slug",
    "short_description",
    "country",
    "order",
    "is_active",
    "image",
)

_MAJOR_LIST_ONLY = (
    *_MAJOR_BROWSE_ONLY,
    "description",
)

from .models import Major, MajorFAQ
from core.study_destinations import WORLD_STUDY_COUNTRY_CODES
from core.browse_cache import count_for_queryset

_WORLD_COUNTRY_CODES = tuple(WORLD_STUDY_COUNTRY_CODES)


def filter_majors_by_country(qs: QuerySet, country_code: str) -> QuerySet:
    code = (country_code or "").strip()
    if not code:
        return qs
    if code == "other":
        return qs.filter(country__in=_WORLD_COUNTRY_CODES)
    return qs.filter(country=code)

_MAJOR_SYNONYMS: tuple[frozenset[str], ...] = _SYNONYM_GROUPS + (
    frozenset({"رشته", "رشته‌ها", "major", "تحصیلی", "رشته تحصیلی", "field"}),
    frozenset({"مهندسی", "engineer", "engineering", "فنی", "مهندس", "مکانیک", "برق", "عمران"}),
    frozenset({"پزشکی", "medical", "medicine", "سلامت", "پرستاری", "دارو", "دندان", "دندون", "دندانپزشکی", "dentistry"}),
    frozenset({"کامپیوتر", "computer", "نرم‌افزار", "نرم افزار", "برنامه", "it", "software", "cs"}),
    frozenset({"مدیریت", "business", "mba", "کسب و کار", "اقتصاد"}),
    frozenset({"حقوق", "law", "قانون", "حقوقی"}),
    frozenset({"معماری", "architecture", "شهرسازی", "urban"}),
    frozenset({"کارشناسی", "لیسانس", "bachelor", "undergraduate", "لیسانس"}),
    frozenset({"ارشد", "master", "کارشناسی ارشد", "تحصیلات تکمیلی"}),
    frozenset({"دکتری", "phd", "دکترا", "تحقیقاتی"}),
    frozenset({"بورسیه", "اسکالرشیپ", "scholarship", "فاند", "کمک هزینه", "کمک‌هزینه"}),
)


def _major_search_q_tokens(q: str) -> tuple[str, list[str], list[str]]:
    q = _normalize_query(q)
    tokens = tokenize_query(q)
    expanded = _expand_major_tokens(tokens)
    return q, tokens, expanded


def _core_search_q(q: str, tokens: list[str], expanded: list[str]) -> Q:
    """فیلتر سریع: عنوان، اسلاگ و خلاصه — بدون join سوالات."""
    clause = (
        Q(title__icontains=q)
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
        clause |= Q(title__icontains=token) | Q(slug__icontains=token)
        if len(seen) <= _SQL_TOKEN_CAP:
            clause |= Q(short_description__icontains=token)
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


def _expand_major_tokens(tokens: list[str]) -> list[str]:
    expanded: list[str] = []
    seen: set[str] = set()
    for token in tokens:
        if token not in seen:
            seen.add(token)
            expanded.append(token)
        for group in _MAJOR_SYNONYMS:
            if token in group:
                for word in group:
                    if word not in seen:
                        seen.add(word)
                        expanded.append(word)
    return expanded


def _best_query_match(query: str, text: str) -> float:
    """
    بهترین شباهت عبارت جستجو با متن — شامل پیشوند و پنجره لغزان
    برای واژه‌های مرکب فارسی (مثل دندانپزشکی در برابر دتندون).
    """
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
        if q_len <= 16 and len(word) >= q_len:
            shifts = len(word) - q_len + 1
            step = 1 if shifts <= 24 else max(1, shifts // 24)
            for i in range(0, shifts, step):
                chunk = word[i : i + q_len]
                best = max(best, _fuzzy_ratio(query, chunk))

    return best


def _fuzzy_score_for_major(major: Major, q: str, *, fast: bool = False) -> float:
    """امتیاز کمکی صرفاً از شباهت تقریبی — برای وقتی تطابق دقیق صفر است."""
    if fast:
        title, summary, _country_label, _haystack = _major_fields_fast(major)
    else:
        title, summary, _description, _faq_text, _country_label, _haystack = _major_fields(major)
    q = _normalize_query(q)
    best = max(
        _best_query_match(q, title),
        _best_query_match(q, summary) * 0.92,
        _fuzzy_ratio(q, title) * 0.85,
    )
    if best < _FUZZY_TYPO_MIN:
        return 0.0
    return best * 16.0


def _major_faq_text(major: Major) -> str:
    parts: list[str] = []
    cache = getattr(major, "_prefetched_objects_cache", {})
    faqs = cache.get("faqs")
    if faqs is None:
        faqs = major.faqs.filter(is_active=True)
    for faq in faqs:
        parts.append(faq.question or "")
        parts.append(strip_tags(faq.answer or ""))
    return _normalize_persian(" ".join(parts)).lower()


def _major_fields_fast(major: Major) -> tuple[str, str, str, str]:
    """فیلدهای سبک برای autocomplete — بدون FAQ و بدون description کامل."""
    title = _normalize_persian(major.title or "").lower()
    summary = _normalize_persian(major.short_description or "").lower()
    country_label = _normalize_persian(major.get_country_display() or "").lower()
    slug_text = (major.slug or "").replace("-", " ").lower()
    haystack = f"{title} {summary} {country_label} {slug_text}"
    return title, summary, country_label, haystack


def _major_fields(major: Major) -> tuple[str, str, str, str, str, str]:
    title = _normalize_persian(major.title or "").lower()
    summary = _normalize_persian(major.short_description or "").lower()
    description = _normalize_persian(strip_tags(major.description or "")).lower()
    faq_text = _major_faq_text(major)
    country_label = _normalize_persian(major.get_country_display() or "").lower()
    slug_text = (major.slug or "").replace("-", " ").lower()
    haystack = f"{title} {summary} {description} {faq_text} {country_label} {slug_text}"
    return title, summary, description, faq_text, country_label, haystack


def _context_boost(haystack: str, *, intent: str = "", target_degree: str = "") -> float:
    score = 0.0
    if intent == "scholarship":
        for word in ("بورسیه", "اسکالرشیپ", "scholarship", "فاند", "کمک"):
            if word in haystack:
                score += 2.5
                break
    degree_words = {
        "bachelor": ("کارشناسی", "لیسانس", "undergraduate", "bachelor"),
        "master": ("ارشد", "master", "کارشناسی ارشد"),
        "phd": ("دکتری", "phd", "دکترا", "تحقیقاتی"),
    }
    for word in degree_words.get((target_degree or "").strip().lower(), ()):
        if word in haystack:
            score += 1.5
            break
    return score


def _score_major(
    major: Major,
    tokens: list[str],
    full_q: str,
    *,
    intent: str = "",
    target_degree: str = "",
    fast: bool = False,
    expanded: list[str] | None = None,
) -> float:
    if not tokens and not full_q:
        return 0.0

    if fast:
        title, summary, country_label, haystack = _major_fields_fast(major)
        description = ""
        faq_text = ""
    else:
        title, summary, description, faq_text, country_label, haystack = _major_fields(major)
    score = 0.0
    full_lower = _normalize_query(full_q).lower()

    if full_lower:
        if title.startswith(full_lower):
            score += 24.0
        elif full_lower == title:
            score += 22.0
        elif full_lower in title:
            score += 18.0
        elif full_lower in summary:
            score += 12.0
        elif full_lower in haystack:
            score += 8.0
        elif not fast:
            for part, weight in ((title, 14.0), (summary, 9.0)):
                fuzzy = _best_query_match(full_lower, part)
                if fuzzy >= _FUZZY_TYPO_STRONG:
                    score += fuzzy * weight
                    break
                if fuzzy >= _FUZZY_TYPO_MIN:
                    score += fuzzy * (weight * 0.7)
                    break

    if expanded is None:
        expanded = _expand_major_tokens(tokens)
    core_tokens = tokens or tokenize_query(full_q)

    if fast:
        if core_tokens and all(token in title for token in core_tokens):
            score += 7.0
        core_matched = 0
        for token in core_tokens:
            if token in title:
                score += 6.5
                core_matched += 1
            elif token in summary:
                score += 4.0
                core_matched += 1
            elif token in haystack:
                score += 1.4
                core_matched += 1
        for token in expanded:
            if token in core_tokens:
                continue
            if token in title:
                score += 2.0
            elif token in haystack:
                score += 0.9
        if core_tokens and core_matched == len(core_tokens):
            score += 5.0
        elif core_tokens and core_matched > 0:
            score += core_matched * 0.8
        if major.country and core_tokens:
            for token in core_tokens:
                if token in country_label:
                    score += 2.0
        score += _context_boost(haystack, intent=intent, target_degree=target_degree)
        if major.order:
            score += min(1.0, major.order * 0.05)
        return score

    if core_tokens and all(
        _token_matches(title, token) >= 0.72 or token in title for token in core_tokens
    ):
        score += 7.0
    core_matched = 0
    for token in core_tokens:
        t_title = max(_token_matches(title, token), _best_query_match(token, title) * 0.95)
        if t_title >= 0.78:
            score += 6.5 * t_title
            core_matched += 1
        elif _token_matches(summary, token) >= 0.78:
            score += 4.0
            core_matched += 1
        elif _token_matches(description, token) >= 0.78 or _token_matches(faq_text, token) >= 0.78:
            score += 2.8
            core_matched += 1
        elif _token_matches(haystack, token) >= 0.72:
            score += 1.4
        elif _token_matches(haystack, token) >= 0.55:
            score += 0.5

    for token in expanded:
        if token in core_tokens:
            continue
        if _token_matches(title, token) >= 0.78:
            score += 2.0
        elif _token_matches(haystack, token) >= 0.72:
            score += 0.9

    if core_tokens and core_matched == len(core_tokens):
        score += 5.0
    elif core_tokens and core_matched > 0:
        score += core_matched * 0.8

    if major.country and core_tokens:
        for token in core_tokens:
            if token in country_label:
                score += 2.0

    score += _context_boost(haystack, intent=intent, target_degree=target_degree)
    if major.order:
        score += min(1.0, major.order * 0.05)
    return score


def _dedupe_majors(majors: list[Major]) -> list[Major]:
    """حذف رشته‌های تکراری با عنوان یکسان (کشورهای مختلف یک کارت)."""
    seen: set[str] = set()
    unique: list[Major] = []
    for major in majors:
        key = _normalize_persian(major.title or "").lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(major)
    return unique


def active_major_queryset() -> QuerySet:
    return Major.objects.filter(is_active=True)


def _major_candidates(*, country_code: str = "") -> list[Major]:
    """همه رشته‌های فعال — فقط برای مسیرهای اداری؛ جستجو از _filtered_majors_for_search استفاده کند."""
    qs = active_major_queryset().prefetch_related(
        Prefetch(
            "faqs",
            queryset=MajorFAQ.objects.filter(is_active=True).order_by("order", "id"),
        )
    )
    if country_code:
        qs = filter_majors_by_country(qs, country_code)
    return list(qs)


def _filtered_majors_for_search(
    q: str,
    *,
    country_code: str = "",
    university_slug: str = "",
    limit: int = _MAJOR_SEARCH_DB_LIMIT,
    prefetch_faqs: bool = False,
) -> list[Major]:
    """پیش‌فیلتر SQL چندمرحله‌ای — عنوان اول، توضیحات بعد، FAQ در صورت نیاز."""
    fields = _MAJOR_LIST_ONLY if prefetch_faqs else _MAJOR_BROWSE_ONLY
    qs = active_major_queryset().only(*fields)
    if country_code:
        qs = filter_majors_by_country(qs, country_code)
    qs = _filter_majors_by_university(qs, university_slug)
    if prefetch_faqs:
        qs = qs.prefetch_related(
            Prefetch(
                "faqs",
                queryset=MajorFAQ.objects.filter(is_active=True).order_by("order", "id"),
            )
        )

    q_norm, tokens, expanded = _major_search_q_tokens(q)
    if not q_norm:
        return list(qs.order_by("order", "id")[: max(1, limit)])

    limit = max(1, limit)
    core_q = _core_search_q(q_norm, tokens, expanded)
    core = list(qs.filter(core_q).distinct().order_by("order", "id")[:limit])
    if len(core) >= max(14, limit // 2):
        return core[:limit]

    seen_ids = {m.id for m in core}
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
        seen_ids.update(m.id for m in extra)

    if len(core) >= max(10, limit // 3):
        return core[:limit]

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


def _fuzzy_fallback_majors(
    q: str,
    *,
    country_code: str = "",
    university_slug: str = "",
    exclude_ids: set[int] | None = None,
    limit: int = 24,
) -> list[Major]:
    """اگر فیلتر متنی نتیجه کم داد، روی زیرمجموعه مرتبط با عبارت fuzzy اجرا می‌شود."""
    exclude_ids = exclude_ids or set()
    qs = active_major_queryset().only(*_MAJOR_BROWSE_ONLY)
    if country_code:
        qs = filter_majors_by_country(qs, country_code)
    qs = _filter_majors_by_university(qs, university_slug)

    q_norm, tokens, expanded = _major_search_q_tokens(q)
    pool_q = Q()
    if len(q_norm) >= 2:
        pool_q |= Q(title__icontains=q_norm[:2])
    for token in (*tokens, *expanded)[:5]:
        if len(token) >= 2:
            pool_q |= Q(title__icontains=token)
    pool: list[Major] = []
    if pool_q:
        pool = list(qs.filter(pool_q).distinct().order_by("order", "id")[:_MAJOR_FUZZY_POOL_LIMIT])
    if len(pool) < limit:
        extra = list(
            qs.exclude(id__in=[m.id for m in pool])
            .order_by("order", "id")[: max(0, _MAJOR_FUZZY_POOL_LIMIT - len(pool))]
        )
        pool.extend(extra)

    scored: list[tuple[float, Major]] = []
    for major in pool:
        if major.id in exclude_ids:
            continue
        fs = _fuzzy_score_for_major(major, q_norm, fast=True)
        if fs > 0:
            scored.append((fs, major))
    scored.sort(key=lambda x: (-x[0], x[1].order, x[1].id))
    return [m for _, m in scored[:limit]]


def _filter_majors_by_university(qs: QuerySet, university_slug: str = "") -> QuerySet:
    slug = (university_slug or "").strip()
    if not slug:
        return qs
    return qs.filter(university_links__university__slug=slug).distinct()


def filter_majors(
    queryset: QuerySet | None = None,
    *,
    q: str = "",
    country_code: str = "",
    university_slug: str = "",
) -> QuerySet:
    qs = queryset if queryset is not None else active_major_queryset()
    if country_code:
        qs = filter_majors_by_country(qs, country_code)
    qs = _filter_majors_by_university(qs, university_slug)
    q_norm, tokens, expanded = _major_search_q_tokens(q)
    if q_norm:
        text_q = _core_search_q(q_norm, tokens, expanded) | _extended_search_q(
            q_norm, tokens, expanded
        )
        faq_q = _faq_search_q(tokens, expanded)
        if faq_q:
            text_q |= faq_q
        qs = qs.filter(text_q).distinct()
    return qs.order_by("order", "id")


def rank_majors(
    majors: Iterable[Major],
    q: str,
    *,
    limit: int = 12,
    intent: str = "",
    target_degree: str = "",
    fast: bool = False,
) -> list[tuple[Major, float]]:
    q = _normalize_query(q)
    tokens = tokenize_query(q)
    major_list = list(majors)
    if not q:
        ranked = [(m, float(m.order)) for m in major_list]
        ranked.sort(key=lambda x: (x[0].order, x[0].id))
        return ranked[:limit]

    expanded = _expand_major_tokens(tokens)
    scored = [
        (
            _score_major(
                major,
                tokens,
                q,
                intent=intent,
                target_degree=target_degree,
                fast=fast,
                expanded=expanded,
            ),
            major,
        )
        for major in major_list
    ]
    scored = [(s, m) for s, m in scored if s > 0]
    if not scored and not fast:
        fuzzy_scored = []
        for major in major_list:
            fs = _fuzzy_score_for_major(major, q, fast=False)
            if fs > 0:
                fuzzy_scored.append((fs, major))
        scored = fuzzy_scored
    elif not scored and fast:
        fuzzy_scored = []
        for major in major_list:
            fs = _fuzzy_score_for_major(major, q, fast=True)
            if fs > 0:
                fuzzy_scored.append((fs, major))
        scored = fuzzy_scored

    scored.sort(key=lambda x: (-x[0], x[1].order, x[1].id))
    return [(m, s) for s, m in scored[:limit]]


def smart_search_majors(
    q: str = "",
    *,
    country_code: str = "",
    limit: int = 30,
    min_score: float = 1.8,
    intent: str = "",
    target_degree: str = "",
) -> list[Major]:
    q = _normalize_query(q)
    if not q:
        qs = filter_majors_by_country(
            active_major_queryset().only(*_MAJOR_LIST_ONLY), country_code
        )
        return list(qs.order_by("order", "id")[:limit])

    majors = _filtered_majors_for_search(
        q,
        country_code=country_code,
        limit=_MAJOR_SEARCH_DB_LIMIT,
        prefetch_faqs=False,
    )
    if len(majors) < 8:
        extra = _fuzzy_fallback_majors(
            q,
            country_code=country_code,
            exclude_ids={m.id for m in majors},
            limit=max(12, limit),
        )
        majors.extend(extra)

    ranked = rank_majors(
        majors,
        q,
        limit=max(limit, 40),
        intent=intent,
        target_degree=target_degree,
        fast=False,
    )
    results = [(m, sc) for m, sc in ranked if sc >= min_score]
    if not results and ranked:
        results = ranked[: min(5, len(ranked))]
    return [m for m, _ in results[:limit]]


def _majors_from_popularity_scores(
    scores: dict[str, float],
    *,
    country_code: str = "",
    limit: int = 8,
) -> list[Major]:
    if not scores:
        return []
    limit = max(1, int(limit or 8))
    ranked_slugs = sorted(scores, key=lambda slug: scores[slug], reverse=True)
    qs = active_major_queryset().only(*_MAJOR_LIST_ONLY)
    if country_code:
        qs = filter_majors_by_country(qs, country_code)
    slug_pool = ranked_slugs[: max(limit * 4, 24)]
    by_slug = {m.slug: m for m in qs.filter(slug__in=slug_pool)}

    best_by_title: dict[str, Major] = {}
    for slug in ranked_slugs:
        major = by_slug.get(slug)
        if not major:
            continue
        title_key = _normalize_persian(major.title or "").lower()
        prev = best_by_title.get(title_key)
        if not prev or scores.get(slug, 0) > scores.get(prev.slug, 0):
            best_by_title[title_key] = major

    ordered = sorted(
        best_by_title.values(),
        key=lambda m: scores.get(m.slug, 0),
        reverse=True,
    )
    return ordered[:limit]


def _fallback_featured_majors(
    *,
    country_code: str = "",
    limit: int = 8,
    exclude_slugs: Iterable[str] = (),
) -> list[Major]:
    limit = max(1, int(limit or 8))
    qs = active_major_queryset().only(*_MAJOR_BROWSE_ONLY)
    if country_code:
        qs = filter_majors_by_country(qs, country_code)
    exclude = {s for s in exclude_slugs if s}
    items = list(qs.exclude(slug__in=exclude).order_by("order", "id")[: limit * 2])
    return _dedupe_majors(items)[:limit]


def get_featured_majors(*, country_code: str = "", limit: int = 8) -> list[Major]:
    """رشته‌های پرطرفدار — اولویت با خروجی موتور ارزیابی، نه ترتیب ثابت DB."""
    from .evaluation_learning import get_popular_major_rankings

    limit = max(1, int(limit or 8))
    rankings = get_popular_major_rankings()
    if rankings.active:
        scores = dict(rankings.global_scores)
        if country_code:
            country_scores = rankings.by_country.get(country_code) or {}
            if country_scores:
                scores = dict(country_scores)
        popular = _majors_from_popularity_scores(
            scores,
            country_code=country_code,
            limit=limit,
        )
        if len(popular) >= min(3, limit):
            if len(popular) < limit:
                exclude = {m.slug for m in popular}
                popular.extend(
                    _fallback_featured_majors(
                        country_code=country_code,
                        limit=limit - len(popular),
                        exclude_slugs=exclude,
                    )
                )
            return popular[:limit]

    return _fallback_featured_majors(country_code=country_code, limit=limit)


def suggest_majors(
    q: str = "",
    *,
    country_code: str = "",
    limit: int = 8,
    intent: str = "",
    target_degree: str = "",
) -> list[Major]:
    return [m for m, _ in suggest_majors_ranked(
        q,
        country_code=country_code,
        limit=limit,
        intent=intent,
        target_degree=target_degree,
    )]


def suggest_majors_ranked(
    q: str = "",
    *,
    country_code: str = "",
    limit: int = 8,
    intent: str = "",
    target_degree: str = "",
) -> list[tuple[Major, float]]:
    """پیشنهاد سریع autocomplete — DB محدود + امتیاز سبک."""
    q = _normalize_query(q)
    if not q or len(q) < 2:
        featured = get_featured_majors(country_code=country_code, limit=limit)
        return [(m, float(m.order)) for m in featured]

    majors = _filtered_majors_for_search(
        q,
        country_code=country_code,
        limit=_MAJOR_SUGGEST_DB_LIMIT,
        prefetch_faqs=False,
    )
    if len(majors) < limit:
        extra = _fuzzy_fallback_majors(
            q,
            country_code=country_code,
            exclude_ids={m.id for m in majors},
            limit=limit,
        )
        seen = {m.id for m in majors}
        for m in extra:
            if m.id not in seen:
                majors.append(m)
                seen.add(m.id)

    return rank_majors(
        majors,
        q,
        limit=limit,
        intent=intent,
        target_degree=target_degree,
        fast=True,
    )


def split_search_results(
    q: str,
    *,
    country_code: str = "",
    university_slug: str = "",
    primary_limit: int = 1,
    related_limit: int = 24,
    min_score: float = 1.8,
    intent: str = "",
    target_degree: str = "",
) -> tuple[list[Major], list[Major], str | None]:
    """
    تفکیک نتیجه: بهترین تطابق‌ها (بالا) و رشته‌های مرتبط (پایین) بر اساس امتیاز.
    """
    q = _normalize_query(q)
    if not q:
        return [], [], None

    adaptive_min = 1.15 if len(q) <= 3 else min_score

    majors = _filtered_majors_for_search(
        q,
        country_code=country_code,
        university_slug=university_slug,
        limit=_MAJOR_SEARCH_DB_LIMIT,
        prefetch_faqs=False,
    )
    if len(majors) < 10:
        majors.extend(
            _fuzzy_fallback_majors(
                q,
                country_code=country_code,
                university_slug=university_slug,
                exclude_ids={m.id for m in majors},
                limit=24,
            )
        )
    ranked = rank_majors(
        majors,
        q,
        limit=max(related_limit + primary_limit + 10, 40),
        intent=intent,
        target_degree=target_degree,
        fast=True,
    )
    ranked = [(m, sc) for m, sc in ranked if sc >= adaptive_min]

    if not ranked:
        return [], [], None

    best_score = ranked[0][1]
    strong_cutoff = max(min_score * 1.1, best_score * 0.82, best_score - 2.5)
    related_cutoff = max(min_score * 1.05, best_score * 0.68)

    primary: list[Major] = []
    related: list[Major] = []

    for major, score in ranked:
        if score >= strong_cutoff and len(primary) < 8:
            primary.append(major)
        elif score >= related_cutoff and len(related) < min(related_limit, 8):
            related.append(major)

    if not primary:
        primary = [ranked[0][0]]
        related = [m for m, _ in ranked[1 : min(related_limit, 7) + 1]]

    primary = _dedupe_majors(primary)
    primary_ids = {m.id for m in primary}
    related = _dedupe_majors([m for m in related if m.id not in primary_ids])

    best_slug = primary[0].slug if primary else None
    return primary, related, best_slug


def related_majors_for_query(
    q: str,
    *,
    country_code: str = "",
    limit: int = 5,
    intent: str = "",
    target_degree: str = "",
) -> list[Major]:
    items = smart_search_majors(
        q,
        country_code=country_code,
        limit=limit,
        min_score=1.0,
        intent=intent,
        target_degree=target_degree,
    )
    if items:
        return items
    extras = _fuzzy_fallback_majors(
        q,
        country_code=country_code,
        limit=limit,
    )
    return extras[:limit]


MAJORS_PAGE_SIZE = 20
MAJORS_PAGE_SIZE_MAX = 40
FEATURED_MAJORS_SIDEBAR_LIMIT = 5


def list_majors_browse(
    *,
    country_code: str = "",
    university_slug: str = "",
    offset: int = 0,
    limit: int = MAJORS_PAGE_SIZE,
) -> tuple[list[Major], int, bool]:
    """صفحه‌بندی لیست رشته‌ها (بدون جستجو) — برای infinite scroll."""
    limit = max(1, min(int(limit or MAJORS_PAGE_SIZE), MAJORS_PAGE_SIZE_MAX))
    offset = max(0, int(offset or 0))
    qs = active_major_queryset().only(*_MAJOR_BROWSE_ONLY)
    if country_code:
        qs = filter_majors_by_country(qs, country_code)
    qs = _filter_majors_by_university(qs, university_slug)
    qs = qs.order_by("order", "id")
    key_parts = (country_code or "-", university_slug or "-")
    total = count_for_queryset("major", key_parts, qs)
    items = list(qs[offset : offset + limit])
    has_more = offset + len(items) < total
    return items, total, has_more
