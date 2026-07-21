"""
پیشنهاد مطالب مرتبط وبلاگ — امتیازدهی توکنی سبک (بدون ML و بدون خواندن HTML کامل).

الگوی رایج سایت‌های بزرگ: مجموعهٔ کوچک کاندید + شباهت عنوان/خلاصه/کلمات کلیدی + کش صفحه.
"""
from __future__ import annotations

import math
from typing import Iterable

from django.db.models import Q, QuerySet

from .faq_search import (
    _expand_tokens,
    _fuzzy_ratio,
    _normalize_persian,
    _normalize_query,
    _words,
    tokenize_query,
)
from .models import BlogPost
from .site_search import _score_text

_BLOG_ONLY_FIELDS = (
    "id",
    "slug",
    "title",
    "excerpt",
    "country_tag",
    "meta_keywords",
    "created_at",
)

# برچسب‌های عمومی که برای شباهت معنایی کم‌ارزش‌اند
_GENERIC_TAGS = frozenset({"خبری", "وبلاگ", "اخبار", "عمومی"})

# توکن‌های پرتکرار در همهٔ مطالب مهاجرت — وزن کمتر در شباهت
_COUNTRY_NAMES = frozenset(
    {
        "کانادا",
        "چین",
        "آلمان",
        "اسپانیا",
        "ایتالیا",
        "فرانسه",
        "انگلستان",
        "انگلیس",
        "استرالیا",
        "ترکیه",
        "اتریش",
        "هلند",
    }
)


def _countries_mentioned(text: str) -> list[str]:
    text_n = _normalize_persian(text or "").lower()
    return [name for name in _COUNTRY_NAMES if name in text_n]


_COMMON_TOPIC_TOKENS = frozenset(
    {
        "مهاجرت",
        "تحصیلی",
        "تحصیل",
        "دانشگاه",
        "دانشجویی",
        "دانشجو",
        "اپلای",
        "apply",
        "ویزا",
        "visa",
        "خارج",
        "کشور",
        "راهنمای",
        "راهنما",
        "نکات",
        "برای",
    }
)


_BLOG_LIST_FIELDS = _BLOG_ONLY_FIELDS + (
    "meta_title",
    "meta_description",
)

_BLOG_SEARCH_DB_LIMIT = 96
_BLOG_SUGGEST_DB_LIMIT = 40
_BLOG_FUZZY_POOL_LIMIT = 72
_SQL_TOKEN_CAP = 8
_FUZZY_TYPO_MIN = 0.42
_FUZZY_TYPO_STRONG = 0.62

_MIN_LIST_SCORE = 2.0
_MIN_LIST_SCORE_FUZZY = 0.8

_COUNTRY_TAG_ORDER = ("کانادا", "اسپانیا", "چین", "آلمان", "ایتالیا")


def active_blog_queryset() -> QuerySet[BlogPost]:
    return BlogPost.objects.filter(is_published=True).only(*_BLOG_ONLY_FIELDS)


def published_blog_list_queryset() -> QuerySet[BlogPost]:
    return BlogPost.objects.filter(is_published=True).only(*_BLOG_LIST_FIELDS).defer("content")


def _blog_search_q_tokens(q: str) -> tuple[str, list[str], list[str]]:
    q = _normalize_query(q)
    tokens = tokenize_query(q)
    expanded = _expand_tokens(tokens)
    return q, tokens, expanded


def _blog_base_queryset(*, tag: str = "") -> QuerySet[BlogPost]:
    qs = published_blog_list_queryset()
    tag = (tag or "").strip()
    if tag:
        qs = qs.filter(country_tag=tag)
    return qs


def _blog_core_search_q(q: str, tokens: list[str], expanded: list[str]) -> Q:
    clause = (
        Q(title__icontains=q)
        | Q(excerpt__icontains=q)
        | Q(slug__icontains=q)
        | Q(meta_title__icontains=q)
        | Q(meta_description__icontains=q)
        | Q(meta_keywords__icontains=q)
        | Q(country_tag__icontains=q)
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
            Q(title__icontains=token)
            | Q(excerpt__icontains=token)
            | Q(meta_keywords__icontains=token)
            | Q(country_tag__icontains=token)
        )
        if len(seen) <= _SQL_TOKEN_CAP:
            clause |= Q(slug__icontains=token)
    return clause


def _blog_content_search_q(q: str, tokens: list[str], expanded: list[str]) -> Q:
    """جستجو در متن کامل — فقط در SQL؛ بدون خواندن HTML در پایتون."""
    clause = Q(content__icontains=q)
    seen: set[str] = set()
    for token in (*tokens, *expanded):
        if len(token) < 2 or token in seen:
            continue
        seen.add(token)
        if len(seen) <= _SQL_TOKEN_CAP:
            clause |= Q(content__icontains=token)
    return clause


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
        if q_len <= 16 and len(word) >= q_len:
            shifts = len(word) - q_len + 1
            step = 1 if shifts <= 24 else max(1, shifts // 24)
            for i in range(0, shifts, step):
                chunk = word[i : i + q_len]
                best = max(best, _fuzzy_ratio(query, chunk))

    return best


def _filtered_blog_posts_for_search(
    q: str,
    *,
    tag: str = "",
    limit: int = _BLOG_SEARCH_DB_LIMIT,
) -> list[BlogPost]:
    """پیش‌فیلتر SQL — حداکثر ~۹۶ پست کاندید برای امتیازدهی."""
    qs = _blog_base_queryset(tag=tag)
    q_norm, tokens, expanded = _blog_search_q_tokens(q)
    if not q_norm:
        return list(qs.order_by("-created_at")[: max(1, limit)])

    limit = max(1, limit)
    core_q = _blog_core_search_q(q_norm, tokens, expanded)
    core = list(qs.filter(core_q).distinct().order_by("-created_at")[:limit])
    if len(core) >= max(14, limit // 2):
        return core[:limit]

    seen_ids = {p.id for p in core}
    need = limit - len(core)
    if need > 0:
        extra = list(
            qs.filter(_blog_content_search_q(q_norm, tokens, expanded))
            .exclude(id__in=seen_ids)
            .distinct()
            .order_by("-created_at")[:need]
        )
        core.extend(extra)
        seen_ids.update(p.id for p in extra)

    if len(core) >= max(10, limit // 3):
        return core[:limit]

    need = limit - len(core)
    if need > 0:
        fuzzy = _fuzzy_fallback_blog_posts(
            q_norm,
            tag=tag,
            exclude_ids=seen_ids,
            limit=need,
        )
        core.extend(fuzzy)
    return core[:limit]


def _fuzzy_fallback_blog_posts(
    q: str,
    *,
    tag: str = "",
    exclude_ids: set[int] | None = None,
    limit: int = 24,
) -> list[BlogPost]:
    exclude_ids = exclude_ids or set()
    qs = _blog_base_queryset(tag=tag)
    q_norm, tokens, expanded = _blog_search_q_tokens(q)

    pool_q = Q()
    if len(q_norm) >= 2:
        pool_q |= Q(title__icontains=q_norm[:2])
    for token in (*tokens, *expanded)[:5]:
        if len(token) >= 2:
            pool_q |= Q(title__icontains=token)

    pool: list[BlogPost] = []
    if pool_q:
        pool = list(qs.filter(pool_q).distinct().order_by("-created_at")[:_BLOG_FUZZY_POOL_LIMIT])
    if len(pool) < limit:
        extra = list(
            qs.exclude(id__in=[p.id for p in pool])
            .order_by("-created_at")[: max(0, _BLOG_FUZZY_POOL_LIMIT - len(pool))]
        )
        pool.extend(extra)

    scored: list[tuple[float, BlogPost]] = []
    for post in pool:
        if post.id in exclude_ids:
            continue
        title = _normalize_persian(post.title or "").lower()
        excerpt = _normalize_persian(post.excerpt or "").lower()
        fs = max(
            _best_query_match(q_norm, title),
            _best_query_match(q_norm, excerpt) * 0.92,
            _fuzzy_ratio(q_norm, title) * 0.85,
        )
        if fs >= _FUZZY_TYPO_MIN:
            scored.append((fs * 16.0, post))
    scored.sort(key=lambda pair: (-pair[0], -pair[1].created_at.timestamp()))
    return [post for _, post in scored[:limit]]


def _blog_tag_key(tag: str) -> str:
    return _normalize_persian((tag or "").strip()).lower()


def _blog_tag_matches(post_tag: str, filter_tag: str) -> bool:
    """تطابق برچسب با تحمل فاصله و غلط جزئی."""
    if not filter_tag:
        return True
    pt = _blog_tag_key(post_tag)
    ft = _blog_tag_key(filter_tag)
    if not pt:
        return False
    if ft == pt or ft in pt or pt in ft:
        return True
    return _fuzzy_ratio(ft, pt) >= 0.82


def unique_blog_tags() -> list[str]:
    """برچسب‌های یکتا برای فیلتر (بدون تکرار ناشی از فاصله یا یونیکد)."""
    seen: dict[str, str] = {}
    raw = (
        BlogPost.objects.filter(is_published=True)
        .exclude(country_tag="")
        .values_list("country_tag", flat=True)
    )
    for tag in raw:
        display = (tag or "").strip()
        if not display:
            continue
        key = _blog_tag_key(display)
        if key not in seen:
            seen[key] = display

    def _sort_key(label: str) -> tuple:
        norm = _normalize_persian(label)
        for idx, country in enumerate(_COUNTRY_TAG_ORDER):
            if country in norm:
                return (0, idx, label)
        return (1, 0, label)

    return sorted(seen.values(), key=_sort_key)


def _blog_list_haystack(post: BlogPost) -> str:
    """متن سبک برای امتیازدهی — بدون parse کردن content."""
    slug_words = (post.slug or "").replace("-", " ")
    return " ".join(
        p
        for p in (
            post.title,
            post.excerpt,
            post.meta_title,
            post.meta_description,
            post.meta_keywords,
            post.country_tag,
            slug_words,
        )
        if p
    )


def _score_blog_list_post(
    post: BlogPost,
    tokens: list[str],
    full_q: str,
    *,
    filter_tag: str = "",
) -> float:
    haystack = _blog_list_haystack(post)
    score = _score_text(
        haystack,
        post.title or "",
        tokens,
        full_q,
        title_boost=20.0,
    )

    title_n = _normalize_persian(post.title or "").lower()
    excerpt_n = _normalize_persian(post.excerpt or "").lower()
    if full_q:
        fq = _normalize_query(full_q).lower()
        slug_n = _normalize_persian((post.slug or "").replace("-", " ")).lower()
        if fq in slug_n:
            score += 4.0
        if title_n.startswith(fq):
            score += 22.0
        elif fq in title_n:
            score += 16.0
        elif fq in excerpt_n:
            score += 10.0
        else:
            fuzzy = _best_query_match(fq, title_n)
            if fuzzy >= _FUZZY_TYPO_STRONG:
                score += fuzzy * 14.0
            elif fuzzy >= _FUZZY_TYPO_MIN:
                score += fuzzy * 9.0

    keywords = _normalize_persian(post.meta_keywords or "").lower()
    for token in _expand_tokens(tokens)[:12]:
        if token in keywords:
            score += 2.5

    if filter_tag:
        if _blog_tag_matches(post.country_tag, filter_tag):
            score += 6.0
        else:
            score *= 0.12

    tag_n = _blog_tag_key(post.country_tag or "")
    for country in _COUNTRY_NAMES:
        c_low = _normalize_persian(country).lower()
        for token in tokens[:6]:
            if _fuzzy_ratio(token, c_low) < 0.78:
                continue
            if tag_n and (c_low in tag_n or _fuzzy_ratio(tag_n, c_low) >= 0.82):
                score += 14.0
            elif c_low in title_n:
                score += 9.0
            elif c_low in haystack.lower():
                score += 2.5
            break

    return score


def filter_and_rank_blog_posts(
    posts: Iterable[BlogPost],
    q: str = "",
    tag: str = "",
) -> list[BlogPost]:
    """جستجو در همه فیلدهای مهم + مرتب‌سازی بر اساس شباهت."""
    q = (q or "").strip()
    tag = (tag or "").strip()
    items = list(posts)

    if tag:
        items = [p for p in items if _blog_tag_matches(p.country_tag, tag)]

    if not q:
        items.sort(key=lambda p: p.created_at, reverse=True)
        return items

    tokens = tokenize_query(q)
    full_q = _normalize_query(q)
    scored: list[tuple[BlogPost, float]] = []
    min_score = _MIN_LIST_SCORE

    for post in items:
        score = _score_blog_list_post(post, tokens, full_q, filter_tag=tag)
        if score >= min_score:
            scored.append((post, score))

    if not scored:
        min_score = _MIN_LIST_SCORE_FUZZY
        for post in items:
            score = _score_blog_list_post(post, tokens, full_q, filter_tag=tag)
            if score >= min_score:
                scored.append((post, score))

    scored.sort(key=lambda pair: (-pair[1], -pair[0].created_at.timestamp()))
    return [post for post, _ in scored]


BLOG_PAGE_SIZE = 6
BLOG_PAGE_SIZE_MAX = 24
BLOG_SEARCH_LIMIT = 30


def fetch_and_rank_blog_posts(q: str = "", tag: str = "") -> list[BlogPost]:
    """جستجوی سریع: پیش‌فیلتر SQL + امتیازدهی روی زیرمجموعه محدود."""
    q = (q or "").strip()
    tag = (tag or "").strip()
    if not q:
        return list(_blog_base_queryset(tag=tag).order_by("-created_at"))
    candidates = _filtered_blog_posts_for_search(q, tag=tag, limit=_BLOG_SEARCH_DB_LIMIT)
    return filter_and_rank_blog_posts(candidates, q=q, tag=tag)


def browse_blog_posts(
    *,
    tag: str = "",
    offset: int = 0,
    limit: int = BLOG_PAGE_SIZE,
) -> tuple[list[BlogPost], int, bool]:
    """مرور بدون جستجو — صفحه‌بندی مستقیم در دیتابیس."""
    qs = _blog_base_queryset(tag=tag).order_by("-created_at")
    total = qs.count()
    offset = max(0, int(offset or 0))
    limit = max(1, min(int(limit or BLOG_PAGE_SIZE), BLOG_PAGE_SIZE_MAX))
    items = list(qs[offset : offset + limit])
    has_more = offset + len(items) < total
    return items, total, has_more


def slice_blog_posts(
    ranked: list[BlogPost],
    *,
    offset: int = 0,
    limit: int = BLOG_PAGE_SIZE,
) -> tuple[list[BlogPost], int, bool]:
    """برش لیست رتبه‌بندی‌شده برای infinite scroll."""
    limit = max(1, min(int(limit or BLOG_PAGE_SIZE), BLOG_PAGE_SIZE_MAX))
    offset = max(0, int(offset or 0))
    total = len(ranked)
    items = ranked[offset : offset + limit]
    has_more = offset + len(items) < total
    return items, total, has_more


def suggest_blog_posts(
    q: str = "",
    tag: str = "",
    *,
    limit: int = 8,
) -> list[dict]:
    """پیشنهاد زنده برای autocomplete وبلاگ."""
    from django.urls import reverse

    q = (q or "").strip()
    tag = (tag or "").strip()
    limit = max(1, min(int(limit or 8), 12))

    if q:
        candidates = _filtered_blog_posts_for_search(
            q, tag=tag, limit=_BLOG_SUGGEST_DB_LIMIT
        )
        ranked = filter_and_rank_blog_posts(candidates, q=q, tag=tag)
        if len(ranked) <= 2:
            alt = suggest_blog_query_correction(q, ranked=ranked)
            if alt:
                retry_candidates = _filtered_blog_posts_for_search(
                    alt, tag=tag, limit=_BLOG_SUGGEST_DB_LIMIT
                )
                retry = filter_and_rank_blog_posts(retry_candidates, q=alt, tag=tag)
                if len(retry) > len(ranked):
                    ranked = retry
    elif tag:
        ranked = list(_blog_base_queryset(tag=tag).order_by("-created_at")[:limit])
    else:
        ranked = list(published_blog_list_queryset().order_by("-created_at")[:limit])

    tokens = tokenize_query(q) if q else []
    full_q = _normalize_query(q) if q else ""
    payload: list[dict] = []

    for post in ranked[:limit]:
        score = _score_blog_list_post(post, tokens, full_q, filter_tag=tag) if q else 1.0
        excerpt = (post.excerpt or "").strip() or (post.meta_description or "")[:140]
        payload.append(
            {
                "slug": post.slug,
                "title": post.title,
                "tag": post.country_tag or "",
                "excerpt": excerpt,
                "smart_match": bool(q and score >= 5.0),
                "url": reverse("blog_detail", kwargs={"slug": post.slug}),
            }
        )

    return payload


def suggest_blog_query_correction(q: str, *, ranked: list[BlogPost] | None = None) -> str | None:
    """پیشنهاد اصلاح غلط املایی وقتی نتیجه ضعیف یا خالی است."""
    q = (q or "").strip()
    if len(q) < 3:
        return None
    from .site_query_correction import suggest_query_correction
    from .site_search import SearchHit
    from django.urls import reverse

    hits: list[SearchHit] = []
    if ranked:
        for post in ranked[:5]:
            hits.append(
                SearchHit(
                    type="blog",
                    title=post.title,
                    subtitle=post.country_tag or "",
                    url=reverse("blog_detail", kwargs={"slug": post.slug}),
                    score=5.0,
                )
            )
    return suggest_query_correction(q, hits=hits or None)


def _blog_haystack(post: BlogPost) -> str:
    return " ".join(
        filter(
            None,
            (post.title, post.excerpt, post.country_tag, post.meta_keywords),
        )
    )


def _seed_query(post: BlogPost) -> str:
    """متن مرجع برای شباهت — فقط فیلدهای سبک، نه content HTML."""
    parts = [post.title, post.excerpt, post.meta_keywords]
    tag = (post.country_tag or "").strip()
    if tag and tag not in _GENERIC_TAGS:
        parts.append(tag)
    return " ".join(p for p in parts if p)


def _token_idf_weights(candidates: list[BlogPost], tokens: list[str]) -> dict[str, float]:
    """توکن‌های نادر در مجموعهٔ کاندید امتیاز بیشتری می‌گیرند (سبک TF-IDF)."""
    n = len(candidates) or 1
    weights: dict[str, float] = {}
    for token in tokens:
        if token in _COMMON_TOPIC_TOKENS:
            base = 0.55
        else:
            base = 1.0
        haystacks = [_normalize_persian(_blog_haystack(p)).lower() for p in candidates]
        df = sum(1 for hay in haystacks if token in hay)
        idf = math.log((n + 1) / (df + 1)) + 1.0
        weights[token] = base * idf
    return weights


def _title_tokens(post: BlogPost) -> list[str]:
    return tokenize_query(post.title or "")


def _score_blog_post(
    post: BlogPost,
    tokens: list[str],
    full_q: str,
    *,
    source_tag: str = "",
    token_weights: dict[str, float] | None = None,
    source_title_tokens: list[str] | None = None,
) -> float:
    score = _score_text(_blog_haystack(post), post.title or "", tokens, full_q)
    tag = (post.country_tag or "").strip()
    title_n = _normalize_persian(post.title or "").lower()
    hay = _normalize_persian(_blog_haystack(post)).lower()

    if source_tag and len(source_tag) >= 2:
        tag_n = _normalize_persian(source_tag).lower()
        if tag == source_tag:
            score += 4.0
        elif tag_n in title_n:
            title_countries = _countries_mentioned(title_n)
            if len(title_countries) > 1 and tag and tag != source_tag:
                score += 2.0
                score *= 0.68
            else:
                score += 7.0
        elif tag and tag != source_tag and tag not in _GENERIC_TAGS:
            score *= 0.55
        elif tag_n in hay:
            score += 1.5

    if source_title_tokens:
        title_hits = sum(1 for t in source_title_tokens if t in title_n and t not in _COMMON_TOPIC_TOKENS)
        if title_hits >= 2:
            score += title_hits * 2.5
        elif title_hits == 1:
            score += 1.2

    if token_weights:
        hay = _normalize_persian(_blog_haystack(post)).lower()
        for token, weight in token_weights.items():
            if weight <= 1.0:
                continue
            if token in hay:
                score += (weight - 1.0) * 1.8

    return score


def rank_blog_posts(
    posts: Iterable[BlogPost],
    q: str,
    *,
    source_tag: str = "",
    source_title_tokens: list[str] | None = None,
    token_weights: dict[str, float] | None = None,
    limit: int = 8,
) -> list[tuple[BlogPost, float]]:
    tokens = tokenize_query(q)
    full_q = _normalize_query(q)
    scored: list[tuple[BlogPost, float]] = []
    for item in posts:
        score = _score_blog_post(
            item,
            tokens,
            full_q,
            source_tag=source_tag,
            token_weights=token_weights,
            source_title_tokens=source_title_tokens,
        )
        if score > 0:
            scored.append((item, score))
    scored.sort(key=lambda pair: -pair[1])
    return scored[:limit]


def _candidate_posts(
    post: BlogPost,
    tokens: list[str],
    *,
    max_candidates: int = 80,
) -> list[BlogPost]:
    """حداکثر ~۸۰ پست کاندید — یک کوئری فیلترشده + در صورت نیاز جدیدترین‌ها."""
    base = active_blog_queryset().exclude(pk=post.pk)
    seen: dict[int, BlogPost] = {}

    def absorb(qs: QuerySet[BlogPost], cap: int) -> None:
        for item in qs[:cap]:
            if item.pk not in seen:
                seen[item.pk] = item
            if len(seen) >= max_candidates:
                return

    source_tag = (post.country_tag or "").strip()
    if source_tag and source_tag not in _GENERIC_TAGS:
        absorb(base.filter(country_tag=source_tag).order_by("-created_at"), 35)

    if tokens:
        token_q = Q()
        for token in tokens[:6]:
            token_q |= (
                Q(title__icontains=token)
                | Q(excerpt__icontains=token)
                | Q(meta_keywords__icontains=token)
                | Q(country_tag__icontains=token)
            )
        absorb(base.filter(token_q).order_by("-created_at"), 50)

    if len(seen) < max_candidates:
        absorb(base.order_by("-created_at"), max_candidates)

    return list(seen.values())


def related_blog_posts(post: BlogPost, *, limit: int = 5) -> list[BlogPost]:
    """
    مطالب مرتبط واقعی برای صفحهٔ جزئیات وبلاگ.

    اولویت: شباهت عنوان/خلاصه/کلمات کلیدی، سپس همان برچسب، در نهایت جدیدترین‌ها.
    """
    seed = _seed_query(post)
    tokens = tokenize_query(seed)
    source_tag = (post.country_tag or "").strip()

    title_tokens = _title_tokens(post)
    candidates = _candidate_posts(post, tokens)
    token_weights = _token_idf_weights(candidates, tokens)
    ranked = rank_blog_posts(
        candidates,
        seed,
        source_tag=source_tag,
        source_title_tokens=title_tokens,
        token_weights=token_weights,
        limit=limit + 6,
    )

    if not ranked:
        return []

    best_score = ranked[0][1]
    min_score = 5.0 if len(tokens) >= 2 else 3.0
    cutoff = max(min_score, best_score * 0.82)

    results: list[BlogPost] = []
    for item, score in ranked:
        if item.pk == post.pk:
            continue
        if score < cutoff:
            continue
        results.append(item)
        if len(results) >= limit:
            break

    if results:
        return results

    # فقط وقتی هیچ تطابق معناداری نبود — همان برچسب یا جدیدترین
    seen_ids = {post.pk}
    fallback_qs = active_blog_queryset().exclude(pk=post.pk)
    if source_tag and source_tag not in _GENERIC_TAGS:
        tagged = list(fallback_qs.filter(country_tag=source_tag).order_by("-created_at")[:limit])
        if tagged:
            return tagged
    return list(fallback_qs.order_by("-created_at")[: min(limit, 3)])
