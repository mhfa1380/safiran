"""
نیازهای کاربری برای فیلتر هوشمند صفحه خدمات.
هر نیاز به دسته، کلمات کلیدی و خدمات مرتبط نگاشت شده است.
"""
from __future__ import annotations

from dataclasses import dataclass

from .models import Service
from .service_search import (
    _normalize_persian,
    _token_matches,
    rank_services,
    tokenize_query,
)


@dataclass(frozen=True)
class ServiceNeed:
    id: str
    label: str
    hint: str
    icon: str
    categories: tuple[str, ...]
    keywords: tuple[str, ...]
    priority_slugs: tuple[str, ...] = ()


SERVICE_NEEDS: tuple[ServiceNeed, ...] = (
    ServiceNeed(
        id="start",
        label="تازه شروع کرده‌ام",
        hint="مشاوره رایگان و انتخاب مسیر",
        icon="ti-flag-alt",
        categories=("moshavere-arezaye",),
        keywords=("شروع", "مشاوره", "اولیه", "ارزیابی", "مسیر", "کشور"),
        priority_slugs=("moshavere-raygan-avalieh", "arzyabi-takhasosi-parvandeh"),
    ),
    ServiceNeed(
        id="apply",
        label="پذیرش و اپلای دانشگاه",
        hint="مکاتبه، SOP و ثبت درخواست",
        icon="ti-book",
        categories=("paziresh-apply",),
        keywords=("پذیرش", "اپلای", "دانشگاه", "offer", "sop", "رزومه", "انگیزه"),
        priority_slugs=(
            "makatebe-ba-daneshgahha-va-asatid",
            "sabt-apply-va-peygiri-paziresh",
            "negaresh-angizeh-nameh-va-resumeh-tahsili",
        ),
    ),
    ServiceNeed(
        id="visa",
        label="ویزا و مدارک",
        hint="ترجمه، سفارت و مصاحبه",
        icon="ti-id-badge",
        categories=("visa-madarek",),
        keywords=("ویزا", "سفارت", "مدارک", "ترجمه", "مصاحبه", "مدرک"),
        priority_slugs=(
            "ekhoz-vizaye-daneshjooei",
            "amadegi-mosahebeh-sefart",
            "tarjomeh-rasmi-va-taid-madarek",
        ),
    ),
    ServiceNeed(
        id="scholarship",
        label="بورسیه و کمک‌هزینه",
        hint="شناسایی فرصت‌های مالی",
        icon="ti-crown",
        categories=("bourse-mali",),
        keywords=("بورسیه", "اسکالرشیپ", "fund", "کمک", "هزینه"),
        priority_slugs=("ekhoz-bourseh-tahsili",),
    ),
    ServiceNeed(
        id="budget",
        label="برنامه‌ریزی مالی تحصیل",
        hint="برآورد شهریه و سپرده",
        icon="ti-wallet",
        categories=("bourse-mali",),
        keywords=("هزینه", "بودجه", "مالی", "شهریه", "سپرده", "تعرفه"),
        priority_slugs=("barname-rizi-mali-tahsili",),
    ),
    ServiceNeed(
        id="settle",
        label="استقرار در کشور مقصد",
        hint="اسکان، ثبت‌نام و پشتیبانی",
        icon="ti-world",
        categories=("estghrar-pasokhbane",),
        keywords=("استقرار", "اسکان", "ورود", "اقامت", "پشتیبانی"),
        priority_slugs=("estghrar-va-askan-avalieh", "poshtibani-pas-az-vorood"),
    ),
    ServiceNeed(
        id="family",
        label="ویزای همراه خانواده",
        hint="همسر و فرزند",
        icon="ti-user",
        categories=("estghrar-pasokhbane", "visa-madarek"),
        keywords=("همراه", "همسر", "فرزند", "خانواده", "وابسته"),
        priority_slugs=("vizaye-hamrah-va-khanavadeh",),
    ),
    ServiceNeed(
        id="online",
        label="مشاوره آنلاین و پیگیری",
        hint="جلسه ویدیویی و گزارش پرونده",
        icon="ti-video-camera",
        categories=("moshavere-arezaye",),
        keywords=("آنلاین", "ویدیو", "پیگیری", "پرونده"),
        priority_slugs=("moshavere-online-va-peygiri-parvandeh",),
    ),
)

NEEDS_BY_ID = {n.id: n for n in SERVICE_NEEDS}


def parse_need_ids(raw: str) -> list[str]:
    if not raw:
        return []
    valid = set(NEEDS_BY_ID)
    return [p for p in raw.replace("،", ",").split(",") if p.strip() in valid]


def _service_haystack(service: Service) -> str:
    parts = [
        service.title or "",
        service.get_display_summary(),
        service.description or "",
        service.highlights or "",
        " ".join(service.get_keywords_list()),
    ]
    if service.category:
        parts.append(service.category.name)
        parts.append(service.category.slug)
    return _normalize_persian(" ".join(parts)).lower()


def _score_service_for_need(service: Service, need: ServiceNeed) -> float:
    score = 0.0
    haystack = _service_haystack(service)
    slug = (service.slug or "").lower()

    if service.category and service.category.slug in need.categories:
        score += 9.0

    if slug and slug in need.priority_slugs:
        score += 14.0

    for kw in need.keywords:
        token = kw.lower()
        if _token_matches(haystack, token) >= 0.78:
            score += 3.5
        elif token in haystack:
            score += 2.5

    return score


def _score_service_for_needs(service: Service, need_ids: list[str]) -> float:
    if not need_ids:
        return 0.0
    total = 0.0
    matched_needs = 0
    for need_id in need_ids:
        need = NEEDS_BY_ID.get(need_id)
        if not need:
            continue
        s = _score_service_for_need(service, need)
        if s >= 2.5:
            matched_needs += 1
        total += s
    if matched_needs >= 2:
        total += matched_needs * 2.0
    if matched_needs == len(need_ids) and len(need_ids) > 1:
        total += 4.0
    return total


def filter_services_by_needs(
    services: list[Service],
    need_ids: list[str],
    *,
    min_score: float = 3.0,
    limit: int = 30,
) -> list[tuple[Service, float, list[str]]]:
    """برگرداندن (service, score, matched_need_ids)."""
    if not need_ids:
        return []

    results: list[tuple[Service, float, list[str]]] = []
    for service in services:
        matched: list[str] = []
        total = 0.0
        for need_id in need_ids:
            need = NEEDS_BY_ID.get(need_id)
            if not need:
                continue
            s = _score_service_for_need(service, need)
            if s >= 2.5:
                matched.append(need_id)
                total += s
        if len(matched) >= 2:
            total += len(matched) * 2.0
        if len(matched) == len(need_ids) and len(need_ids) > 1:
            total += 4.0
        if total >= min_score and matched:
            results.append((service, total, matched))

    results.sort(key=lambda x: (-x[1], x[0].order, x[0].id))
    return results[:limit]


def smart_filter_services(
    *,
    q: str = "",
    need_ids: list[str] | None = None,
    category_slug: str = "",
    limit: int = 24,
) -> tuple[list[Service], list[Service], str | None, dict]:
    """
    فیلتر ترکیبی نیاز + جستجو + دسته.
    خروجی: primary_list, related_list, best_slug, meta
    """
    from .service_search import _service_candidates, split_search_results

    need_ids = need_ids or []
    meta: dict = {
        "need_ids": need_ids,
        "matched_count": 0,
        "message": "",
        "mode": "all",
    }

    candidates = _service_candidates(category_slug=category_slug)

    if q and need_ids:
        meta["mode"] = "needs_and_query"
        q_norm = _normalize_persian(q)
        need_query = " ".join(
            NEEDS_BY_ID[n].label for n in need_ids if n in NEEDS_BY_ID
        )
        combined_q = f"{q_norm} {need_query}"
        primary, related, best_slug = split_search_results(
            combined_q,
            category_slug=category_slug,
            primary_limit=3,
            related_limit=8,
        )
        need_ranked = filter_services_by_needs(
            primary + related,
            need_ids,
            min_score=2.0,
            limit=limit,
        )
        if need_ranked:
            primary = [s for s, _, _ in need_ranked[: max(3, len(need_ranked) // 2)]]
            primary_ids = {s.id for s in primary}
            related = [s for s, _, _ in need_ranked if s.id not in primary_ids]
            best_slug = primary[0].slug if primary else best_slug
        meta["matched_count"] = len(primary) + len(related)
        meta["message"] = _build_message(need_ids, q, meta["matched_count"])
        return primary, related, best_slug, meta

    if q:
        meta["mode"] = "query"
        primary, related, best_slug = split_search_results(
            q,
            category_slug=category_slug,
            primary_limit=2,
            related_limit=8,
        )
        meta["matched_count"] = len(primary) + len(related)
        meta["message"] = _build_message([], q, meta["matched_count"])
        return primary, related, best_slug, meta

    if need_ids:
        meta["mode"] = "needs"
        ranked = filter_services_by_needs(candidates, need_ids, min_score=3.0, limit=limit)
        if not ranked:
            ranked = filter_services_by_needs(candidates, need_ids, min_score=1.5, limit=limit)
        if ranked:
            split_at = min(6, max(2, len(ranked) // 2 + 1))
            primary = [s for s, _, _ in ranked[:split_at]]
            primary_ids = {s.id for s in primary}
            related = [s for s, _, _ in ranked[split_at:] if s.id not in primary_ids]
            best_slug = primary[0].slug if primary else None
            meta["matched_count"] = len(ranked)
            meta["message"] = _build_message(need_ids, "", meta["matched_count"])
            meta["need_matches"] = {s.id: matched for s, _, matched in ranked}
            return primary, related, best_slug, meta

        related = [s for s, _ in rank_services(candidates, " ".join(NEEDS_BY_ID[n].label for n in need_ids if n in NEEDS_BY_ID), limit=6)]
        meta["matched_count"] = 0
        meta["message"] = "خدمت دقیقی پیدا نشد؛ چند پیشنهاد نزدیک:"
        return [], related, None, meta

    meta["mode"] = "all"
    if category_slug:
        services = candidates
    else:
        services = candidates
    meta["matched_count"] = len(services)
    return services, [], None, meta


def _build_message(need_ids: list[str], q: str, count: int) -> str:
    parts = []
    if need_ids:
        labels = [NEEDS_BY_ID[n].label for n in need_ids if n in NEEDS_BY_ID]
        if labels:
            parts.append("نیاز: " + "، ".join(labels))
    if q:
        parts.append(f"جستجو: «{q}»")
    if count:
        parts.append(f"{count} خدمت مناسب")
    return " · ".join(parts) if parts else ""
