"""
جستجوی سراسری سایت — همه محتواها، صفحات ثابت و پیشنهاد زنده.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable

from django.db.models import Q
from django.urls import reverse

from .faq_search import (
    _expand_tokens,
    _fuzzy_ratio,
    _normalize_persian,
    _normalize_query,
    _token_matches,
    tokenize_query,
)
from .models import (
    BlogPost,
    Course,
    FAQ,
    Major,
    MonthlyAchievement,
    Service,
    StudyCountry,
    University,
)
from .search_highlight import append_highlight_param
from .site_navigation import _resolve_link, get_searchable_page_defs

TYPE_LABELS = {
    "page": "صفحه",
    "blog": "وبلاگ",
    "country": "کشور",
    "university": "دانشگاه",
    "major": "رشته",
    "course": "دوره",
    "service": "خدمت",
    "faq": "سوال",
    "achievement": "دستاورد",
}

TYPE_ICONS = {
    "page": "ti-home",
    "blog": "ti-pencil-alt",
    "country": "ti-world",
    "university": "ti-book",
    "major": "ti-layout",
    "course": "ti-blackboard",
    "service": "ti-briefcase",
    "faq": "ti-help-alt",
    "achievement": "ti-medall",
}

# اولویت نوع محتوا در پیشنهاد نوبار (بعد از امتیاز متنی)
TYPE_RANK_BOOST = {
    "country": 1.14,
    "service": 1.1,
    "page": 1.08,
    "university": 1.06,
    "faq": 1.04,
    "blog": 1.02,
    "major": 1.0,
    "course": 0.98,
    "achievement": 0.96,
}

@dataclass(frozen=True)
class SearchHit:
    type: str
    title: str
    subtitle: str
    url: str
    score: float
    smart_match: bool = False

    def to_dict(self, *, highlight_q: str = "") -> dict:
        url = append_highlight_param(self.url, highlight_q) if highlight_q else self.url
        return {
            "type": self.type,
            "type_label": TYPE_LABELS.get(self.type, self.type),
            "icon": TYPE_ICONS.get(self.type, "ti-search"),
            "title": self.title,
            "subtitle": self.subtitle,
            "url": url,
            "score": round(self.score, 2),
            "smart_match": self.smart_match,
        }


def _score_text(haystack: str, title: str, tokens: list[str], full_q: str, *, title_boost: float = 15.0) -> float:
    haystack = _normalize_persian(haystack or "").lower()
    title_n = _normalize_persian(title or "").lower()
    full_lower = _normalize_query(full_q).lower()
    score = 0.0

    if full_lower:
        if full_lower in title_n:
            score += title_boost
        elif full_lower in haystack:
            score += 7.0
        else:
            ratio = _fuzzy_ratio(full_lower, title_n)
            if ratio >= 0.55:
                score += ratio * 8.0

    expanded = _expand_tokens(tokens)
    matched = 0
    for token in expanded[:14]:
        t_title = _token_matches(title_n, token)
        if t_title >= 0.78:
            score += 5.0 * t_title
            matched += 1
        elif _token_matches(haystack, token) >= 0.78:
            score += 2.5
            matched += 1

    if matched >= 2 and tokens:
        score += min(4.0, matched * 0.8)
    return score


def _final_rank(hit: SearchHit) -> float:
    boost = TYPE_RANK_BOOST.get(hit.type, 1.0)
    smart = 3.5 if hit.smart_match else 0.0
    return hit.score * boost + smart


def _dedupe_hits(pool: list[SearchHit], limit: int) -> list[SearchHit]:
    seen_urls: set[str] = set()
    unique: list[SearchHit] = []
    for hit in pool:
        if hit.url in seen_urls:
            continue
        seen_urls.add(hit.url)
        unique.append(hit)
        if len(unique) >= limit:
            break
    return unique


def _static_hits() -> list[SearchHit]:
    hits = []
    for defn in get_searchable_page_defs():
        link = _resolve_link(defn)
        if not link:
            continue
        hits.append(
            SearchHit(
                type="page",
                title=defn.label,
                subtitle=defn.search_subtitle or "",
                url=link.url,
                score=0.0,
            )
        )
    return hits


def _collect_static(q: str, tokens: list[str], limit: int) -> list[SearchHit]:
    if not q:
        return _static_hits()[: min(4, limit)]
    results = []
    for defn in get_searchable_page_defs():
        link = _resolve_link(defn)
        if not link:
            continue
        haystack = f"{defn.label} {defn.search_subtitle} {defn.search_keywords}"
        score = _score_text(haystack, defn.label, tokens, q)
        if score <= 0:
            continue
        results.append(
            SearchHit(
                type="page",
                title=defn.label,
                subtitle=defn.search_subtitle or "",
                url=link.url,
                score=score,
                smart_match=score >= 5,
            )
        )
    results.sort(key=lambda h: -h.score)
    return results[:limit]


def _collect_blogs(q: str, tokens: list[str], limit: int) -> list[SearchHit]:
    qs = BlogPost.objects.filter(is_published=True)
    if q:
        token_q = Q()
        for token in tokens[:8]:
            token_q |= (
                Q(title__icontains=token)
                | Q(excerpt__icontains=token)
                | Q(country_tag__icontains=token)
                | Q(meta_keywords__icontains=token)
            )
        qs = qs.filter(Q(title__icontains=q) | Q(excerpt__icontains=q) | token_q)
    posts = list(qs.order_by("-created_at")[: max(limit, 12)])
    hits = []
    for post in posts:
        haystack = f"{post.title} {post.excerpt} {post.country_tag} {post.meta_keywords}"
        score = _score_text(haystack, post.title, tokens, q)
        if q and score <= 0:
            continue
        if not q:
            score = 1.0
        hits.append(
            SearchHit(
                type="blog",
                title=post.title,
                subtitle=post.country_tag or "وبلاگ",
                url=reverse("blog_detail", kwargs={"slug": post.slug}),
                score=score,
                smart_match=score >= 5,
            )
        )
    hits.sort(key=lambda h: -h.score)
    return hits[:limit]


def _collect_countries(q: str, tokens: list[str], limit: int) -> list[SearchHit]:
    qs = StudyCountry.objects.filter(is_active=True)
    if q:
        token_q = Q()
        for token in tokens[:8]:
            token_q |= Q(name__icontains=token) | Q(search_keywords__icontains=token)
        qs = qs.filter(Q(name__icontains=q) | Q(headline__icontains=q) | token_q)
    countries = list(qs.order_by("order", "id")[: max(limit, 10)])
    hits = []
    for country in countries:
        haystack = f"{country.name} {country.headline} {country.intro} {' '.join(country.get_keywords_list())}"
        score = _score_text(haystack, country.name, tokens, q)
        if q and score <= 0:
            continue
        if not q:
            score = 2.0 - country.order * 0.01
        hits.append(
            SearchHit(
                type="country",
                title=f"تحصیل در {country.name}",
                subtitle=country.headline[:80] if country.headline else "کشور مقصد",
                url=country.get_absolute_url(),
                score=score,
                smart_match=score >= 5,
            )
        )
    hits.sort(key=lambda h: -h.score)
    return hits[:limit]


def _collect_universities(q: str, tokens: list[str], limit: int) -> list[SearchHit]:
    qs = University.objects.all()
    if q:
        token_q = Q()
        for token in tokens[:8]:
            token_q |= (
                Q(name_fa__icontains=token)
                | Q(name_en__icontains=token)
                | Q(city__icontains=token)
            )
        qs = qs.filter(Q(name_fa__icontains=q) | Q(name_en__icontains=q) | token_q)
    rows = list(qs.order_by("name_fa")[: max(limit, 15)])
    hits = []
    for uni in rows:
        haystack = f"{uni.name_fa} {uni.name_en} {uni.city} {uni.short_description}"
        score = _score_text(haystack, uni.name_fa, tokens, q)
        if q and score <= 0:
            continue
        if not q:
            score = 1.0
        hits.append(
            SearchHit(
                type="university",
                title=uni.name_fa,
                subtitle=f"{uni.get_country_display()} — {uni.city}",
                url=reverse("school_detail", kwargs={"slug": uni.slug}),
                score=score,
                smart_match=score >= 5,
            )
        )
    hits.sort(key=lambda h: -h.score)
    return hits[:limit]


def _collect_majors(q: str, tokens: list[str], limit: int) -> list[SearchHit]:
    qs = Major.objects.filter(is_active=True)
    if q:
        token_q = Q()
        for token in tokens[:8]:
            token_q |= Q(title__icontains=token) | Q(short_description__icontains=token)
        qs = qs.filter(Q(title__icontains=q) | token_q)
    rows = list(qs.order_by("order", "id")[: max(limit, 12)])
    hits = []
    for major in rows:
        haystack = f"{major.title} {major.short_description}"
        score = _score_text(haystack, major.title, tokens, q)
        if q and score <= 0:
            continue
        if not q:
            score = 1.0
        hits.append(
            SearchHit(
                type="major",
                title=major.title,
                subtitle=major.get_country_display() if major.country else "رشته تحصیلی",
                url=reverse("major_details", kwargs={"slug": major.slug}),
                score=score,
                smart_match=score >= 5,
            )
        )
    hits.sort(key=lambda h: -h.score)
    return hits[:limit]


def _collect_courses(q: str, tokens: list[str], limit: int) -> list[SearchHit]:
    qs = Course.objects.filter(is_active=True)
    if q:
        token_q = Q()
        for token in tokens[:8]:
            token_q |= Q(title__icontains=token) | Q(short_description__icontains=token)
        qs = qs.filter(Q(title__icontains=q) | token_q)
    rows = list(qs.order_by("order", "id")[: max(limit, 10)])
    hits = []
    for course in rows:
        haystack = f"{course.title} {course.short_description}"
        score = _score_text(haystack, course.title, tokens, q)
        if q and score <= 0:
            continue
        if not q:
            score = 1.0
        hits.append(
            SearchHit(
                type="course",
                title=course.title,
                subtitle=course.price or "دوره آموزشی",
                url=course.get_course_url(),
                score=score,
                smart_match=score >= 5,
            )
        )
    hits.sort(key=lambda h: -h.score)
    return hits[:limit]


def _collect_services(q: str, tokens: list[str], limit: int) -> list[SearchHit]:
    qs = Service.objects.filter(is_active=True).select_related("category")
    if q:
        token_q = Q()
        for token in tokens[:8]:
            token_q |= (
                Q(title__icontains=token)
                | Q(search_keywords__icontains=token)
                | Q(short_description__icontains=token)
            )
        qs = qs.filter(Q(title__icontains=q) | token_q)
    rows = list(qs.order_by("-is_featured", "order", "id")[: max(limit, 12)])
    hits = []
    for svc in rows:
        haystack = f"{svc.title} {svc.get_display_summary()} {' '.join(svc.get_keywords_list())}"
        score = _score_text(haystack, svc.title, tokens, q)
        if not q:
            score = (3.0 if svc.is_featured else 1.0) + min(2.0, math.log1p(svc.view_count))
        if q and score <= 0:
            continue
        hits.append(
            SearchHit(
                type="service",
                title=svc.title,
                subtitle=svc.category.name if svc.category else "خدمات موسسه",
                url=f"{reverse('services')}#service-{svc.slug}",
                score=score,
                smart_match=score >= 5,
            )
        )
    hits.sort(key=lambda h: -h.score)
    return hits[:limit]


def _collect_faqs(q: str, tokens: list[str], limit: int) -> list[SearchHit]:
    qs = FAQ.objects.filter(is_active=True).select_related("category")
    if q:
        token_q = Q()
        for token in tokens[:8]:
            token_q |= (
                Q(question__icontains=token)
                | Q(search_keywords__icontains=token)
                | Q(answer__icontains=token)
            )
        qs = qs.filter(Q(question__icontains=q) | token_q)
    rows = list(qs.order_by("-is_featured", "order", "id")[: max(limit, 12)])
    hits = []
    for faq in rows:
        answer_snip = (faq.answer or "")[:280]
        haystack = f"{faq.question} {answer_snip} {' '.join(faq.get_keywords_list())}"
        score = _score_text(haystack, faq.question, tokens, q)
        if not q:
            score = (3.0 if faq.is_featured else 1.0) + min(2.0, math.log1p(faq.view_count))
        if q and score <= 0:
            continue
        slug = faq.slug or str(faq.pk)
        if faq.category_id and faq.category:
            faq_url = f"{reverse('faq_category', kwargs={'category_slug': faq.category.slug})}#faq-{slug}"
        else:
            faq_url = f"{reverse('faq')}#faq-{slug}"
        hits.append(
            SearchHit(
                type="faq",
                title=faq.question,
                subtitle=faq.category.name if faq.category else "سوالات متداول",
                url=faq_url,
                score=score,
                smart_match=score >= 5,
            )
        )
    hits.sort(key=lambda h: -h.score)
    return hits[:limit]


def _collect_achievements(q: str, tokens: list[str], limit: int) -> list[SearchHit]:
    qs = MonthlyAchievement.objects.filter(is_active=True)
    if q:
        token_q = Q()
        for token in tokens[:8]:
            token_q |= (
                Q(title__icontains=token)
                | Q(person_name__icontains=token)
                | Q(search_keywords__icontains=token)
            )
        qs = qs.filter(Q(title__icontains=q) | Q(person_name__icontains=q) | token_q)
    rows = list(qs.order_by("-is_featured", "order", "-created_at")[: max(limit, 10)])
    hits = []
    for ach in rows:
        haystack = f"{ach.person_name} {ach.title} {ach.description} {' '.join(ach.get_keywords_list())}"
        score = _score_text(haystack, f"{ach.person_name} {ach.title}", tokens, q)
        if q and score <= 0:
            continue
        if not q:
            score = 2.0 if ach.is_featured else 1.0
        hits.append(
            SearchHit(
                type="achievement",
                title=ach.title,
                subtitle=ach.person_role or ach.person_name,
                url=ach.get_absolute_url(),
                score=score,
                smart_match=score >= 5,
            )
        )
    hits.sort(key=lambda h: -h.score)
    return hits[:limit]


def site_search(
    q: str = "",
    *,
    limit: int = 12,
    include_courses: bool = True,
    per_type: int | None = None,
) -> list[SearchHit]:
    """جستجوی یکپارچه در تمام بخش‌های سایت."""
    q_norm = _normalize_query(q)
    tokens = tokenize_query(q_norm)
    cap = per_type if per_type is not None else max(3, limit // 3)

    if not q_norm:
        pool: list[SearchHit] = []
        pool.extend(_collect_static("", tokens, 4))
        pool.extend(_collect_services("", tokens, 3))
        pool.extend(_collect_faqs("", tokens, 2))
        pool.extend(_collect_countries("", tokens, 3))
        if include_courses:
            pool.extend(_collect_courses("", tokens, 2))
        pool.sort(key=lambda h: -_final_rank(h))
        return pool[:limit]

    pool: list[SearchHit] = []
    pool.extend(_collect_static(q_norm, tokens, cap))
    pool.extend(_collect_countries(q_norm, tokens, cap))
    pool.extend(_collect_services(q_norm, tokens, cap))
    pool.extend(_collect_faqs(q_norm, tokens, cap))
    pool.extend(_collect_blogs(q_norm, tokens, cap))
    pool.extend(_collect_universities(q_norm, tokens, cap))
    pool.extend(_collect_majors(q_norm, tokens, cap))
    pool.extend(_collect_achievements(q_norm, tokens, cap))
    if include_courses:
        pool.extend(_collect_courses(q_norm, tokens, cap))

    pool.sort(key=lambda h: (-_final_rank(h), h.title))
    if not pool:
        return site_search("", limit=limit, include_courses=include_courses)

    return _dedupe_hits(pool, limit)


def suggest_site_search(
    q: str = "",
    *,
    limit: int = 8,
    include_courses: bool = True,
) -> list[SearchHit]:
    """پیشنهاد سریع برای autocomplete نوبار — کاندید بیشتر، رتبه‌بندی سراسری."""
    q_norm = _normalize_query(q)
    if not q_norm:
        return site_search("", limit=limit, include_courses=include_courses)
    cap = max(6, limit + 2)
    return site_search(
        q_norm,
        limit=limit,
        include_courses=include_courses,
        per_type=cap,
    )


def group_hits(hits: Iterable[SearchHit], *, highlight_q: str = "") -> list[dict]:
    """گروه‌بندی نتایج برای نمایش در پنل جستجو."""
    groups: dict[str, list[dict]] = {}
    order: list[str] = []
    for hit in hits:
        if hit.type not in groups:
            groups[hit.type] = []
            order.append(hit.type)
        groups[hit.type].append(hit.to_dict(highlight_q=highlight_q))
    return [
        {
            "type": t,
            "type_label": TYPE_LABELS.get(t, t),
            "items": groups[t],
        }
        for t in order
    ]
