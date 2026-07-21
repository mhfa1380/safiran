"""
جستجو و پیشنهاد هوشمند سوالات متداول.
امتیازدهی معنایی: نرمال‌سازی فارسی، مترادف‌ها، تطابق تقریبی و محبوبیت.
"""
import difflib
import math
import re
from typing import Iterable

from django.db.models import Q, QuerySet

from .models import FAQ

_PERSIAN_STOP = frozenset(
    {
        "از",
        "به",
        "با",
        "در",
        "که",
        "این",
        "آن",
        "را",
        "برای",
        "یا",
        "هم",
        "چه",
        "چگونه",
        "آیا",
        "چطور",
        "کدام",
        "یک",
        "است",
        "هست",
        "می",
        "میشود",
        "شود",
        "کنم",
        "کنید",
        "دارم",
        "دارد",
        "من",
        "ما",
        "شما",
    }
)

# گروه‌های مترادف — هر کلمه جستجو بقیه گروه را هم پوشش می‌دهد
_SYNONYM_GROUPS: tuple[frozenset[str], ...] = (
    frozenset({"ویزا", "visa", "ویزای", "اقامت", "سفارت", "embassy"}),
    frozenset({"بورسیه", "اسکالرشیپ", "scholarship", "فاند", "کمک", "هزینه"}),
    frozenset({"مدرک", "مدارک", "سند", "مدرک زبان", "ielts", "تافل", "toefl"}),
    frozenset({"مشاوره", "مشاور", "consultation", "جلسه", "رزرو"}),
    frozenset({"پذیرش", "اپلای", "apply", "دانشگاه", "تحصیل", "تحصیلی"}),
    frozenset({"کانادا", "canada", "آلمان", "germany", "چین", "china", "اسپانیا", "spain"}),
    frozenset({"همراه", "همسر", "خانواده", "فرزند", "وابسته"}),
    frozenset({"کار", "شغل", "درآمد", "پاره وقت"}),
    frozenset({"ارزیابی", "فرم", "شروع", "اقدام"}),
)

_ARABIC_TO_PERSIAN = str.maketrans(
    {
        "ك": "ک",
        "ي": "ی",
        "ى": "ی",
        "ة": "ه",
        "ؤ": "و",
        "إ": "ا",
        "أ": "ا",
        "ٱ": "ا",
        "٠": "0",
        "١": "1",
        "٢": "2",
        "٣": "3",
        "٤": "4",
        "٥": "5",
        "٦": "6",
        "٧": "7",
        "٨": "8",
        "٩": "9",
    }
)


def _normalize_persian(text: str) -> str:
    """یکسان‌سازی حروف و فاصله برای جستجوی بهتر فارسی."""
    text = (text or "").strip().translate(_ARABIC_TO_PERSIAN)
    text = text.replace("\u200c", " ").replace("\xa0", " ")
    text = re.sub(r"[\u064B-\u065F\u0670]", "", text)  # اعراب
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _normalize_query(q: str) -> str:
    return _normalize_persian(q)


def tokenize_query(q: str) -> list[str]:
    """استخراج توکن‌های معنادار از عبارت جستجو."""
    q = _normalize_query(q)
    if not q:
        return []
    parts = re.split(r"[\s,،؛.!?]+", q)
    tokens = []
    for part in parts:
        part = part.strip().lower()
        if len(part) < 2 or part in _PERSIAN_STOP:
            continue
        tokens.append(part)
    if not tokens and len(q) >= 2:
        tokens.append(q.lower())
    return tokens


def _expand_tokens(tokens: list[str]) -> list[str]:
    """گسترش توکن‌ها با مترادف‌های از پیش تعریف‌شده."""
    expanded: list[str] = []
    seen: set[str] = set()
    for token in tokens:
        for t in (token,):
            if t not in seen:
                seen.add(t)
                expanded.append(t)
        for group in _SYNONYM_GROUPS:
            if token in group:
                for word in group:
                    if word not in seen:
                        seen.add(word)
                        expanded.append(word)
    return expanded


def _words(text: str) -> list[str]:
    text = _normalize_persian(text).lower()
    return [w for w in re.split(r"[\s,،؛]+", text) if len(w) >= 2]


def _fuzzy_ratio(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    if a in b or b in a:
        return 1.0
    return difflib.SequenceMatcher(None, a, b).ratio()


def _token_matches(text: str, token: str) -> float:
    """امتیاز تطابق یک توکن در متن (۰ تا ۱)."""
    text_n = _normalize_persian(text).lower()
    token = token.lower()
    if not token:
        return 0.0
    if token in text_n:
        return 1.0
    best = 0.0
    for word in _words(text_n):
        if len(word) < 2:
            continue
        ratio = _fuzzy_ratio(token, word)
        if ratio > best:
            best = ratio
    if best >= 0.78:
        return best
    if len(token) >= 4 and token[:4] in text_n:
        return 0.65
    return 0.0


def _score_faq(faq: FAQ, tokens: list[str], full_q: str) -> float:
    """امتیاز تطابق یک سوال با عبارت جستجو."""
    if not tokens and not full_q:
        return 0.0

    question = _normalize_persian(faq.question or "").lower()
    answer = _normalize_persian(faq.answer or "").lower()
    keywords_raw = " ".join(faq.get_keywords_list())
    keywords = _normalize_persian(keywords_raw).lower()
    haystack = f"{question} {keywords} {answer}"

    score = 0.0
    full_lower = _normalize_query(full_q).lower()

    if full_lower:
        if full_lower in question:
            score += 15.0
        elif full_lower in keywords:
            score += 10.0
        elif full_lower in haystack:
            score += 7.0
        else:
            q_ratio = _fuzzy_ratio(full_lower, question)
            if q_ratio >= 0.55:
                score += q_ratio * 8.0

    expanded = _expand_tokens(tokens)
    matched_tokens = 0
    for token in expanded:
        t_score = _token_matches(question, token)
        if t_score >= 0.78:
            score += 5.0 * t_score
            matched_tokens += 1
        elif _token_matches(keywords, token) >= 0.78:
            score += 3.5
            matched_tokens += 1
        elif _token_matches(answer, token) >= 0.78:
            score += 2.0
            matched_tokens += 1
        elif _token_matches(haystack, token) >= 0.65:
            score += 0.8

    if tokens and matched_tokens == len(tokens):
        score += 3.0
    elif tokens and matched_tokens > 0:
        score += matched_tokens * 0.5

    if faq.category and tokens:
        cat_name = _normalize_persian(faq.category.name).lower()
        for token in tokens:
            if token in cat_name:
                score += 1.5

    if faq.is_featured:
        score += 1.2
    if faq.view_count:
        score += min(2.5, math.log1p(faq.view_count))

    return score


def active_faq_queryset() -> QuerySet:
    return FAQ.objects.filter(is_active=True).select_related("category")


def _faq_candidates(*, category_slug: str = "") -> list[FAQ]:
    qs = active_faq_queryset()
    if category_slug:
        qs = qs.filter(category__slug=category_slug, category__is_active=True)
    return list(qs[:500])


def filter_faqs(
    queryset: QuerySet | None = None,
    *,
    q: str = "",
    category_slug: str = "",
) -> QuerySet:
    """فیلتر ساده برای سازگاری؛ جستجوی هوشمند از smart_search_faqs استفاده کنید."""
    qs = queryset if queryset is not None else active_faq_queryset()
    if category_slug:
        qs = qs.filter(category__slug=category_slug, category__is_active=True)
    q = _normalize_query(q)
    if q:
        expanded = _expand_tokens(tokenize_query(q))
        token_q = Q()
        for token in expanded[:12]:
            token_q |= (
                Q(question__icontains=token)
                | Q(answer__icontains=token)
                | Q(search_keywords__icontains=token)
            )
        qs = qs.filter(Q(question__icontains=q) | Q(answer__icontains=q) | token_q)
    return qs.order_by("category__order", "order", "id")


def rank_faqs(faqs: Iterable[FAQ], q: str, *, limit: int = 8) -> list[tuple[FAQ, float]]:
    """مرتب‌سازی سوالات بر اساس امتیاز تطابق."""
    q = _normalize_query(q)
    tokens = tokenize_query(q)
    if not q:
        ranked = []
        for faq in faqs:
            score = (2.0 if faq.is_featured else 0.0) + min(3.0, math.log1p(faq.view_count))
            ranked.append((faq, score))
        ranked.sort(key=lambda x: (-x[1], x[0].order, x[0].id))
        return ranked[:limit]

    scored = [(_score_faq(faq, tokens, q), faq) for faq in faqs]
    scored = [(s, f) for s, f in scored if s > 0]
    scored.sort(key=lambda x: (-x[0], x[1].order, x[1].id))
    return [(f, s) for s, f in scored[:limit]]


def smart_search_faqs(
    q: str = "",
    *,
    category_slug: str = "",
    limit: int = 30,
    min_score: float = 2.0,
) -> list[FAQ]:
    """
    جستجوی هوشمند: همه سوالات امتیازدهی می‌شوند (نه فقط تطابق دقیق).
    حتی با غلط املایی یا واژه مترادف، نزدیک‌ترین سوالات برگردانده می‌شود.
    """
    faqs = _faq_candidates(category_slug=category_slug)
    q = _normalize_query(q)
    if not q:
        ranked = rank_faqs(faqs, "", limit=limit)
        return [f for f, _ in ranked]

    ranked = rank_faqs(faqs, q, limit=max(limit, 50))
    results = [(f, s) for f, s in ranked if s >= min_score]
    if not results and ranked:
        results = ranked[: min(5, len(ranked))]
    return [f for f, _ in results[:limit]]


def get_featured_faqs(*, category_slug: str = "", limit: int = 8) -> list[FAQ]:
    """
    سوالات پرتکرار: فقط مواردی که در ادمین تیک «سوالات پرتکرار» دارند.
  """
    qs = active_faq_queryset().filter(is_featured=True)
    if category_slug:
        qs = qs.filter(category__slug=category_slug, category__is_active=True)
    return list(qs.order_by("order", "id")[:limit])


def suggest_faqs(
    q: str = "",
    *,
    category_slug: str = "",
    limit: int = 6,
) -> list[FAQ]:
    """پیشنهاد سوالات برای autocomplete."""
    q = _normalize_query(q)
    if not q or len(q) < 2:
        faqs = _faq_candidates(category_slug=category_slug)
        featured = [f for f in faqs if f.is_featured]
        if featured:
            featured.sort(key=lambda f: (-f.view_count, f.order, f.id))
            return featured[:limit]
        faqs.sort(key=lambda f: (-f.view_count, f.order, f.id))
        return faqs[:limit]

    return smart_search_faqs(
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
) -> tuple[list[FAQ], list[FAQ], str | None]:
    """
    تفکیک نتیجه جستجو: بهترین تطابق (بالا) و سوالات مرتبط (پایین).
    برمی‌گرداند: (primary_faqs, related_faqs, best_slug)
    """
    q = _normalize_query(q)
    if not q:
        return [], [], None

    faqs = _faq_candidates(category_slug=category_slug)
    ranked = rank_faqs(faqs, q, limit=max(primary_limit + related_limit + 5, 30))
    ranked = [(f, s) for f, s in ranked if s >= min_score]

    if not ranked:
        related = related_faqs_for_query(q, category_slug=category_slug, limit=related_limit)
        return [], related, None

    primary = [f for f, _ in ranked[:primary_limit]]
    primary_ids = {f.id for f in primary}
    related = [f for f, _ in ranked[primary_limit : primary_limit + related_limit] if f.id not in primary_ids]

    if len(related) < related_limit:
        for f in related_faqs_for_query(q, category_slug=category_slug, limit=related_limit + 3):
            if f.id in primary_ids:
                continue
            if any(r.id == f.id for r in related):
                continue
            related.append(f)
            if len(related) >= related_limit:
                break

    best_slug = primary[0].slug if primary else None
    return primary, related, best_slug


def related_faqs_for_query(q: str, *, category_slug: str = "", limit: int = 5) -> list[FAQ]:
    """سوالات مرتبط وقتی جستجو نتیجه ضعیف یا خالی دارد."""
    items = smart_search_faqs(q, category_slug=category_slug, limit=limit, min_score=1.0)
    if items:
        return items
    faqs = _faq_candidates(category_slug=category_slug)
    return [f for f, _ in rank_faqs(faqs, q, limit=limit)]


def related_faqs(faq: FAQ, *, limit: int = 4) -> list[FAQ]:
    """سوالات مرتبط بر اساس یک سوال مشخص."""
    return related_faqs_for_query(faq.question, limit=limit + 1)[1:limit + 1] or list(
        active_faq_queryset()
        .filter(category_id=faq.category_id)
        .exclude(pk=faq.pk)[:limit]
    )
