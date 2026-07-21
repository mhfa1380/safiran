"""
جستجوی هوشمند محتوای مرتبط با یک کشور مقصد.
فقط FAQ، دانشگاه، رشته، دوره، وبلاگ و بخش‌های صفحه همان کشور را جستجو می‌کند.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Optional

from django.db.models import Q
from django.urls import reverse

from .faq_search import (
    _SYNONYM_GROUPS,
    _normalize_persian,
    _normalize_query,
    _token_matches,
    _words,
    rank_faqs,
    tokenize_query,
)
from .faq_seo import _plain_answer
from .major_search import _FUZZY_TYPO_MIN, _FUZZY_TYPO_STRONG, _best_query_match
from .models import BlogPost, Course, FAQ, Major, StudyCountry, University


_KIND_LABELS = {
    "section": "راهنمای کشور",
    "faq": "سوال متداول",
    "university": "دانشگاه",
    "major": "رشته تحصیلی",
    "course": "دوره",
    "blog": "مطلب وبلاگ",
}

# مترادف‌های مخصوص جستجو در صفحه کشور (ویزا، بورسیه، پذیرش، …)
_COUNTRY_SYNONYMS: tuple[frozenset[str], ...] = _SYNONYM_GROUPS + (
    frozenset({"ویزا", "visa", "ویزای", "اقامت", "سفارت", "پاسپورت", "passport"}),
    frozenset({"بورسیه", "اسکالرشیپ", "scholarship", "فاند", "کمک هزینه", "کمک‌هزینه"}),
    frozenset({"پذیرش", "اپلای", "apply", "application", "ثبت نام", "ثبت‌نام"}),
    frozenset({"هزینه", "شهریه", "tuition", "زندگی", "اقامت", "اجاره", "خواربار"}),
    frozenset({"دانشگاه", "uni", "university", "مدرسه", "کالج", "college"}),
    frozenset({"رشته", "major", "تحصیلی", "رشته‌ها"}),
    frozenset({"کار", "شغل", "پاره وقت", "part time", "درآمد"}),
    frozenset({"مدرک", "مدارک", "ielts", "تافل", "toefl", "زبان"}),
)

_KIND_WEIGHTS = {
    "faq": 1.15,
    "university": 1.08,
    "major": 1.05,
    "section": 1.0,
    "course": 0.98,
    "blog": 0.92,
}


@dataclass
class CountrySearchHit:
    kind: str
    title: str
    snippet: str
    url: str
    score: float
    badge: str = ""
    faq: Any = None
    search_blob: str = ""
    extra: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.badge:
            self.badge = _KIND_LABELS.get(self.kind, "")
        if not self.search_blob:
            self.search_blob = f"{self.title} {self.snippet}"


def _plain(text: str, *, max_len: int = 220) -> str:
    return _plain_answer(text, max_len=max_len)


def _expand_country_tokens(tokens: list[str]) -> list[str]:
    expanded: list[str] = []
    seen: set[str] = set()
    for token in tokens:
        if token not in seen:
            seen.add(token)
            expanded.append(token)
        for group in _COUNTRY_SYNONYMS:
            if token in group:
                for word in group:
                    if word not in seen:
                        seen.add(word)
                        expanded.append(word)
    return expanded


def _text_mentions_country(text: str, markers: set[str]) -> bool:
    hay = _normalize_persian(text).lower()
    if not hay:
        return False
    for marker in markers:
        if marker and marker in hay:
            return True
    return False


def _fuzzy_fallback_score(title: str, blob: str, q: str) -> float:
    """امتیاز کمکی وقتی تطابق دقیق صفر است — برای غلط املایی."""
    q = _normalize_query(q)
    if not q:
        return 0.0
    title_n = _normalize_persian(title or "").lower()
    blob_n = _normalize_persian(blob or "").lower()
    best = max(_best_query_match(q, title_n), _best_query_match(q, blob_n) * 0.9)
    if best < _FUZZY_TYPO_MIN:
        return 0.0
    weight = 16.0 if best >= _FUZZY_TYPO_STRONG else 11.0
    return best * weight


def _score_country_hit(
    hit: CountrySearchHit,
    tokens: list[str],
    full_q: str,
) -> float:
    title = _normalize_persian(hit.title or "").lower()
    snippet = _normalize_persian(hit.snippet or "").lower()
    blob = _normalize_persian(hit.search_blob or f"{hit.title} {hit.snippet}").lower()
    haystack = f"{title} {snippet} {blob}"

    score = 0.0
    full_lower = _normalize_query(full_q).lower()

    if full_lower:
        if full_lower == title:
            score += 22.0
        elif full_lower in title:
            score += 17.0
        elif full_lower in snippet:
            score += 11.0
        elif full_lower in blob:
            score += 8.0
        else:
            for part, weight in ((title, 14.0), (snippet, 9.0), (blob, 7.0)):
                fuzzy = _best_query_match(full_lower, part)
                if fuzzy >= _FUZZY_TYPO_STRONG:
                    score += fuzzy * weight
                    break
                if fuzzy >= _FUZZY_TYPO_MIN:
                    score += fuzzy * (weight * 0.72)
                    break

    expanded = _expand_country_tokens(tokens)
    core_tokens = tokens or tokenize_query(full_q)
    core_matched = 0

    for token in core_tokens:
        t_title = max(_token_matches(title, token), _best_query_match(token, title) * 0.95)
        if t_title >= 0.78:
            score += 6.0 * t_title
            core_matched += 1
        elif _token_matches(snippet, token) >= 0.78:
            score += 3.8
            core_matched += 1
        elif _token_matches(blob, token) >= 0.72:
            score += 2.4
            core_matched += 1
        elif _token_matches(blob, token) >= 0.55:
            score += 0.9
        elif _best_query_match(token, title) >= _FUZZY_TYPO_MIN:
            score += _best_query_match(token, title) * 4.5
            core_matched += 1

    for token in expanded:
        if token in core_tokens:
            continue
        if _token_matches(title, token) >= 0.72:
            score += 1.8
        elif _token_matches(blob, token) >= 0.65:
            score += 0.7

    if core_tokens and core_matched == len(core_tokens):
        score += 4.0
    elif core_tokens and core_matched > 0:
        score += core_matched * 0.75

    if hit.kind == "faq" and hit.faq:
        faq_rank = rank_faqs([hit.faq], full_q, limit=1)
        if faq_rank:
            score = max(score, faq_rank[0][1] * 1.05)

    if hit.kind == "section" and score > 0:
        for word in _words(title):
            if word in full_lower or any(_token_matches(word, t) >= 0.78 for t in core_tokens):
                score += 1.2
                break

    if score > 0:
        score *= _KIND_WEIGHTS.get(hit.kind, 1.0)

    return score


def get_study_country(country_code: str) -> Optional[StudyCountry]:
    code = (country_code or "").strip().lower()
    if not code:
        return None
    return StudyCountry.objects.filter(code=code, is_active=True).first()


def _country_faqs(country: StudyCountry) -> list[FAQ]:
    markers = country.get_search_markers()
    faqs = list(
        FAQ.objects.filter(is_active=True)
        .select_related("category")
        .order_by("order", "id")[:400]
    )
    return [
        f
        for f in faqs
        if _text_mentions_country(
            f"{f.question} {f.answer} {f.search_keywords} {f.detail_content}",
            markers,
        )
    ]


def _country_blog_q(country: StudyCountry) -> Q:
    q = Q()
    for marker in country.get_search_markers():
        if len(marker) >= 2:
            q |= Q(country_tag__icontains=marker)
    return q


def _section_hits(country: StudyCountry) -> list[CountrySearchHit]:
    from .country_immigration_pathway import pathway_search_blob

    sections = [
        ("مسیر مهاجرت", pathway_search_blob(country)),
        ("راهنمای کلی", country.description or country.intro),
        ("ویزا و اقامت", country.visa_info),
        ("پذیرش و اپلای", country.admission_info),
        ("هزینه و زندگی", country.living_info),
        ("بورسیه", country.scholarship_info),
        ("مزایا", "\n".join(country.get_pros_list())),
        ("معایب", "\n".join(country.get_cons_list())),
    ]
    hits: list[CountrySearchHit] = []
    page_url = country.get_absolute_url()
    for title, body in sections:
        plain = _plain(body, max_len=500)
        if not plain:
            continue
        section_title = f"{title} — {country.name}"
        anchor = "country-pathway" if title == "مسیر مهاجرت" else _slug_anchor(title)
        hits.append(
            CountrySearchHit(
                kind="section",
                title=section_title,
                snippet=plain,
                url=f"{page_url}#{anchor}",
                score=0.0,
                search_blob=f"{section_title} {plain}",
            )
        )
    return hits


def _slug_anchor(title: str) -> str:
    base = re.sub(r"[^\w\u0600-\u06FF]+", "-", title.strip())
    return base.strip("-").lower() or "section"


def build_country_index(country: StudyCountry) -> list[CountrySearchHit]:
    """همه آیتم‌های قابل جستجو برای یک کشور."""
    code = country.code
    hits: list[CountrySearchHit] = list(_section_hits(country))

    for faq in _country_faqs(country):
        keywords = " ".join(faq.get_keywords_list())
        answer_plain = _plain(faq.answer, max_len=400)
        hits.append(
            CountrySearchHit(
                kind="faq",
                title=faq.question,
                snippet=_plain(faq.answer),
                url=faq.get_absolute_url(),
                score=0.0,
                faq=faq,
                search_blob=f"{faq.question} {keywords} {answer_plain}",
            )
        )

    for uni in University.objects.filter(country=code).order_by("name_fa"):
        body = f"{uni.name_fa} {uni.name_en} {uni.city} {uni.short_description} {uni.description}"
        body_plain = _plain(body, max_len=600)
        hits.append(
            CountrySearchHit(
                kind="university",
                title=uni.name_fa,
                snippet=_plain(uni.short_description or uni.description or uni.city),
                url=reverse("school_detail", kwargs={"slug": uni.slug}),
                score=0.0,
                search_blob=body_plain,
                extra={"city": uni.city, "name_en": uni.name_en},
            )
        )

    for major in Major.objects.filter(is_active=True, country=code).order_by("order", "id"):
        slug_text = (major.slug or "").replace("-", " ")
        body = f"{major.title} {major.short_description} {major.description} {slug_text}"
        hits.append(
            CountrySearchHit(
                kind="major",
                title=major.title,
                snippet=_plain(major.short_description or major.description),
                url=reverse("major_details", kwargs={"slug": major.slug}),
                score=0.0,
                search_blob=_plain(body, max_len=500),
            )
        )

    for course in Course.objects.filter(is_active=True, country=code).order_by("order", "id"):
        body = f"{course.title} {course.short_description} {course.description}"
        hits.append(
            CountrySearchHit(
                kind="course",
                title=course.title,
                snippet=_plain(course.short_description or course.description),
                url=course.get_course_url(),
                score=0.0,
                search_blob=_plain(body, max_len=500),
            )
        )

    blog_q = _country_blog_q(country)
    if blog_q:
        for post in BlogPost.objects.filter(is_published=True).filter(blog_q).order_by("-created_at")[:30]:
            body = f"{post.title} {post.excerpt} {_plain(post.content, max_len=300)}"
            hits.append(
                CountrySearchHit(
                    kind="blog",
                    title=post.title,
                    snippet=_plain(post.excerpt or post.content),
                    url=reverse("blog_detail", kwargs={"slug": post.slug}),
                    score=0.0,
                    search_blob=_plain(body, max_len=500),
                )
            )

    return hits


def rank_country_hits(
    hits: list[CountrySearchHit],
    q: str,
    *,
    limit: int = 12,
    min_score: float = 1.6,
) -> list[tuple[CountrySearchHit, float]]:
    q = _normalize_query(q)
    tokens = tokenize_query(q)
    if not q:
        return [(h, 0.0) for h in hits[:limit]]

    scored: list[tuple[float, CountrySearchHit]] = []
    for hit in hits:
        score = _score_country_hit(hit, tokens, q)
        if score > 0:
            scored.append((score, hit))

    if not scored:
        for hit in hits:
            fs = _fuzzy_fallback_score(hit.title, hit.search_blob, q)
            if fs > 0:
                fs *= _KIND_WEIGHTS.get(hit.kind, 1.0)
                scored.append((fs, hit))

    scored.sort(key=lambda x: (-x[0], x[1].title))

    strong = [(s, h) for s, h in scored if s >= min_score]
    pool = strong if strong else scored[: max(limit, 5)]

    results: list[tuple[CountrySearchHit, float]] = []
    for score, hit in pool[:limit]:
        hit.score = score
        results.append((hit, score))
    return results


def smart_search_country(
    country_code: str,
    q: str = "",
    *,
    limit: int = 12,
    min_score: float = 1.6,
) -> list[CountrySearchHit]:
    country = get_study_country(country_code)
    if not country:
        return []
    index = build_country_index(country)
    q = _normalize_query(q)
    if not q:
        return index[:limit]
    ranked = rank_country_hits(index, q, limit=limit, min_score=min_score)
    return [h for h, _ in ranked]


def suggest_country(
    country_code: str,
    q: str = "",
    *,
    limit: int = 8,
) -> list[CountrySearchHit]:
    q = _normalize_query(q)
    country = get_study_country(country_code)
    if not country:
        return []
    if not q or len(q) < 2:
        suggestions: list[CountrySearchHit] = []
        for faq in _country_faqs(country)[:4]:
            suggestions.append(
                CountrySearchHit(
                    kind="faq",
                    title=faq.question,
                    snippet=_plain(faq.answer, max_len=80),
                    url=faq.get_absolute_url(),
                    score=0.0,
                    faq=faq,
                    search_blob=f"{faq.question} {' '.join(faq.get_keywords_list())}",
                )
            )
        for uni in University.objects.filter(country=country.code).order_by("name_fa")[:3]:
            suggestions.append(
                CountrySearchHit(
                    kind="university",
                    title=uni.name_fa,
                    snippet=uni.city,
                    url=reverse("school_detail", kwargs={"slug": uni.slug}),
                    score=0.0,
                    search_blob=f"{uni.name_fa} {uni.name_en} {uni.city}",
                )
            )
        return suggestions[:limit]
    return smart_search_country(country_code, q, limit=limit, min_score=1.2)


def split_country_search(
    country_code: str,
    q: str,
    *,
    primary_limit: int = 1,
    related_limit: int = 8,
) -> tuple[list[CountrySearchHit], list[CountrySearchHit]]:
    q = _normalize_query(q)
    if not q:
        return [], []

    country = get_study_country(country_code)
    if not country:
        return [], []

    index = build_country_index(country)
    ranked = rank_country_hits(
        index,
        q,
        limit=primary_limit + related_limit + 6,
        min_score=1.4,
    )

    if not ranked:
        # نزدیک‌ترین موارد حتی با امتیاز پایین
        weak = rank_country_hits(index, q, limit=related_limit, min_score=0.0)
        if weak:
            hits = [h for h, _ in weak]
            return hits[:primary_limit], hits[primary_limit : primary_limit + related_limit]
        fallback = index[:related_limit]
        return [], fallback

    hits = [h for h, _ in ranked]
    scores = [s for _, s in ranked]

    primary: list[CountrySearchHit] = []
    related: list[CountrySearchHit] = []

    if hits:
        primary = [hits[0]]
        if scores[0] < 2.0 and len(hits) > 1:
            # اگر بهترین تطابق ضعیف است، همه را در بخش «مرتبط» نشان بده
            related = hits[1 : primary_limit + related_limit]
        else:
            related = hits[primary_limit : primary_limit + related_limit]

    if len(related) < related_limit:
        seen_urls = {h.url for h in primary + related}
        for hit in index:
            if hit.url in seen_urls:
                continue
            related.append(hit)
            seen_urls.add(hit.url)
            if len(related) >= related_limit:
                break

    return primary, related
