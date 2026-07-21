"""
کاتالوگ بورسیه و فاند — پیشنهاد بر اساس کشور، مقطع و پروفایل ارزیابی.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from django.urls import reverse
from .faq_seo import _plain_answer

from .models import EvaluationRequest

_DEGREE_BACHELOR = EvaluationRequest.DEGREE_BACHELOR
_DEGREE_MASTER = EvaluationRequest.DEGREE_MASTER
_DEGREE_PHD = EvaluationRequest.DEGREE_PHD
_ANY = "any"


@dataclass(frozen=True)
class ScholarshipProgram:
    id: str
    country: str
    name: str
    provider: str
    coverage: str
    degree_levels: frozenset[str]
    min_gpa: float | None = None
    lang_note: str = ""
    highlights: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    priority: int = 50


SCHOLARSHIP_PROGRAMS: tuple[ScholarshipProgram, ...] = (
    # ─── کانادا ───
    ScholarshipProgram(
        "ca-pearson",
        "canada",
        "بورسیه Lester B. Pearson (دانشگاه تورنتو)",
        "University of Toronto",
        "شهریه، هزینه زندگی و کتاب تا سقف برنامه",
        frozenset({_DEGREE_BACHELOR}),
        min_gpa=17.5,
        lang_note="IELTS 7+ یا معادل",
        highlights=(
            "یکی از کامل‌ترین بورسیه‌های کارشناسی کانادا",
            "مناسب دانشجویان بین‌المللی با رزومه قوی",
        ),
        tags=("کارشناسی", "تمام‌وقت", "رقابتی"),
        priority=95,
    ),
    ScholarshipProgram(
        "ca-entrance",
        "canada",
        "بورسیه‌های ورودی دانشگاه‌ها (Entrance Scholarships)",
        "دانشگاه‌های کانادا",
        "معمولاً ۲٬۰۰۰ تا ۲۰٬۰۰۰ دلار کانادا در سال اول",
        frozenset({_DEGREE_BACHELOR, _DEGREE_MASTER}),
        min_gpa=15.0,
        lang_note="IELTS 6.0+ بسته به دانشگاه",
        highlights=(
            "بسیاری از دانشگاه‌ها به‌صورت خودکار بر اساس معدل ارزیابی می‌کنند",
            "برخی نیاز به درخواست جداگانه دارند",
        ),
        tags=("کارشناسی", "ارشد", "مبتنی بر معدل"),
        priority=88,
    ),
    ScholarshipProgram(
        "ca-vanier",
        "canada",
        "بورسیه Vanier Canada Graduate",
        "دولت کانادا",
        "۵۰٬۰۰۰ دلار کانادا در سال (۳ سال)",
        frozenset({_DEGREE_PHD}),
        min_gpa=17.0,
        lang_note="رزومه پژوهشی قوی",
        highlights=(
            "برای دکتری با پتانسیل تحقیقاتی بالا",
            "نیاز به معرفی استاد و طرح تحقیقاتی",
        ),
        tags=("دکتری", "پژوهشی", "دولتی"),
        priority=92,
    ),
    ScholarshipProgram(
        "ca-ontario-trillium",
        "canada",
        "Ontario Trillium Scholarship (OTS)",
        "استان انتاریو",
        "۴۰٬۰۰۰ دلار کانادا در سال",
        frozenset({_DEGREE_MASTER, _DEGREE_PHD}),
        min_gpa=16.5,
        highlights=("برای ارشد و دکتری در دانشگاه‌های انتاریو",),
        tags=("ارشد", "دکتری", "استانی"),
        priority=85,
    ),
    # ─── چین ───
    ScholarshipProgram(
        "cn-csc",
        "china",
        "بورسیه دولتی چین (CSC)",
        "دولت چین",
        "شهریه، خوابگاه و مقرری ماهانه",
        frozenset({_DEGREE_BACHELOR, _DEGREE_MASTER, _DEGREE_PHD}),
        min_gpa=14.0,
        lang_note="برنامه انگلیسی‌زبان یا HSK بسته به رشته",
        highlights=(
            "محبوب‌ترین بورسیه بین‌المللی چین",
            "قابل ترکیب با پذیرش بسیاری از دانشگاه‌های معتبر",
        ),
        tags=("دولتی", "کامل", "بین‌المللی"),
        priority=98,
    ),
    ScholarshipProgram(
        "cn-provincial",
        "china",
        "بورسیه‌های استانی چین",
        "دولت استانی",
        "بخشی از شهریه و مقرری",
        frozenset({_DEGREE_BACHELOR, _DEGREE_MASTER}),
        min_gpa=13.5,
        highlights=("گزینه تکمیلی برای CSC یا مسیر مستقل برخی استان‌ها",),
        tags=("استانی", "تکمیلی"),
        priority=80,
    ),
    ScholarshipProgram(
        "cn-university-president",
        "china",
        "بورسیه رئیس دانشگاه (University President Scholarship)",
        "دانشگاه‌های چین",
        "۵۰ تا ۱۰۰٪ شهریه",
        frozenset({_DEGREE_BACHELOR, _DEGREE_MASTER}),
        min_gpa=15.0,
        highlights=("رقابت در سطح هر دانشگاه؛ زمان‌بندی جدا از CSC",),
        tags=("دانشگاهی", "شهریه"),
        priority=78,
    ),
    # ─── اسپانیا ───
    ScholarshipProgram(
        "es-maec",
        "spain",
        "بورسیه MAEC-AECID",
        "وزارت امور خارجه اسپانیا",
        "شهریه، بیمه و مقرری ماهانه",
        frozenset({_DEGREE_MASTER, _DEGREE_PHD}),
        min_gpa=15.5,
        lang_note="اسپانیایی یا انگلیسی بسته به برنامه",
        highlights=("برای تحصیلات تکمیلی در دانشگاه‌های اسپانیا",),
        tags=("ارشد", "دکتری", "دولتی"),
        priority=90,
    ),
    ScholarshipProgram(
        "es-merit",
        "spain",
        "بورسیه مبتنی بر شایستگی دانشگاهی",
        "دانشگاه‌های اسپانیا",
        "تا ۵۰٪ شهریه یا کمک‌هزینه",
        frozenset({_DEGREE_BACHELOR, _DEGREE_MASTER}),
        min_gpa=14.5,
        highlights=("هر دانشگاه لیست و شرایط جداگانه دارد",),
        tags=("کارشناسی", "ارشد", "شایستگی"),
        priority=82,
    ),
    # ─── آلمان ───
    ScholarshipProgram(
        "de-daad",
        "germany",
        "بورسیه DAAD",
        "DAAD آلمان",
        "مقرری ماهانه و بیمه",
        frozenset({_DEGREE_MASTER, _DEGREE_PHD}),
        min_gpa=15.0,
        lang_note="آلمانی یا انگلیسی بسته به برنامه",
        highlights=("یکی از معتبرترین برنامه‌های اروپا برای تحصیلات تکمیلی",),
        tags=("ارشد", "دکتری", "DAAD"),
        priority=91,
    ),
    ScholarshipProgram(
        "de-deutschlandstipendium",
        "germany",
        "Deutschlandstipendium",
        "دولت و بخش خصوصی",
        "۳۰۰ یورو در ماه",
        frozenset({_DEGREE_BACHELOR, _DEGREE_MASTER}),
        min_gpa=14.0,
        highlights=("نیاز به عملکرد تحصیلی و فعالیت اجتماعی",),
        tags=("کارشناسی", "ارشد"),
        priority=75,
    ),
    # ─── ایتالیا ───
    ScholarshipProgram(
        "it-invest-talent",
        "italy",
        "Invest Your Talent in Italy",
        "دولت ایتالیا",
        "شهریه و مقرری",
        frozenset({_DEGREE_MASTER}),
        min_gpa=15.0,
        lang_note="انگلیسی",
        highlights=("برای رشته‌های STEM و طراحی در مقطع ارشد",),
        tags=("ارشد", "STEM"),
        priority=86,
    ),
    ScholarshipProgram(
        "it-dsu",
        "italy",
        "بورسیه منطقه‌ای DSU",
        "مناطق ایتالیا",
        "شهریه، خوابگاه و وعده غذا",
        frozenset({_DEGREE_BACHELOR, _DEGREE_MASTER}),
        min_gpa=13.0,
        highlights=("بر اساس درآمد خانوار؛ مناسب بودجه محدود",),
        tags=("کارشناسی", "ارشد", "نیازمندی مالی"),
        priority=84,
    ),
)


def _strip_html(text: str, limit: int = 280) -> str:
    return _plain_answer(text or "", max_len=limit)


def _scholarship_page_url(country_code: str, target_degree: str = "") -> str:
    from .country_scholarship_seo import get_country_scholarship_guide

    guide = get_country_scholarship_guide(country_code, target_degree)
    if guide:
        return guide.get_absolute_url()
    base = reverse("country_detail", kwargs={"country_code": country_code})
    return f"{base}#guide-scholarship"


def _country_flag_url(code: str) -> str:
    from django.templatetags.static import static

    flags = {"canada": "ca", "spain": "es", "china": "cn", "germany": "de", "italy": "it"}
    iso = flags.get(code, code[:2] if code else "xx")
    return static(f"img/flags/{iso}.svg")


def _resolve_target_degree(scholarship_target: str, profile_degree_level: int) -> str:
    if scholarship_target in (_DEGREE_BACHELOR, _DEGREE_MASTER, _DEGREE_PHD):
        return scholarship_target
    if profile_degree_level >= 4:
        return _DEGREE_PHD
    if profile_degree_level >= 3:
        return _DEGREE_MASTER
    return _DEGREE_BACHELOR


def _program_matches_degree(program: ScholarshipProgram, target_degree: str) -> bool:
    if _ANY in program.degree_levels:
        return True
    return target_degree in program.degree_levels


def _score_program(
    program: ScholarshipProgram,
    *,
    gpa: float | None,
    lang_ielts: float | None,
    research_score: int,
    target_degree: str,
    country_rank: int,
) -> float:
    if not _program_matches_degree(program, target_degree):
        return 0.0
    score = float(program.priority)
    if country_rank == 0:
        score += 12
    elif country_rank == 1:
        score += 6
    if gpa is not None and program.min_gpa is not None:
        if gpa >= program.min_gpa + 1:
            score += 8
        elif gpa >= program.min_gpa:
            score += 4
        else:
            score -= 6
    if lang_ielts is not None:
        if lang_ielts >= 6.5:
            score += 4
        elif lang_ielts >= 6.0:
            score += 2
    if program.degree_levels == frozenset({_DEGREE_PHD}) and research_score >= 2:
        score += 6
    elif program.degree_levels == frozenset({_DEGREE_PHD}):
        score -= 4
    return score


_UNI_NAME_STOP = frozenset(
    {
        "university",
        "of",
        "the",
        "and",
        "دانشگاه",
        "در",
        "و",
        "college",
        "institute",
        "international",
        "student",
        "entrance",
        "scholarship",
        "scholarships",
        "بورسیه",
        "ورودی",
        "بین",
        "المللی",
    }
)

# بورسیه‌های عمومی — بدون تطابق «مرتبط با دانشگاه پیشنهادی»
_GENERIC_PROGRAM_KEYS = frozenset(
    {
        "ca-entrance",
        "cn-provincial",
        "cn-university-president",
        "es-merit",
        "es-regional",
    }
)

_GENERIC_SCHOLARSHIP_PHRASES = (
    "سایر دانشگاه",
    "دانشگاه‌های کانادا",
    "دانشگاه‌های چین",
    "دانشگاه‌های اسپانیا",
    "دانشگاه‌ها (entrance",
    "entrance scholarships)",
    "گسترده‌ترین دسته",
)

# قطعات slug / نام → واژه‌های جستجو در نام بورسیه و program_key
_UNI_SIGNATURE_ALIASES: dict[str, tuple[str, ...]] = {
    "waterloo": ("waterloo", "uwaterloo", "واترلو"),
    "toronto": ("toronto", "utoronto", "تورنتو", "u of t", "uoft"),
    "mcgill": ("mcgill", "مکگیل", "مک گیل", "macgill"),
    "british-columbia": ("british columbia", "ubc", "columbia", "بریتیش کلمبیا", "ونکوور"),
    "columbia": ("ubc", "british columbia", "بریتیش کلمبیا"),
    "alberta": ("alberta", "ualberta", "آلبرتا", "ادمونتون"),
    "carleton": ("carleton", "کارلتون", "اتاوا"),
    "york": ("york university", "yorku", "یورک"),
    "ottawa": ("uottawa", "اتاوا"),
    "calgary": ("ucalgary", "کلگری"),
    "montreal": ("umontreal", "مونترال", "montreal"),
    "western": ("western university", "uwo", "وسترن"),
    "peking": ("peking", "پکن", "beijing"),
    "tsinghua": ("tsinghua", "چینهوا"),
    "jaen": ("jaen", "jaén", "خائن"),
    "upf": ("upf", "pompeu", "بارسلون"),
}


def _scholarship_detail_url(guide_url: str, slug: str) -> str:
    base = (guide_url or "").split("#", 1)[0].rstrip("/")
    return f"{base}#scholarship-{slug}"


def _is_generic_scholarship_program(
    *,
    program_key: str = "",
    name: str = "",
    provider: str = "",
) -> bool:
    pk = (program_key or "").strip().lower()
    if pk in _GENERIC_PROGRAM_KEYS:
        return True
    blob = f"{name} {provider}".lower()
    return any(phrase in blob for phrase in _GENERIC_SCHOLARSHIP_PHRASES)


def _build_university_match_signatures(top_university: dict[str, str] | None) -> set[str]:
    """امضاهای جستجو برای تطابق بورسیه با دانشگاه پیشنهادی."""
    if not top_university:
        return set()
    from .faq_search import _normalize_persian

    sigs: set[str] = set()
    slug = (top_university.get("slug") or "").lower()
    slug_parts = [p for p in slug.split("-") if p and p not in _UNI_NAME_STOP]

    for part in slug_parts:
        if len(part) >= 3:
            sigs.add(part)
        aliases = _UNI_SIGNATURE_ALIASES.get(part)
        if aliases:
            sigs.update(a.lower() for a in aliases)

    for i in range(len(slug_parts) - 1):
        pair = f"{slug_parts[i]}-{slug_parts[i + 1]}"
        aliases = _UNI_SIGNATURE_ALIASES.get(pair)
        if aliases:
            sigs.update(a.lower() for a in aliases)

    for field in ("name_fa", "name_en"):
        raw = (top_university.get(field) or "").strip()
        if not raw:
            continue
        norm = _normalize_persian(raw).lower()
        for part in re.split(r"[\s,،\-/()]+", norm):
            part = part.strip().strip(".,;:")
            if len(part) >= 3 and part not in _UNI_NAME_STOP:
                sigs.add(part)
        for key, aliases in _UNI_SIGNATURE_ALIASES.items():
            if key.replace("-", " ") in norm or key in slug:
                sigs.update(a.lower() for a in aliases)

    # واترلو / تورنتو از نام فارسی بدون فاصله
    name_fa = _normalize_persian(top_university.get("name_fa") or "").lower()
    if "واترلو" in name_fa:
        sigs.update(("waterloo", "uwaterloo", "واترلو"))
    if "تورنتو" in name_fa:
        sigs.update(("toronto", "utoronto", "تورنتو", "pearson"))
    if "مک" in name_fa and "گیل" in name_fa:
        sigs.add("mcgill")
    if "بریتیش" in name_fa or "کلمبیا" in name_fa:
        sigs.update(("ubc", "british columbia", "بریتیش کلمبیا"))

    # حذف امضاهای خیلی کوتاه یا مبهم (به‌جز ubc)
    return {s for s in sigs if len(s) >= 3 or s == "ubc"}


def _explicit_university_owner(name: str, provider: str) -> str | None:
    """دانشگاه صریح در نام/ارائه‌دهنده بورسیه (نه برچسب شهر)."""
    from .faq_search import _normalize_persian

    blob = _normalize_persian(f"{name} {provider}").lower()
    owners = (
        ("university of toronto", "toronto"),
        ("u of t", "toronto"),
        ("university of waterloo", "waterloo"),
        ("mcgill university", "mcgill"),
        ("york university", "york"),
        ("carleton university", "carleton"),
        ("university of british columbia", "ubc"),
        ("university of alberta", "alberta"),
        ("university of ottawa", "ottawa"),
        ("university of calgary", "calgary"),
        ("western university", "western"),
        ("universite de montreal", "montreal"),
        ("university of montreal", "montreal"),
    )
    for phrase, key in owners:
        if phrase in blob:
            return key
    for match in re.finditer(r"\(([^)]+)\)", blob):
        inner = match.group(1).strip().lower()
        if inner in _UNI_SIGNATURE_ALIASES:
            return inner
        for key in _UNI_SIGNATURE_ALIASES:
            if key in inner:
                return key
    return None


def _owner_matches_university(owner_key: str, signatures: set[str]) -> bool:
    if owner_key in signatures:
        return True
    slug_keys = {s for s in signatures if s in _UNI_SIGNATURE_ALIASES}
    if owner_key in slug_keys:
        return True
    for sig in signatures:
        aliases = _UNI_SIGNATURE_ALIASES.get(owner_key, ())
        if sig in aliases or owner_key in sig:
            return True
    return False


def _signature_in_blob(signature: str, blob: str) -> bool:
    if not signature or not blob:
        return False
    if signature in blob:
        return True
    if len(signature) >= 5:
        return False
    pattern = rf"(?<![a-z0-9\u0600-\u06ff]){re.escape(signature)}(?![a-z0-9\u0600-\u06ff])"
    return bool(re.search(pattern, blob))


def _matches_top_university(
    top_university: dict[str, str] | None,
    *,
    name: str,
    provider: str,
    extra: str = "",
    program_key: str = "",
    scholarship_slug: str = "",
    tags: str = "",
) -> bool:
    if not top_university:
        return False
    if _is_generic_scholarship_program(program_key=program_key, name=name, provider=provider):
        return False

    from .faq_search import _normalize_persian

    signatures = _build_university_match_signatures(top_university)
    if not signatures:
        return False

    owner = _explicit_university_owner(name, provider)
    if owner and not _owner_matches_university(owner, signatures):
        return False

    blob = _normalize_persian(
        f"{name} {provider} {extra} {tags} {program_key} {scholarship_slug}"
    ).lower()
    pk = (program_key or "").lower().replace("_", "-")
    sl = (scholarship_slug or "").lower()

    for sig in signatures:
        if _signature_in_blob(sig, blob):
            return True
        if len(sig) >= 4 and (sig in pk or sig in sl):
            return True
        # program_key مثل ca-waterloo-intl یا ca-mcgill-entrance
        if pk and sig in pk.split("-"):
            return True

    return False


def _score_db_scholarship(
    sch,
    guide,
    *,
    gpa: float | None,
    lang_ielts: float | None,
    target_degree: str,
    country_rank: int,
    top_country_code: str,
    top_university: dict[str, str] | None,
) -> tuple[float, list[str], bool]:
    score = 42.0 + (8 if sch.is_featured else 0) - sch.order * 0.15
    degree_mismatch = bool(guide.target_degree and guide.target_degree != target_degree)
    if degree_mismatch:
        score -= 18
    elif not guide.target_degree:
        score += 2
    if country_rank == 0:
        score += 14
    elif country_rank == 1:
        score += 7
    if guide.country.code == top_country_code:
        score += 6
    if gpa is not None and sch.min_gpa is not None:
        min_g = float(sch.min_gpa)
        if gpa >= min_g + 1:
            score += 10
        elif gpa >= min_g:
            score += 5
        else:
            score -= 8
    if lang_ielts is not None:
        if lang_ielts >= 6.5:
            score += 4
        elif lang_ielts >= 6.0:
            score += 2
    uni_match = _matches_top_university(
        top_university,
        name=sch.name,
        provider=sch.provider,
        extra=sch.eligibility or "",
        program_key=sch.program_key or "",
        scholarship_slug=sch.slug,
        tags=" ".join(sch.get_tags_list()),
    )
    if uni_match:
        score += 32
        if degree_mismatch:
            score += 14
            score = max(score, 58.0)
    reasons: list[str] = []
    if uni_match:
        uni_label = (top_university or {}).get("name_fa") or "دانشگاه پیشنهادی"
        reasons.append(f"مرتبط با {uni_label}")
        if degree_mismatch:
            reasons.append("مقطع راهنما با هدف شما متفاوت است — جزئیات را در صفحه بورسیه بخوانید")
    elif country_rank <= 1:
        reasons.append("هم‌راستا با کشور پیشنهادی شما")
    if gpa is not None and sch.min_gpa and gpa >= float(sch.min_gpa):
        reasons.append(f"معدل شما ({gpa:.1f}) در محدوده این برنامه است")
    elif gpa is None:
        reasons.append("پس از تکمیل معدل، امکان‌سنجی دقیق‌تر انجام می‌شود")
    if sch.lang_requirement and lang_ielts and lang_ielts >= 6.0:
        reasons.append("شرط زبان با نمره ثبت‌شده شما سازگار است")
    if not reasons:
        reasons.append("بر اساس داده بورسیه‌های فعال سایت")
    return score, reasons[:3], uni_match


def _serialize_db_scholarship(
    sch,
    guide,
    *,
    country_name: str,
    match_score: float,
    reasons: list[str],
    is_university_match: bool,
) -> dict[str, Any]:
    guide_url = guide.get_absolute_url()
    return {
        "id": sch.program_key or sch.slug,
        "slug": sch.slug,
        "country": guide.country.code,
        "country_name": country_name,
        "name": sch.name,
        "provider": sch.provider,
        "coverage": sch.coverage,
        "lang_note": sch.lang_requirement or "",
        "highlights": sch.get_highlights_list()[:4],
        "tags": sch.get_tags_list()[:4],
        "match_score": round(match_score, 1),
        "reasons": reasons,
        "url": _scholarship_detail_url(guide_url, sch.slug),
        "country_url": guide_url,
        "is_university_match": is_university_match,
        "is_featured": sch.is_featured,
    }


def _serialize_program(
    program: ScholarshipProgram,
    *,
    country_name: str,
    match_score: float,
    reasons: list[str],
    target_degree: str = "",
    top_university: dict[str, str] | None = None,
    is_university_match: bool = False,
) -> dict[str, Any]:
    guide_url = _scholarship_page_url(program.country, target_degree)
    slug = program.id
    try:
        from .models import CountryScholarship

        db_row = (
            CountryScholarship.objects.filter(
                program_key=program.id,
                is_active=True,
                guide__country__code=program.country,
                guide__is_active=True,
            )
            .select_related("guide")
            .first()
        )
        if db_row:
            slug = db_row.slug
            guide_url = db_row.guide.get_absolute_url()
            if not is_university_match:
                is_university_match = _matches_top_university(
                    top_university,
                    name=db_row.name,
                    provider=db_row.provider,
                    extra=db_row.eligibility or "",
                    program_key=db_row.program_key or program.id,
                    scholarship_slug=db_row.slug,
                    tags=db_row.tags or "",
                )
    except Exception:
        pass
    return {
        "id": program.id,
        "slug": slug,
        "country": program.country,
        "country_name": country_name,
        "name": program.name,
        "provider": program.provider,
        "coverage": program.coverage,
        "lang_note": program.lang_note,
        "highlights": list(program.highlights),
        "tags": list(program.tags),
        "match_score": round(match_score, 1),
        "reasons": reasons,
        "url": _scholarship_detail_url(guide_url, slug),
        "country_url": guide_url,
        "is_university_match": is_university_match,
        "is_featured": False,
    }


def _load_db_scholarship_rows(
    country_codes: list[str],
    target_degree: str,
    *,
    widen_degree_scope: bool = False,
) -> list[tuple[Any, Any]]:
    from django.db.models import Prefetch, Q

    from .models import CountryScholarship, CountryScholarshipGuide

    if widen_degree_scope:
        degree_q = Q()
    else:
        degree_q = Q(target_degree="") | Q(target_degree=target_degree)
    guides = (
        CountryScholarshipGuide.objects.filter(
            country__code__in=country_codes,
            is_active=True,
        )
        .filter(degree_q)
        .select_related("country")
        .prefetch_related(
            Prefetch(
                "scholarships",
                queryset=CountryScholarship.objects.filter(is_active=True).order_by(
                    "-is_featured", "order", "id"
                ),
            )
        )
        .order_by("country__order", "id")
    )
    rows: list[tuple[Any, Any]] = []
    for guide in guides:
        for sch in guide.scholarships.all():
            rows.append((guide, sch))
    return rows


def pick_scholarship_recommendations(
    profile,
    country_codes: list[str],
    *,
    scholarship_target: str = "",
    limit: int = 8,
    top_country_code: str = "",
    top_university: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    """پیشنهاد بورسیه از داده واقعی سایت + تطابق دانشگاه پیشنهادی."""
    from .evaluation_engine import _COUNTRY_LABELS

    if not country_codes:
        country_codes = ["canada", "china", "spain"]

    target_degree = _resolve_target_degree(
        scholarship_target, getattr(profile, "target_degree_level", 2)
    )
    gpa = getattr(profile, "gpa", None)
    lang_ielts = getattr(profile, "lang_ielts_equiv", None)
    research_score = getattr(profile, "research_score", 0)
    country_rank = {c: i for i, c in enumerate(country_codes)}
    primary = top_country_code or (country_codes[0] if country_codes else "")

    ranked: list[tuple[float, int, dict[str, Any]]] = []
    seen_keys: set[str] = set()

    for guide, sch in _load_db_scholarship_rows(
        country_codes, target_degree, widen_degree_scope=bool(top_university)
    ):
        code = guide.country.code
        rank = country_rank.get(code, 99)
        score, reasons, uni_match = _score_db_scholarship(
            sch,
            guide,
            gpa=gpa,
            lang_ielts=lang_ielts,
            target_degree=target_degree,
            country_rank=rank,
            top_country_code=primary,
            top_university=top_university,
        )
        if score <= 0:
            continue
        key = sch.program_key or f"{code}:{sch.slug}"
        if key in seen_keys:
            continue
        seen_keys.add(key)
        country_name = _COUNTRY_LABELS.get(code, guide.country.name)
        ranked.append(
            (
                score,
                1 if uni_match else 0,
                _serialize_db_scholarship(
                    sch,
                    guide,
                    country_name=country_name,
                    match_score=score,
                    reasons=reasons,
                    is_university_match=uni_match,
                ),
            )
        )

    for program in SCHOLARSHIP_PROGRAMS:
        if program.country not in country_codes:
            continue
        if program.id in seen_keys:
            continue
        rank = country_rank.get(program.country, 99)
        base = _score_program(
            program,
            gpa=gpa,
            lang_ielts=lang_ielts,
            research_score=research_score,
            target_degree=target_degree,
            country_rank=rank,
        )
        if base <= 0:
            continue
        uni_match = _matches_top_university(
            top_university,
            name=program.name,
            provider=program.provider,
            program_key=program.id,
            tags=" ".join(program.tags),
        )
        if uni_match:
            base += 28
        reasons: list[str] = []
        if uni_match:
            uni_label = (top_university or {}).get("name_fa") or "دانشگاه پیشنهادی"
            reasons.append(f"مرتبط با {uni_label}")
        elif rank <= 1:
            reasons.append("هم‌راستا با کشور پیشنهادی شما")
        if gpa is not None and program.min_gpa and gpa >= program.min_gpa:
            reasons.append(f"معدل شما ({gpa:.1f}) در محدوده رقابتی این برنامه است")
        elif gpa is None:
            reasons.append("پس از تکمیل معدل، امکان‌سنجی دقیق‌تر انجام می‌شود")
        if lang_ielts and lang_ielts >= 6.0:
            reasons.append("نمره زبان برای بسیاری بورسیه‌ها قابل اتکاست")
        if not reasons:
            reasons.append("گزینه پرطرفدار برای دانشجویان بین‌المللی")
        country_name = _COUNTRY_LABELS.get(program.country, program.country)
        seen_keys.add(program.id)
        ranked.append(
            (
                base,
                1 if uni_match else 0,
                _serialize_program(
                    program,
                    country_name=country_name,
                    match_score=base,
                    reasons=reasons,
                    target_degree=target_degree,
                    top_university=top_university,
                    is_university_match=uni_match,
                ),
            )
        )

    ranked.sort(key=lambda x: (-x[0], -x[1]))
    out: list[dict[str, Any]] = []
    per_country: dict[str, int] = {}
    uni_slots = 0
    for _, _, item in ranked:
        if len(out) >= limit:
            break
        code = item["country"]
        if per_country.get(code, 0) >= 3:
            continue
        if item.get("is_university_match"):
            if uni_slots >= 3:
                continue
            uni_slots += 1
        per_country[code] = per_country.get(code, 0) + 1
        out.append(item)
    return out


def build_country_scholarship_guides(
    *,
    target_degree: str = "",
    country_filter: str = "",
    programs_per_country: int = 3,
) -> list[dict[str, Any]]:
    """راهنمای بورسیه به تفکیک کشور — برای صفحه دانشگاه‌ها."""
    from .evaluation_engine import _get_active_country_codes

    try:
        from .models import StudyCountry

        active = _get_active_country_codes()
        qs = StudyCountry.objects.filter(is_active=True, code__in=active).order_by("order", "id")
        if country_filter:
            qs = qs.filter(code=country_filter)
        countries = list(qs)
    except Exception:
        countries = []

    degree = target_degree if target_degree in (_DEGREE_BACHELOR, _DEGREE_MASTER, _DEGREE_PHD) else ""

    from .models import CountryScholarshipGuide

    guides: list[dict[str, Any]] = []
    for sc in countries:
        db_guide = (
            CountryScholarshipGuide.objects.filter(
                country=sc, is_active=True, target_degree=degree
            )
            .prefetch_related("scholarships")
            .first()
        )
        if db_guide:
            db_programs = list(
                db_guide.scholarships.filter(is_active=True).order_by(
                    "-is_featured", "order", "id"
                )[:programs_per_country]
            )
            programs_payload = [
                {
                    "name": s.name,
                    "provider": s.provider,
                    "coverage": s.coverage,
                    "highlights": s.get_highlights_list(),
                    "tags": s.get_tags_list(),
                }
                for s in db_programs
            ]
            intro = _strip_html(db_guide.intro or sc.scholarship_info, 320)
            page_url = db_guide.get_absolute_url()
        else:
            programs = [
                p
                for p in SCHOLARSHIP_PROGRAMS
                if p.country == sc.code and (not degree or _program_matches_degree(p, degree))
            ]
            programs = sorted(programs, key=lambda p: -p.priority)[:programs_per_country]
            programs_payload = [
                {
                    "name": p.name,
                    "provider": p.provider,
                    "coverage": p.coverage,
                    "highlights": list(p.highlights),
                    "tags": list(p.tags),
                }
                for p in programs
            ]
            intro = _strip_html(sc.scholarship_info, 320)
            page_url = _scholarship_page_url(sc.code, degree)

        guides.append(
            {
                "code": sc.code,
                "name": sc.name,
                "flag_url": _country_flag_url(sc.code),
                "intro": intro,
                "country_url": page_url,
                "evaluation_url": reverse("evaluation")
                + f"?target_degree={degree or _DEGREE_BACHELOR}&intent=scholarship",
                "programs": programs_payload,
            }
        )
    return guides
