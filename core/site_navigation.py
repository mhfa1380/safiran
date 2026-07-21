"""
تعریف متمرکز لینک‌ها و منوهای سایت — نوبار، فوتر و جستجو از همین‌جا تغذیه می‌شوند.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from django.core.cache import cache
from django.urls import NoReverseMatch, reverse

from .cache_utils import NAV_COUNTRIES_CACHE_KEY, has_active_courses_exists_cached
from .models import Course, CourseInstructor, StudyCountry
from .nav_degrees import DEGREE_NAV_LEVELS, build_nav_degree_url

_CACHE_TIMEOUT = 300


@dataclass(frozen=True)
class NavLinkDef:
    """تعریف یک لینک — قبل از resolve شدن URL."""

    key: str
    label: str
    url_name: str
    url_kwargs: dict[str, Any] = field(default_factory=dict)
    requires_courses: bool = False
    search_keywords: str = ""
    search_subtitle: str = ""


@dataclass(frozen=True)
class NavLink:
    """لینک آماده برای قالب."""

    key: str
    label: str
    url: str
    css_class: str = ""
    flag_static: str = ""


@dataclass(frozen=True)
class NavPanelSection:
    """بخش داخل پنل dropdown (عنوان + لینک‌ها)."""

    title: str
    items: tuple[NavLink, ...] = ()
    css_class: str = ""


@dataclass(frozen=True)
class NavMenuGroup:
    """آیتم منوی هدر با زیرمنو."""

    id: str
    label: str
    url: str
    panel_title: str
    items: tuple[NavLink, ...] = ()
    sections: tuple[NavPanelSection, ...] = ()
    panel_wide: bool = False
    panel_class: str = ""


@dataclass(frozen=True)
class NavFooterColumn:
    """ستون لینک فوتر."""

    title: str
    links: tuple[NavLink, ...]


# ——— تعریف لینک‌ها (تک منبع حقیقت) ———
NAV_LINKS: dict[str, NavLinkDef] = {
    "index": NavLinkDef("index", "صفحه اصلی", "index", search_subtitle="موسسه سفیران", search_keywords="خانه home"),
    "about": NavLinkDef("about", "درباره ما", "about", search_subtitle="معرفی موسسه", search_keywords="درباره about"),
    "monthly_achievements": NavLinkDef(
        "monthly_achievements",
        "دستاوردهای ما",
        "monthly_achievements",
        search_subtitle="داستان‌های موفقیت",
        search_keywords="دستاورد achievement",
    ),
    "contact": NavLinkDef("contact", "تماس با ما", "contact", search_subtitle="آدرس و تلفن", search_keywords="تماس contact"),
    "blog": NavLinkDef("blog", "وبلاگ", "blog", search_subtitle="مقالات و اخبار", search_keywords="blog مقاله"),
    "schools_list": NavLinkDef(
        "schools_list",
        "دانشگاه‌ها",
        "schools_list",
        search_subtitle="لیست دانشگاه‌های خارج",
        search_keywords="دانشگاه university",
    ),
    "schools_list_all": NavLinkDef(
        "schools_list_all",
        "همه دانشگاه‌ها",
        "schools_list",
        search_subtitle="لیست کامل",
    ),
    "universities": NavLinkDef(
        "universities",
        "راهنمای کشورها",
        "universities",
        search_subtitle="کشورهای مقصد",
        search_keywords="کشور country",
    ),
    "degree_bachelor": NavLinkDef(
        "degree_bachelor",
        "کارشناسی",
        "evaluation",
        search_subtitle="بورسیه و پذیرش کارشناسی",
        search_keywords="کارشناسی bachelor لیسانس بورسیه",
    ),
    "degree_master": NavLinkDef(
        "degree_master",
        "کارشناسی ارشد",
        "evaluation",
        search_subtitle="بورسیه ارشد",
        search_keywords="ارشد master بورسیه",
    ),
    "degree_phd": NavLinkDef(
        "degree_phd",
        "دکتری",
        "evaluation",
        search_subtitle="بورسیه دکتری",
        search_keywords="دکتری phd بورسیه فاند",
    ),
    "majors": NavLinkDef("majors", "رشته‌های تحصیلی", "majors", search_subtitle="لیست رشته‌ها", search_keywords="رشته major"),
    "courses_list": NavLinkDef(
        "courses_list",
        "همه دوره‌های آموزشی",
        "courses_list",
        requires_courses=True,
        search_subtitle="لیست دوره‌ها و کلاس‌های زبان",
        search_keywords="دوره course کلاس زبان انگلیسی آیلتس",
    ),
    "services": NavLinkDef("services", "خدمات با ما", "services", search_subtitle="خدمات موسسه", search_keywords="خدمات services"),
    "pricing": NavLinkDef("pricing", "تعرفه خدمات", "pricing", search_subtitle="هزینه‌ها", search_keywords="تعرفه pricing"),
    "faq": NavLinkDef("faq", "سوالات متداول", "faq", search_subtitle="پاسخ سوالات", search_keywords="faq سوال"),
    "evaluation": NavLinkDef(
        "evaluation",
        "ارزیابی هوشمند",
        "evaluation",
        search_subtitle="ارزیابی رایگان آنلاین مهاجرت تحصیلی",
        search_keywords=(
            "ارزیابی evaluation هوشمند رایگان آنلاین "
            "تحلیل پرونده مهاجرت تحصیلی فرم ارزیابی"
        ),
    ),
    "appointment": NavLinkDef(
        "appointment",
        "رزرو مشاوره",
        "appointment",
        search_subtitle="وقت مشاوره",
        search_keywords="مشاوره appointment رزرو",
    ),
}

# ——— ساختار منوی هدر ———
HEADER_MENU_SPEC: tuple[dict[str, Any], ...] = (
    {
        "id": "institute",
        "label": "موسسه",
        "link": "about",
        "panel_title": "درباره سفیران",
        "items": ("about", "monthly_achievements", "contact", "blog"),
    },
    {
        "id": "destinations",
        "label": "مقصد تحصیلی",
        "link": "universities",
        "panel_title": "کشور مقصد تحصیلی",
        "panel_wide": False,
        "panel_class": "site-header__panel--destinations",
        "dynamic": "destinations",
    },
    {
        "id": "degrees",
        "label": "مقاطع تحصیلی",
        "link": "degree_bachelor",
        "panel_title": "کارشناسی، ارشد و دکتری",
        "panel_wide": True,
        "panel_class": "site-header__panel--degrees",
        "dynamic": "degrees",
    },
    {
        "id": "study",
        "label": "رشته و دوره",
        "link": "courses_list",
        "panel_title": "دوره‌ها و رشته‌های تحصیلی",
        "items": ("courses_list", "majors"),
        "append_active_courses": True,
        "append_instructors": True,
    },
    {
        "id": "services",
        "label": "خدمات",
        "link": "services",
        "panel_title": "خدمات و پشتیبانی",
        "items": ("services", "pricing", "faq", "courses_list"),
    },
)

HEADER_STANDALONE_KEYS: tuple[str, ...] = ()
HEADER_CTA_KEY: str | None = None
HEADER_CTA_LABEL = "نیاز به مشاوره دارید؟"
HEADER_EVAL_KEY = "evaluation"
QUICK_LINK_KEYS: tuple[str, ...] = ("services", "faq", "appointment")

# لینک‌های «مسیرهای مرتبط» صفحه ارزیابی — کلیدهای NAV_LINKS (+ وبلاگ راهنما)
EVALUATION_RELATED_NAV_KEYS: tuple[str, ...] = (
    "appointment",
    "pricing",
    "faq",
    "schools_list",
    "majors",
    "services",
)

# ——— ستون‌های فوتر (بالا — لینک‌های اصلی؛ بدون تکرار دوره/مدرس/درباره) ———
FOOTER_COLUMNS_SPEC: tuple[dict[str, Any], ...] = (
    {
        "title": "تحصیل در خارج",
        "links": ("universities", "schools_list", "majors"),
    },
    {
        "title": "دوره و زبان",
        "links": ("courses_list",),
    },
    {
        "title": "خدمات",
        "links": ("services", "pricing", "appointment", "evaluation", "faq"),
    },
)

FOOTER_BOTTOM_ABOUT_KEYS: tuple[str, ...] = (
    "about",
    "monthly_achievements",
    "blog",
)

FOOTER_ABOUT_TEXT = (
    "{name} با تیمی متخصص و مجرب، در کنار شماست تا مسیر مهاجرت را ساده‌تر، "
    "مطمئن‌تر و حرفه‌ای‌تر طی کنید. ما با مجوز رسمی از وزارت علوم، همراه شما "
    "برای ساخت آینده‌ای روشن و پایدار هستیم."
)


def has_active_courses_cached() -> bool:
    return has_active_courses_exists_cached()


def _active_course_detail_links() -> tuple[NavLink, ...]:
    """لینک مستقیم به صفحه هر دوره فعال."""
    if not has_active_courses_cached():
        return ()
    links: list[NavLink] = []
    for course in Course.objects.filter(is_active=True).only("title", "slug").order_by("order", "id"):
        try:
            url = course.get_course_url()
        except NoReverseMatch:
            continue
        links.append(
            NavLink(
                key=f"course_{course.slug}",
                label=course.title,
                url=url,
            )
        )
    return tuple(links)


def _active_instructor_links() -> tuple[NavLink, ...]:
    """لینک صفحه مدرسان دوره‌های فعال."""
    if not has_active_courses_cached():
        return ()
    links: list[NavLink] = []
    for instructor in (
        CourseInstructor.objects.filter(is_active=True, courses__is_active=True)
        .distinct()
        .only("name", "slug", "position")
        .order_by("order", "id")
    ):
        try:
            url = reverse("course_instructor_detail", kwargs={"slug": instructor.slug})
        except NoReverseMatch:
            continue
        label = instructor.name
        if instructor.position:
            label = f"{instructor.name} — {instructor.position}"
        links.append(
            NavLink(
                key=f"instructor_{instructor.slug}",
                label=label,
                url=url,
            )
        )
    return tuple(links)


def _append_course_nav_items(items: list[NavLink], spec: dict[str, Any]) -> None:
    if spec.get("append_active_courses"):
        items.extend(_active_course_detail_links())
    if spec.get("append_instructors"):
        items.extend(_active_instructor_links())


def get_nav_countries_cached() -> list[StudyCountry]:
    countries = cache.get(NAV_COUNTRIES_CACHE_KEY)
    if countries is None:
        countries = list(
            StudyCountry.objects.filter(is_active=True)
            .order_by("order", "id")
            .only("code", "name", "headline")
        )
        cache.set(NAV_COUNTRIES_CACHE_KEY, countries, _CACHE_TIMEOUT)
    return countries


def _resolve_link(defn: NavLinkDef, *, css_class: str = "") -> NavLink | None:
    if defn.requires_courses and not has_active_courses_cached():
        return None
    try:
        if defn.url_kwargs:
            url = reverse(defn.url_name, kwargs=defn.url_kwargs)
        else:
            url = reverse(defn.url_name)
    except NoReverseMatch:
        return None
    return NavLink(key=defn.key, label=defn.label, url=url, css_class=css_class)


def _links_from_keys(keys: tuple[str, ...], *, css_classes: dict[str, str] | None = None) -> tuple[NavLink, ...]:
    css_classes = css_classes or {}
    out: list[NavLink] = []
    for key in keys:
        defn = NAV_LINKS.get(key)
        if not defn:
            continue
        link = _resolve_link(defn, css_class=css_classes.get(key, ""))
        if link:
            out.append(link)
    return tuple(out)


def _country_links(*, scholarship: bool = False, target_degree: str = "") -> tuple[NavLink, ...]:
    countries = get_nav_countries_cached()
    if not countries:
        fallback = _resolve_link(NAV_LINKS["universities"])
        return (fallback,) if fallback else ()
    links: list[NavLink] = []
    for c in countries:
        url = reverse("country_detail", kwargs={"country_code": c.code})
        if scholarship and target_degree:
            url = build_nav_degree_url(
                "country_scholarships",
                target_degree=target_degree,
                intent="scholarship",
                url_kwargs={"country_code": c.code},
            )
        links.append(
            NavLink(
                key=f"country_{c.code}",
                label=f"تحصیل در {c.name}",
                url=url,
            )
        )
    return tuple(links)


def _universities_by_country_links() -> tuple[NavLink, ...]:
    all_uni = _resolve_link(NAV_LINKS["schools_list"])
    if not all_uni:
        return ()
    items: list[NavLink] = [
        NavLink(
            key="schools_list",
            label="همه دانشگاه‌ها",
            url=all_uni.url,
            css_class="site-header__panel-cta",
        )
    ]
    for c in get_nav_countries_cached():
        items.append(
            NavLink(
                key=f"schools_{c.code}",
                label=f"دانشگاه‌های {c.name}",
                url=build_nav_degree_url("schools_list", country=c.code),
            )
        )
    return tuple(items)


def _country_pathway_links() -> tuple[NavLink, ...]:
    countries = get_nav_countries_cached()
    if not countries:
        return ()
    links: list[NavLink] = []
    for c in countries:
        url = reverse("country_detail", kwargs={"country_code": c.code}) + "#country-pathway"
        links.append(
            NavLink(
                key=f"pathway_{c.code}",
                label=f"مسیر مهاجرت {c.name}",
                url=url,
            )
        )
    return tuple(links)


def _destinations_quick_links() -> tuple[NavLink, ...]:
    """لینک‌های عمومی — بدون ارزیابی (ارزیابی داخل بخش اعزام ماست)."""
    specs: tuple[tuple[str, str], ...] = (
        ("universities", "site-header__dest-quick"),
        ("schools_list", "site-header__dest-quick"),
    )
    links: list[NavLink] = []
    for key, css in specs:
        defn = NAV_LINKS.get(key)
        if not defn:
            continue
        resolved = _resolve_link(defn, css_class=css)
        if resolved:
            links.append(resolved)
    return tuple(links)


def _country_nav_link(country: StudyCountry) -> NavLink:
    from .study_destinations import country_flag_static, is_primary_study_country

    primary = is_primary_study_country(country.code)
    return NavLink(
        key=f"country_{country.code}",
        label=country.name,
        url=reverse("country_detail", kwargs={"country_code": country.code}),
        css_class=(
            "site-header__dest-chip site-header__dest-chip--primary"
            if primary
            else "site-header__dest-chip"
        ),
        flag_static=country_flag_static(country.code),
    )


def _split_country_nav_links() -> tuple[tuple[NavLink, ...], tuple[NavLink, ...]]:
    """کشورهای اعزام ما (اصلی) جدا از سایر مقاصد."""
    from .study_destinations import is_primary_study_country

    countries = get_nav_countries_cached()
    if not countries:
        fallback = _resolve_link(NAV_LINKS["universities"])
        fb = ((fallback,), ()) if fallback else ((), ())
        return fb

    primary: list[NavLink] = []
    other: list[NavLink] = []
    for c in countries:
        link = _country_nav_link(c)
        if is_primary_study_country(c.code):
            primary.append(link)
        else:
            other.append(link)
    return tuple(primary), tuple(other)


def _destinations_sections() -> tuple[NavPanelSection, ...]:
    quick = _destinations_quick_links()
    primary_countries, other_countries = _split_country_nav_links()
    sections: list[NavPanelSection] = []

    if quick:
        sections.append(
            NavPanelSection(
                title="",
                items=quick,
                css_class="site-header__dest-quick-section",
            )
        )

    if primary_countries:
        primary_items: list[NavLink] = list(primary_countries)
        eval_link = _resolve_link(
            NAV_LINKS["evaluation"],
            css_class="site-header__dest-eval-btn site-header__dest-quick--accent",
        )
        if eval_link:
            primary_items.append(eval_link)
        sections.append(
            NavPanelSection(
                title="مقاصد اعزام ما",
                items=tuple(primary_items),
                css_class="site-header__dest-primary-section",
            )
        )

    if other_countries:
        sections.append(
            NavPanelSection(
                title="سایر کشورهای مقصد",
                items=other_countries,
                css_class="site-header__dest-other-section",
            )
        )

    return tuple(sections)


def _degree_sections() -> tuple[NavPanelSection, ...]:
    countries = get_nav_countries_cached()
    sections: list[NavPanelSection] = []
    for level in DEGREE_NAV_LEVELS:
        items: list[NavLink] = [
            NavLink(
                key=f"eval_scholarship_{level.key}",
                label=f"ارزیابی و بورسیه {level.label}",
                url=build_nav_degree_url(
                    "evaluation", target_degree=level.key, intent="scholarship"
                ),
                css_class="site-header__panel-featured",
            ),
            NavLink(
                key=f"schools_{level.key}",
                label="دانشگاه‌ها",
                url=build_nav_degree_url(
                    "schools_list", target_degree=level.key, intent="scholarship"
                ),
            ),
            NavLink(
                key=f"majors_{level.key}",
                label="رشته‌های تحصیلی",
                url=build_nav_degree_url(
                    "majors", target_degree=level.key, intent="scholarship"
                ),
            ),
        ]
        for c in countries[:5]:
            items.append(
                NavLink(
                    key=f"country_{level.key}_{c.code}",
                    label=f"بورسیه {c.name}",
                    url=build_nav_degree_url(
                        "country_scholarships",
                        target_degree=level.key,
                        intent="scholarship",
                        url_kwargs={"country_code": c.code},
                    ),
                )
            )
        sections.append(
            NavPanelSection(
                title=level.label,
                items=tuple(items),
                css_class=f"site-header__panel-degree site-header__panel-degree--{level.key}",
            )
        )
    return tuple(sections)


def build_header_menu() -> tuple[NavMenuGroup, ...]:
    groups: list[NavMenuGroup] = []
    for spec in HEADER_MENU_SPEC:
        root = NAV_LINKS.get(spec["link"])
        if not root:
            continue
        root_resolved = _resolve_link(root)
        if not root_resolved:
            continue
        if spec["id"] == "degrees":
            root_resolved = NavLink(
                key="degrees",
                label=root_resolved.label,
                url=build_nav_degree_url(
                    "evaluation",
                    target_degree=DEGREE_NAV_LEVELS[0].key,
                    intent="scholarship",
                ),
            )

        items: list[NavLink] = list(_links_from_keys(tuple(spec.get("items") or ())))
        sections: tuple[NavPanelSection, ...] = ()

        dynamic = spec.get("dynamic")
        if dynamic == "destinations":
            sections = _destinations_sections()
            items = []
        elif dynamic == "degrees":
            sections = _degree_sections()
            items = []
        elif dynamic == "countries":
            sections = (NavPanelSection(title="", items=_country_links()),)
            items = []

        footer_key = spec.get("footer_item")
        if footer_key and footer_key in NAV_LINKS and sections:
            cta = _resolve_link(NAV_LINKS[footer_key], css_class="site-header__panel-cta")
            if cta:
                sec_list = list(sections)
                last = sec_list[-1]
                sec_list[-1] = NavPanelSection(
                    title=last.title,
                    items=last.items + (cta,),
                    css_class=last.css_class,
                )
                sections = tuple(sec_list)
        elif footer_key and footer_key in NAV_LINKS and items:
            cta = _resolve_link(NAV_LINKS[footer_key], css_class="site-header__panel-cta")
            if cta:
                items.append(cta)

        _append_course_nav_items(items, spec)

        groups.append(
            NavMenuGroup(
                id=spec["id"],
                label=spec["label"],
                url=root_resolved.url,
                panel_title=spec.get("panel_title", ""),
                items=tuple(items),
                sections=sections,
                panel_wide=bool(spec.get("panel_wide")),
                panel_class=spec.get("panel_class", ""),
            )
        )
    return tuple(groups)


def _degree_footer_links() -> tuple[NavLink, ...]:
    return tuple(
        NavLink(
            key=f"footer_degree_{level.key}",
            label=f"بورسیه {level.label}",
            url=build_nav_degree_url(
                "evaluation", target_degree=level.key, intent="scholarship"
            ),
        )
        for level in DEGREE_NAV_LEVELS
    )


def build_footer_columns() -> tuple[NavFooterColumn, ...]:
    columns: list[NavFooterColumn] = []
    for spec in FOOTER_COLUMNS_SPEC:
        links = _links_from_keys(tuple(spec["links"]))
        if links:
            columns.append(NavFooterColumn(title=spec["title"], links=links))
    return tuple(columns)


def build_footer_bottom_about() -> tuple[NavLink, ...]:
    """لینک‌های درباره ما در نوار پایین فوتر."""
    return _links_from_keys(FOOTER_BOTTOM_ABOUT_KEYS)


def build_header_standalone() -> tuple[NavLink, ...]:
    return _links_from_keys(HEADER_STANDALONE_KEYS)


def build_header_cta() -> NavLink | None:
    if not HEADER_CTA_KEY:
        return None
    defn = NAV_LINKS.get(HEADER_CTA_KEY)
    link = _resolve_link(defn) if defn else None
    if not link:
        return None
    return NavLink(key=link.key, label=HEADER_CTA_LABEL, url=link.url, css_class=link.css_class)


def build_header_eval() -> NavLink | None:
    defn = NAV_LINKS.get(HEADER_EVAL_KEY)
    return _resolve_link(defn) if defn else None


def get_searchable_page_defs() -> tuple[NavLinkDef, ...]:
    """صفحات ثابت قابل جستجو — از همان تعریف لینک‌ها."""
    order = (
        "index",
        "about",
        "contact",
        "appointment",
        "evaluation",
        "pricing",
        "services",
        "faq",
        "blog",
        "majors",
        "schools_list",
        "monthly_achievements",
        "courses_list",
        "universities",
        "degree_bachelor",
        "degree_master",
        "degree_phd",
    )
    out: list[NavLinkDef] = []
    for key in order:
        defn = NAV_LINKS.get(key)
        if not defn:
            continue
        if defn.requires_courses and not has_active_courses_cached():
            continue
        out.append(defn)
    return tuple(out)


def build_quick_links() -> tuple[NavLink, ...]:
    """لینک‌های میانبر برای صفحات خالی / CTA."""
    return _links_from_keys(QUICK_LINK_KEYS)


def _evaluation_related_label(defn: NavLinkDef) -> str:
    """برچسب نمایشی از تعریف ناوبری (عنوان + زیرعنوان جستجو)."""
    subtitle = (defn.search_subtitle or "").strip()
    if subtitle and subtitle not in defn.label:
        return f"{defn.label} — {subtitle}"
    return defn.label


def _evaluation_blog_guide_link(*, base: str) -> dict[str, str] | None:
    """لینک پست راهنمای ارزیابی — عنوان و slug از دیتابیس."""
    from .seed_data.blog_post_evaluation import EVALUATION_BLOG_SLUG

    slug = EVALUATION_BLOG_SLUG
    label = "راهنمای ارزیابی رایگان (وبلاگ)"
    try:
        from .models import BlogPost

        post = (
            BlogPost.objects.filter(slug=EVALUATION_BLOG_SLUG, is_published=True)
            .only("title", "slug")
            .first()
        )
        if post:
            slug = post.slug
            title = (post.title or "").strip()
            if title:
                label = title if len(title) <= 80 else f"{title[:77]}…"
    except Exception:
        pass

    try:
        path = reverse("blog_detail", kwargs={"slug": slug})
    except NoReverseMatch:
        return None

    return {
        "key": "blog_evaluation_guide",
        "label": label,
        "url": f"{base}{path}",
    }


def build_evaluation_related_links(*, site_url: str = "") -> tuple[dict[str, str], ...]:
    """
    مسیرهای مرتبط صفحه ارزیابی — URL با reverse و برچسب از NAV_LINKS.
    آدرس مطلق اگر site_url داده شود.
    """
    base = site_url.rstrip("/") if site_url else ""
    out: list[dict[str, str]] = []

    blog = _evaluation_blog_guide_link(base=base)
    if blog:
        out.append(blog)

    for key in EVALUATION_RELATED_NAV_KEYS:
        defn = NAV_LINKS.get(key)
        if not defn:
            continue
        link = _resolve_link(defn)
        if not link:
            continue
        url = link.url
        if base and url.startswith("/"):
            url = f"{base}{url}"
        out.append(
            {
                "key": key,
                "label": _evaluation_related_label(defn),
                "url": url,
            }
        )

    return tuple(out)


def build_site_navigation(institute_name: str = "") -> dict[str, Any]:
    """ساختار کامل ناوبری برای context قالب."""
    cta = build_header_cta()
    return {
        "header_menu": build_header_menu(),
        "header_standalone": build_header_standalone(),
        "header_cta": cta,
        "header_eval": build_header_eval(),
        "footer_columns": build_footer_columns(),
        "footer_bottom_about": build_footer_bottom_about(),
        "footer_about": FOOTER_ABOUT_TEXT.format(name=institute_name or "موسسه"),
        "countries": get_nav_countries_cached(),
        "quick_links": build_quick_links(),
    }
