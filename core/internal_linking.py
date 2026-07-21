"""
لینک‌سازی داخلی هدفمند برای صفحات پرترافیک GSC و کمک به ایندکس صفحات Discovered.
"""
from __future__ import annotations

from dataclasses import dataclass

from django.urls import reverse

from .gsc_indexing import get_gsc_not_indexed_slugs
from .models import BlogPost, Major, University

# اولویت بر اساس Performance و Queries در GSC (۳ ماه اخیر)
PRIORITY_UNIVERSITY_SLUGS: tuple[str, ...] = (
    "peking-university",
    "fudan-university",
    "universitat-de-valencia",
    "universidad-complutense-madrid",
    "sichuan-university",
    "sun-yat-sen-university",
    "hunan-university",
    "university-of-windsor",
    "concordia-university",
    "universidad-de-granada",
    "beihang-university",
    "upc-barcelona-tech",
    "university-of-alberta",
    "memorial-university",
    "universidad-de-murcia",
    "xiamen-university",
    "universite-de-montreal",
    "york-university",
    "universidad-de-oviedo",
    "universidade-de-santiago-de-compostela",
    "university-of-victoria",
    "university-of-saskatchewan",
    "university-of-british-columbia",
    "western-university",
    "east-china-normal-university",
    "chongqing-university",
)

PRIORITY_MAJOR_SLUGS: tuple[str, ...] = (
    "canada-علوم-شناختی",
    "canada-علوم-سیاسی",
    "canada-مهندسی-مواد-و-متالورژی",
    "canada-هوش-مصنوعی",
    "china-علوم-کامپیوتر-هوش-مصنوعی",
    "china-کامپیوتر",
    "china-داروسازی-بالینی",
    "spain-حقوق",
    "spain-کامپیوتر-شبکه",
    "canada-علوم-تربیتی",
    "canada-علوم-اعصاب",
    "china-مهندسی-هوافضا",
    "spain-گردشگری",
    "canada-مهندسی-محیط-زیست",
    "china-بیوانفورماتیک",
    "spain-روانشناسی-بالینی",
    "canada-امنیت-سایبری",
    "china-حقوق-بینالملل",
)

PRIORITY_BLOG_SLUGS: tuple[str, ...] = (
    "china-csc-scholarship-application-guide-2026",
    "study-abroad-without-language-certificate",
    "china-cost-living-beijing-shanghai-guangzhou-2025",
    "china-student-visa-x1-x2-requirements-2025",
    "spain-student-visa-type-d-checklist-2025",
    "spain-tapas-paella-regional-food-student-guide",
    "local-food-guide-canada-spain-china-students",
    "halal-food-muslim-students-canada-spain-china",
)

# لینک‌های منابع از پست‌های پرترافیک به صفحات هدف
BLOG_RESOURCE_SLUGS: dict[str, dict[str, tuple[str, ...]]] = {
    "china-csc-scholarship-application-guide-2026": {
        "universities": (
            "peking-university",
            "fudan-university",
            "sichuan-university",
            "sun-yat-sen-university",
            "beihang-university",
        ),
        "majors": ("china-کامپیوتر", "china-داروسازی-بالینی", "china-علوم-کامپیوتر-هوش-مصنوعی"),
    },
    "study-abroad-without-language-certificate": {
        "universities": (
            "universidad-complutense-madrid",
            "universidad-de-granada",
            "sichuan-university",
            "hunan-university",
        ),
        "majors": ("spain-حقوق", "china-کامپیوتر", "canada-علوم-تربیتی"),
    },
    "china-cost-living-beijing-shanghai-guangzhou-2025": {
        "universities": (
            "peking-university",
            "fudan-university",
            "shanghai-jiao-tong-university",
            "east-china-normal-university",
        ),
        "majors": ("china-کامپیوتر", "china-مهندسی-شهرسازی"),
    },
    "china-student-visa-x1-x2-requirements-2025": {
        "universities": ("peking-university", "xiamen-university", "chongqing-university"),
        "majors": ("china-داروسازی-بالینی", "china-پرستاری"),
    },
    "spain-student-visa-type-d-checklist-2025": {
        "universities": (
            "universitat-de-valencia",
            "universidad-complutense-madrid",
            "universidad-de-granada",
            "universidad-de-oviedo",
        ),
        "majors": ("spain-حقوق", "spain-گردشگری", "spain-کامپیوتر-شبکه"),
    },
    "spain-tapas-paella-regional-food-student-guide": {
        "universities": ("universitat-de-valencia", "universidad-de-granada", "universidad-de-murcia"),
        "majors": ("spain-گردشگری", "spain-مدیریت-هتل-و-مهماننوازی"),
    },
    "local-food-guide-canada-spain-china-students": {
        "universities": (
            "university-of-windsor",
            "concordia-university",
            "universitat-de-valencia",
            "peking-university",
        ),
        "majors": ("canada-تغذیه", "spain-گردشگری", "china-صنایع-غذایی"),
    },
    "halal-food-muslim-students-canada-spain-china": {
        "universities": ("memorial-university", "universidad-de-granada", "sichuan-university"),
        "majors": ("canada-تغذیه", "spain-حقوق"),
    },
}

_UNI_BY_COUNTRY: dict[str, tuple[str, ...]] = {
    "china": (
        "peking-university",
        "fudan-university",
        "sichuan-university",
        "sun-yat-sen-university",
        "hunan-university",
        "beihang-university",
        "xiamen-university",
        "chongqing-university",
        "east-china-normal-university",
    ),
    "canada": (
        "university-of-windsor",
        "concordia-university",
        "memorial-university",
        "university-of-alberta",
        "universite-de-montreal",
        "york-university",
        "university-of-british-columbia",
        "western-university",
    ),
    "spain": (
        "universitat-de-valencia",
        "universidad-complutense-madrid",
        "universidad-de-granada",
        "universidad-de-murcia",
        "universidad-de-oviedo",
        "upc-barcelona-tech",
        "universidade-de-santiago-de-compostela",
    ),
}

_MAJOR_BY_COUNTRY: dict[str, tuple[str, ...]] = {
    "china": tuple(s for s in PRIORITY_MAJOR_SLUGS if s.startswith("china-")),
    "canada": tuple(s for s in PRIORITY_MAJOR_SLUGS if s.startswith("canada-")),
    "spain": tuple(s for s in PRIORITY_MAJOR_SLUGS if s.startswith("spain-")),
}

_UNI_FIELDS = ("slug", "name_fa", "name_en", "city", "country", "type", "image", "world_rank")
_MAJOR_FIELDS = ("slug", "title", "short_description", "country", "image")


@dataclass(frozen=True)
class InternalLink:
    label: str
    url: str
    kind: str  # university | major | blog | page


@dataclass(frozen=True)
class InternalLinkGroup:
    title: str
    links: tuple[InternalLink, ...]


def _uni_url(slug: str) -> str:
    return reverse("school_detail", kwargs={"slug": slug})


def _major_url(slug: str) -> str:
    return reverse("major_details", kwargs={"slug": slug})


def _blog_url(slug: str) -> str:
    return reverse("blog_detail", kwargs={"slug": slug})


def _fetch_universities(slugs: tuple[str, ...] | list[str], *, exclude: str = "") -> list[University]:
    ordered = [s for s in slugs if s and s != exclude]
    if not ordered:
        return []
    by_slug = {
        u.slug: u
        for u in University.objects.filter(slug__in=ordered).only(*_UNI_FIELDS)
    }
    return [by_slug[s] for s in ordered if s in by_slug]


def _fetch_majors(slugs: tuple[str, ...] | list[str], *, exclude: str = "") -> list[Major]:
    ordered = [s for s in slugs if s and s != exclude]
    if not ordered:
        return []
    by_slug = {
        m.slug: m
        for m in Major.objects.filter(slug__in=ordered, is_active=True).only(*_MAJOR_FIELDS)
    }
    return [by_slug[s] for s in ordered if s in by_slug]


def _uni_links(universities: list[University]) -> tuple[InternalLink, ...]:
    return tuple(
        InternalLink(label=u.name_fa, url=_uni_url(u.slug), kind="university") for u in universities
    )


def _major_links(majors: list[Major]) -> tuple[InternalLink, ...]:
    return tuple(
        InternalLink(label=m.title, url=_major_url(m.slug), kind="major") for m in majors
    )


def _merge_priority_slugs(
    gsc_slugs: tuple[str, ...],
    country_slugs: tuple[str, ...],
    global_slugs: tuple[str, ...],
    *,
    exclude_slug: str = "",
) -> list[str]:
    """GSC not-indexed اول، سپس اولویت ثابت کشور، سپس لیست سراسری."""
    seen: set[str] = set()
    ordered: list[str] = []
    for slug in (*gsc_slugs, *country_slugs, *global_slugs):
        if not slug or slug == exclude_slug or slug in seen:
            continue
        seen.add(slug)
        ordered.append(slug)
    return ordered


def get_priority_related_universities(
    *,
    country: str,
    exclude_slug: str = "",
    limit: int = 6,
) -> list[University]:
    """دانشگاه‌های هم‌کشور با اولویت GSC، سپس پرکردن از دیتابیس."""
    gsc = get_gsc_not_indexed_slugs()
    gsc_country = tuple(s for s in gsc["universities"] if s != exclude_slug)
    country_slugs = _UNI_BY_COUNTRY.get(country, ())
    priority = _merge_priority_slugs(
        gsc_country,
        country_slugs,
        PRIORITY_UNIVERSITY_SLUGS,
        exclude_slug=exclude_slug,
    )
    found = _fetch_universities(priority[: limit * 2], exclude=exclude_slug)
    if len(found) >= limit:
        return found[:limit]

    seen = {u.slug for u in found}
    extra = (
        University.objects.filter(country=country)
        .exclude(slug__in=seen | {exclude_slug})
        .only(*_UNI_FIELDS)
        .order_by("world_rank_num", "name_fa")[: limit - len(found)]
    )
    return found + list(extra)


def get_priority_related_majors(
    *,
    country: str,
    exclude_slug: str = "",
    limit: int = 6,
) -> list[Major]:
    country_slugs = _MAJOR_BY_COUNTRY.get(country, ())
    gsc = get_gsc_not_indexed_slugs()
    gsc_country = tuple(
        s for s in gsc["majors"] if s.startswith(f"{country}-") and s != exclude_slug
    )
    priority = _merge_priority_slugs(
        gsc_country,
        country_slugs,
        PRIORITY_MAJOR_SLUGS,
        exclude_slug=exclude_slug,
    )
    found = _fetch_majors(priority[: limit * 2], exclude=exclude_slug)
    if len(found) >= limit:
        return found[:limit]

    seen = {m.slug for m in found}
    extra = (
        Major.objects.filter(is_active=True, country=country)
        .exclude(slug__in=seen | {exclude_slug})
        .only(*_MAJOR_FIELDS)
        .order_by("order", "id")[: limit - len(found)]
    )
    return found + list(extra)


def get_index_discovery_groups() -> list[InternalLinkGroup]:
    """بخش راهنمای مسیرها در صفحه اصلی."""
    groups: list[InternalLinkGroup] = []
    gsc = get_gsc_not_indexed_slugs()

    gsc_unis = _fetch_universities(gsc["universities"][:10])
    if gsc_unis:
        groups.append(
            InternalLinkGroup(
                title="دانشگاه‌های پیشنهادی برای مطالعه",
                links=_uni_links(gsc_unis),
            )
        )

    gsc_majors = _fetch_majors(gsc["majors"][:10])
    if gsc_majors:
        groups.append(
            InternalLinkGroup(
                title="رشته‌های پیشنهادی",
                links=_major_links(gsc_majors),
            )
        )

    for code, label in (("china", "چین"), ("canada", "کانادا"), ("spain", "اسپانیا")):
        unis = _fetch_universities(_UNI_BY_COUNTRY.get(code, ())[:6])
        if unis:
            groups.append(
                InternalLinkGroup(
                    title=f"دانشگاه‌های پرجستجو در {label}",
                    links=_uni_links(unis),
                )
            )

    majors = _fetch_majors(PRIORITY_MAJOR_SLUGS[:8])
    if majors:
        groups.append(
            InternalLinkGroup(
                title="رشته‌های پرطرفدار",
                links=_major_links(majors),
            )
        )

    blogs = list(
        BlogPost.objects.filter(is_published=True, slug__in=PRIORITY_BLOG_SLUGS)
        .only("slug", "title")
        .order_by("-updated_at")[:6]
    )
    slug_order = {s: i for i, s in enumerate(PRIORITY_BLOG_SLUGS)}
    blogs.sort(key=lambda b: slug_order.get(b.slug, 99))
    if blogs:
        groups.append(
            InternalLinkGroup(
                title="راهنماهای کاربردی",
                links=tuple(
                    InternalLink(label=b.title, url=_blog_url(b.slug), kind="blog") for b in blogs
                ),
            )
        )

    page_links = (
        InternalLink("خدمات موسسه", reverse("services"), "page"),
        InternalLink("ارزیابی هوشمند رایگان", reverse("evaluation"), "page"),
        InternalLink("همه دانشگاه‌ها", reverse("schools_list"), "page"),
        InternalLink("همه رشته‌ها", reverse("majors"), "page"),
    )
    groups.append(InternalLinkGroup(title="شروع سریع", links=page_links))
    return groups


def get_services_discovery_groups() -> list[InternalLinkGroup]:
    """لینک به صفحات پربازدید از صفحه خدمات."""
    groups: list[InternalLinkGroup] = []
    unis = _fetch_universities(PRIORITY_UNIVERSITY_SLUGS[:8])
    if unis:
        groups.append(InternalLinkGroup(title="دانشگاه‌های محبوب", links=_uni_links(unis)))
    majors = _fetch_majors(PRIORITY_MAJOR_SLUGS[:6])
    if majors:
        groups.append(InternalLinkGroup(title="رشته‌های پرجستجو", links=_major_links(majors)))
    blogs = _fetch_blog_links(PRIORITY_BLOG_SLUGS[:4])
    if blogs:
        groups.append(InternalLinkGroup(title="راهنماهای تکمیلی", links=blogs))
    return groups


def _fetch_blog_links(slugs: tuple[str, ...]) -> tuple[InternalLink, ...]:
    posts = BlogPost.objects.filter(is_published=True, slug__in=slugs).only("slug", "title")
    by_slug = {p.slug: p for p in posts}
    return tuple(
        InternalLink(label=by_slug[s].title, url=_blog_url(s), kind="blog")
        for s in slugs
        if s in by_slug
    )


def get_blog_resource_groups(blog_slug: str) -> list[InternalLinkGroup]:
    """لینک از پست وبلاگ به دانشگاه/رشته مرتبط."""
    spec = BLOG_RESOURCE_SLUGS.get(blog_slug)
    if not spec:
        return []
    groups: list[InternalLinkGroup] = []
    unis = _fetch_universities(spec.get("universities", ()))
    if unis:
        groups.append(InternalLinkGroup(title="دانشگاه‌های مرتبط", links=_uni_links(unis)))
    majors = _fetch_majors(spec.get("majors", ()))
    if majors:
        groups.append(InternalLinkGroup(title="رشته‌های مرتبط", links=_major_links(majors)))
    return groups


def get_blog_resource_universities(blog_slug: str, *, limit: int = 6) -> list[University]:
    spec = BLOG_RESOURCE_SLUGS.get(blog_slug, {})
    return _fetch_universities(spec.get("universities", ())[:limit])


def get_blog_resource_majors(blog_slug: str, *, limit: int = 6) -> list[Major]:
    spec = BLOG_RESOURCE_SLUGS.get(blog_slug, {})
    return _fetch_majors(spec.get("majors", ())[:limit])
