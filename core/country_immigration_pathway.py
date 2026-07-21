"""
مسیر مهاجرت تحصیلی هر کشور — مراحل به‌هم‌پیوسته با داده واقعی و لینک به صفحات سایت.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any
from urllib.parse import urlencode

from django.urls import reverse

from .models import StudyCountry


@dataclass(frozen=True)
class PathwayLink:
    label: str
    url: str
    variant: str = ""  # primary | ghost
    jump_id: str = ""  # اسکرول نرم در همان صفحه کشور


@dataclass(frozen=True)
class PathwayStep:
    order: int
    phase: str
    title: str
    summary: str
    detail: str
    duration: str
    icon: str
    service_hint: str
    links: tuple[PathwayLink, ...] = ()
    jump_id: str = ""


@dataclass(frozen=True)
class CountryImmigrationPathway:
    country_code: str
    country_name: str
    headline: str
    intro: str
    total_duration: str
    highlight_stats: tuple[tuple[str, str], ...]
    steps: tuple[PathwayStep, ...]
    cta_label: str
    cta_url: str


def _url(name: str, **kwargs: Any) -> str:
    return reverse(name, kwargs=kwargs) if kwargs else reverse(name)


def _qurl(name: str, query: dict[str, str], **kwargs: Any) -> str:
    base = _url(name, **kwargs)
    if not query:
        return base
    return f"{base}?{urlencode(query)}"


_COUNTRY_PATHWAY_META: dict[str, dict[str, Any]] = {
    "canada": {
        "total_duration": "۱۲ تا ۱۸ ماه (از مشاوره تا ورود)",
        "highlight_stats": (
            ("ویزا", "Study Permit + PAL"),
            ("پس از تحصیل", "PGWP ۱–۳ سال"),
            ("کار حین تحصیل", "۲۰ ساعت/هفته"),
            ("تمکن", "GIC ~۲۲,۸۹۵ CAD"),
        ),
        "step_details": {
            1: "بررسی معدل، IELTS، بودجه و هدف شغلی؛ تعیین استان، DLI و زمان‌بندی Fall/Winter. "
            "برای کارشناسی در بسیاری پرونده‌ها <strong>PAL</strong> لازم است.",
            2: "انتخاب ۵–۸ دانشگاه DLI متناسب با رشته؛ مقایسه رتبه QS، شهریه و شهر (تورنتو، ونکوور، مونترال).",
            3: "IELTS Academic معمولاً ۶.۰–۷.۰؛ ترجمه رسمی ریزنمرات، انگیزه‌نامه و توصیه‌نامه (ارشد/دکتری). "
            "پذیرش مشروط زبان در بسیاری دانشگاه‌ها ممکن است.",
            4: "اپلای از OUAC، ApplyAlberta یا پورتال دانشگاه؛ دریافت Letter of Acceptance و پرداخت سپرده.",
            5: "بورسیه Entrance خودکار، Pearson/UBC Scholars؛ آماده‌سازی GIC و اثبات تمکن مالی IRCC.",
            6: "درخواست Study Permit آنلاین؛ معاینه پزشکی و عدم سوءپیشینه؛ زمان بررسی معمولاً ۴–۱۲ هفته.",
            7: "ورود، دریافت SIN، افتتاح حساب و استقرار؛ پس از فارغ‌التحصیلی مسیر PGWP و Express Entry.",
        },
    },
    "spain": {
        "total_duration": "۱۰ تا ۱۶ ماه (با توجه به Homologación)",
        "highlight_stats": (
            ("ویزا", "Tipo D — Estudiante"),
            ("اقامت", "کارت TIE پس از ورود"),
            ("کار", "۳۰ ساعت/هفته"),
            ("شهریه دولتی", "۷۵۰–۳,۵۰۰ یورو/سال"),
        ),
        "step_details": {
            1: "تعیین مقطع Grado/Máster، سطح زبان (DELE B2 یا IELTS برای برنامه انگلیسی) و بودجه شهر.",
            2: "انتخاب دانشگاه دولتی یا خصوصی؛ مادرید و بارسلونا گران‌تر؛ والنسیا و گرانادا مقرون‌به‌صرفه‌تر.",
            3: "ترجمه و Apostille مدارک؛ برای پزشکی و معماری <strong>Homologación</strong> زمان‌بر است — زود شروع کنید.",
            4: "اپلای UNEDasiss یا پورتال دانشگاه؛ آزمون PCE در صورت نیاز؛ دریافت carta de admisión.",
            5: "بورسیه دانشگاهی و MAEC-AECID؛ تمکن ~۱,۰۰۰ یورو/ماه × ۱۲؛ بیمه درمانی خصوصی برای ویزا.",
            6: "رزرو سفارت/ویزاسنتر؛ ویزای نوع D؛ زمان‌بندی ۲–۳ ماه برای وقت و بررسی.",
            7: "ثبت TIE ظرف ۳۰ روز؛ اسکان و ثبت‌نام دانشگاه؛ ۱۲ ماه جستجوی کار پس از فارغ‌التحصیلی.",
        },
    },
    "china": {
        "total_duration": "۸ تا ۱۴ ماه (با CSC زودتر شروع کنید)",
        "highlight_stats": (
            ("ویزا", "X1 + Residence Permit"),
            ("بورسیه", "CSC تمام‌هزینه"),
            ("اپلای", "studyinchina.edu.cn"),
            ("خوابگاه", "۸۰۰–۲,۰۰۰ یوان/ماه"),
        ),
        "step_details": {
            1: "بررسی لیست دانشگاه‌های مورد تأیید وزارت علوم/بهداشت؛ برنامه‌ریزی بورسیه CSC (ژانویه–مارس).",
            2: "انتخاب دانشگاه (Tsinghua، Fudan، …) و رشته؛ MBBS، مهندسی یا زبان چینی.",
            3: "IELTS ۶+ یا HSK ۴–۵؛ گواهی سلامت و عدم سوءپیشینه برای ویزا از همان ابتدا آماده شود.",
            4: "ثبت‌نام studyinchina یا سایت دانشگاه؛ دریافت Admission Notice و فرم JW201/JW202.",
            5: "اپلای همزمان CSC؛ بورسیه استانی و دانشگاهی؛ شهریه بدون بورسیه ۱۵,۰۰۰–۶۰,۰۰۰ یوان.",
            6: "ویزای X1 از CVASC ایران؛ صدور معمولاً ۱–۲ هفته پس از مدارک کامل.",
            7: "Residence Permit ظرف ۳۰ روز؛ خوابگاه و ثبت‌نام؛ کار پاره‌وقت با مجوز دانشگاه.",
        },
    },
}


@lru_cache(maxsize=1)
def _world_pathway_meta() -> dict[str, dict[str, Any]]:
    """متادیتای مسیر مهاجرت کشورهای جهانی — از کاتالوگ محتوای غنی."""
    from .seed_data.world_rich_country_builder import build_pathway_meta
    from .seed_data.world_rich_country_facts import WORLD_COUNTRY_FACTS

    out: dict[str, dict[str, Any]] = {}
    for code, facts in WORLD_COUNTRY_FACTS.items():
        meta = build_pathway_meta(facts)
        steps = meta.get("step_details") or {}
        if len(steps) >= 7:
            out[code] = meta
    return out


def _pathway_meta_for(code: str) -> dict[str, Any]:
    return _COUNTRY_PATHWAY_META.get(code) or _world_pathway_meta().get(code) or _COUNTRY_PATHWAY_META["canada"]


def _base_steps(country: StudyCountry, code: str) -> list[PathwayStep]:
    meta = _pathway_meta_for(code)
    details = meta["step_details"]
    cc = country.code
    cn = country.name
    appt_q = urlencode({"about": "universities", "title": cn})
    schol_url = _url("country_scholarships", country_code=cc)

    return [
        PathwayStep(
            order=1,
            phase="۱",
            title="ارزیابی و مشاوره",
            summary="شناخت وضعیت شما و ترسیم نقشه راه",
            detail=details[1],
            duration="۱–۲ هفته",
            icon="ti-target",
            service_hint="مشاوره تخصصی · ارزیابی پرونده",
            links=(
                PathwayLink("فرم ارزیابی مهاجرت", _url("evaluation"), "primary"),
                PathwayLink("رزرو مشاوره", f"{_url('appointment')}?{appt_q}"),
                PathwayLink("خدمات مشاوره", _url("services_category", category_slug="moshavere-arezaye")),
            ),
        ),
        PathwayStep(
            order=2,
            phase="۲",
            title="انتخاب دانشگاه و رشته",
            summary=f"مقایسه گزینه‌های تحصیل در {cn}",
            detail=details[2],
            duration="۲–۴ هفته",
            icon="ti-bookmark-alt",
            service_hint="مشاوره انتخاب مقصد",
            links=(
                PathwayLink(
                    f"دانشگاه‌های {cn}",
                    _qurl("schools_list", {"country": cc}),
                    "primary",
                ),
                PathwayLink("رشته‌های تحصیلی", _qurl("majors", {"country": cc})),
                PathwayLink(
                    "معرفی کشور",
                    f"{country.get_absolute_url()}#country-intro",
                    jump_id="country-intro",
                ),
            ),
        ),
        PathwayStep(
            order=3,
            phase="۳",
            title="آماده‌سازی زبان و مدارک",
            summary="IELTS، ترجمه رسمی و تکمیل پرونده",
            detail=details[3],
            duration="۲–۶ ماه",
            icon="ti-files",
            service_hint="ترجمه · آمادگی مصاحبه",
            links=(
                PathwayLink("دوره‌های آمادگی", _qurl("courses_list", {"country": cc})),
                PathwayLink(
                    "ترجمه و تأیید مدارک",
                    _url("services_category", category_slug="visa-madarek"),
                ),
                PathwayLink("سوالات متداول", _url("faq")),
            ),
        ),
        PathwayStep(
            order=4,
            phase="۴",
            title="اپلای و اخذ پذیرش",
            summary="ثبت درخواست تا Letter of Acceptance",
            detail=details[4],
            duration="۲–۵ ماه",
            icon="ti-medall",
            service_hint="پذیرش · SOP · پیگیری Offer",
            links=(
                PathwayLink(
                    "خدمات پذیرش و اپلای",
                    _url("services_category", category_slug="paziresh-apply"),
                    "primary",
                ),
                PathwayLink(
                    "راهنمای پذیرش",
                    f"{country.get_absolute_url()}#guide-admission",
                    jump_id="guide-admission",
                ),
                PathwayLink("تعرفه خدمات", _url("pricing")),
            ),
        ),
        PathwayStep(
            order=5,
            phase="۵",
            title="بورسیه و تمکن مالی",
            summary="فرصت‌های مالی و اثبات بودجه ویزا",
            detail=details[5],
            duration="همزمان با اپلای",
            icon="ti-crown",
            service_hint="بورسیه · برنامه‌ریزی مالی",
            links=(
                PathwayLink("راهنمای بورسیه", f"{schol_url}", "primary"),
                PathwayLink(
                    "بخش بورسیه صفحه",
                    f"{country.get_absolute_url()}#guide-scholarship",
                    jump_id="guide-scholarship",
                ),
                PathwayLink("محاسبه تعرفه", _url("pricing")),
            ),
        ),
        PathwayStep(
            order=6,
            phase="۶",
            title="ویزا و آمادگی سفر",
            summary="اقدام سفارت تا دریافت ویزا",
            detail=details[6],
            duration="۱–۳ ماه",
            icon="ti-id-badge",
            service_hint="روادید تحصیلی · پیگیری سفارت",
            links=(
                PathwayLink(
                    "خدمات ویزا",
                    _url("services_category", category_slug="visa-madarek"),
                    "primary",
                ),
                PathwayLink(
                    "ویزا و اقامت",
                    f"{country.get_absolute_url()}#guide-visa",
                    jump_id="guide-visa",
                ),
                PathwayLink(
                    "هزینه و زندگی",
                    f"{country.get_absolute_url()}#guide-living",
                    jump_id="guide-living",
                ),
            ),
        ),
        PathwayStep(
            order=7,
            phase="۷",
            title="ورود و استقرار",
            summary="شروع تحصیل و پشتیبانی پس از ورود",
            detail=details[7],
            duration="اولین ماه مقصد",
            icon="ti-world",
            service_hint="استقرار · اسکان · پشتیبانی",
            links=(
                PathwayLink(
                    "خدمات استقرار",
                    _url("services_category", category_slug="estghrar-pasokhbane"),
                    "primary",
                ),
                PathwayLink("دستاوردهای دانشجویان", _url("monthly_achievements")),
                PathwayLink("تماس با ما", _url("contact")),
            ),
        ),
    ]


def build_country_immigration_pathway(country: StudyCountry) -> CountryImmigrationPathway:
    code = (country.code or "").strip().lower()
    meta = _pathway_meta_for(code)
    steps = tuple(_base_steps(country, code))
    intro_bits = (country.intro or "").strip()
    if len(intro_bits) > 200:
        intro_bits = intro_bits[:197].rstrip() + "…"

    return CountryImmigrationPathway(
        country_code=code,
        country_name=country.name,
        headline=f"مسیر مهاجرت تحصیلی به {country.name} — گام‌به‌گام با سفیران",
        intro=(
            f"از اولین مشاوره تا روز اول کلاس در {country.name}، این نقشه راه هفت مرحله‌ای "
            f"بر اساس مقررات واقعی، خدمات قراردادی موسسه و تجربه اعزام دانشجو طراحی شده است. "
            f"{intro_bits}"
        ),
        total_duration=meta["total_duration"],
        highlight_stats=meta["highlight_stats"],
        steps=steps,
        cta_label=f"شروع مسیر {country.name} با مشاوره",
        cta_url=f"{reverse('appointment')}?{urlencode({'about': 'universities', 'title': country.name})}",
    )


def pathway_search_blob(country: StudyCountry) -> str:
    """متن برای ایندکس جستجوی صفحه کشور."""
    pw = build_country_immigration_pathway(country)
    parts = [pw.headline, pw.intro, pw.total_duration]
    for step in pw.steps:
        parts.extend([step.title, step.summary, step.detail, step.service_hint])
    return " ".join(parts)
