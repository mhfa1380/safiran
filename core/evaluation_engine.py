"""
موتور پیشنهاد هوشمند فرم ارزیابی مهاجرت تحصیلی (نسخه ۴).
پروفایل ساختاریافته، قوانین مسیر تحصیلی، پارس معدل/زبان، انتخاب منسجم.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from collections.abc import Callable
from typing import Any

from django.conf import settings
from django.core.cache import cache
from django.urls import reverse

from .cache_utils import evaluation_catalog_cache_key

from .evaluation_copy import (
    build_analysis_points,
    build_coherence_note_full,
    build_coherence_note_partial,
    build_detail_full,
    build_detail_partial,
    build_summary_full,
    build_summary_partial,
    collect_insights,
    confidence_label,
    dedupe_reasons_against_narrative,
    field_desired_relation,
    make_narrative_picker,
)
from .evaluation_blog import (
    blog_country_hints,
    blog_insights,
    load_blog_catalog,
    pick_scored_blogs,
)
from .evaluation_courses import build_language_pathway
from .faq_search import _expand_tokens, _fuzzy_ratio, _normalize_persian, tokenize_query
from .models import (
    ConsultationRequest,
    EvaluationRequest,
    FAQ,
    Major,
    MonthlyAchievement,
    University,
)

ENGINE_VERSION = "5.7"

_EVAL_CATALOG_TTL = int(getattr(settings, "EVAL_CATALOG_CACHE_SECONDS", 300))
_EVAL_MAX_MAJORS_TRIPLE = 10
_EVAL_MAX_UNIS_TRIPLE = 20
_EVAL_MAX_COMBINED = 400
_EVAL_MAJOR_PREFILTER = 50

from .study_destinations import ALL_DESTINATION_LABELS

_COUNTRY_LABELS = dict(ALL_DESTINATION_LABELS)
_DEFAULT_COUNTRIES = frozenset({"canada", "spain", "china"})

_COUNTRY_INTRO = {
    "canada": "کانادا با دانشگاه‌های معتبر و مسیر اقامت پس از تحصیل، از محبوب‌ترین مقصدهاست.",
    "spain": "اسپانیا با هزینه مناسب‌تر و دانشگاه‌های اروپایی گزینه جذابی است.",
    "china": "چین با بورسیه‌های متنوع و رشد علمی سریع در آسیا پیشرو است.",
    "germany": "آلمان با شهریه پایین و کیفیت آموزشی بالا در اروپا محبوب است.",
    "italy": "ایتالیا با هزینه متعادل و دانشگاه‌های معتبر گزینه جذابی در اروپاست.",
}

_COUNTRY_FLAG_ISO = {
    "canada": "ca",
    "spain": "es",
    "china": "cn",
    "germany": "de",
    "italy": "it",
}

# حداقل نمره زبان تقریبی (IELTS-equivalent) برای پذیرش راحت‌تر
_LANG_THRESHOLDS = {
    "canada": {"strong": 6.5, "ok": 6.0, "min": 5.5},
    "spain": {"strong": 6.5, "ok": 5.5, "min": 5.0},
    "china": {"strong": 6.0, "ok": 5.5, "min": 5.0},
    "germany": {"strong": 6.5, "ok": 6.0, "min": 5.5},
    "italy": {"strong": 6.0, "ok": 5.5, "min": 5.0},
}

_COUNTRY_LANG_TESTS = {
    "canada": frozenset({"ielts", "toefl", "pte", "duolingo"}),
    "spain": frozenset({"ielts", "toefl", "delf", "pte", "duolingo"}),
    "china": frozenset({"ielts", "toefl", "yos", "duolingo", "pte"}),
    "germany": frozenset({"ielts", "toefl", "testdaf", "pte"}),
    "italy": frozenset({"ielts", "toefl", "delf", "pte"}),
}

# مترادف‌های رایج برای تطابق رشته
_FIELD_SYNONYMS: dict[str, frozenset[str]] = {
    "پزشکی": frozenset({"medicine", "md", "mbbs", "پزشک", "علوم پزشکی"}),
    "مهندسی": frozenset({"engineering", "مهندس"}),
    "کامپیوتر": frozenset({"computer", "cs", "it", "نرم", "نرم‌افزار", "software"}),
    "مدیریت": frozenset({"mba", "business", "بازرگانی"}),
    "حقوق": frozenset({"law", "legal"}),
    "پرستاری": frozenset({"nursing", "nurse"}),
    "داروسازی": frozenset({"pharmacy", "دارو"}),
}

_MEDICINE_KEYWORDS = frozenset({"پزشکی", "medicine", "mbbs", "md", "پزشک", "علوم پزشکی"})

_DENTAL_MAJOR_KEYWORDS = frozenset(
    {"دندان", "dentistry", "dental", "دندانپزشکی", "ارتودنسی", "پروتز", "اندودنتیک"}
)
_HEALTH_SCIENCE_KEYWORDS = frozenset(
    {
        "سلامت",
        "health",
        "بهداشت",
        "public health",
        "epidemi",
        "اپیدمی",
        "زیست",
        "biology",
        "biomedical",
        "بیومد",
        "پرستاری",
        "nursing",
        "داروسازی",
        "pharmacy",
        "فیزیو",
        "تغذیه",
        "nutrition",
        "میکروبیولوژی",
        "immun",
        "ایمنی",
    }
)
_POSTGRAD_TRACK_KEYWORDS = frozenset(
    {
        "تخصص",
        "فلو",
        "specialization",
        "speciality",
        "specialty",
        "fellowship",
        "residency",
        "ارشد",
        "دکتری",
        "phd",
        "doctorate",
        "پژوهش",
        "research",
        "mph",
        "msc",
        "master",
    }
)

_FIELD_CLUSTERS: tuple[tuple[str, frozenset[str]], ...] = (
    (
        "engineering",
        frozenset(
            {
                "مهندسی",
                "کامپیوتر",
                "نرم",
                "برق",
                "مکانیک",
                "عمران",
                "معماری",
                "صنایع",
                "شیمی",
                "مواد",
                "هوش",
                "ربات",
                "الکترونیک",
                "عمران",
                "computer",
                "engineering",
                "it",
                "software",
            }
        ),
    ),
    (
        "medical",
        frozenset(
            {
                "پزشکی",
                "پرستاری",
                "دارو",
                "دندان",
                "بهداشت",
                "زیست",
                "بیولوژی",
                "پزشک",
                "دامپزشکی",
                "medical",
                "nursing",
                "pharmacy",
                "dentistry",
            }
        ),
    ),
    (
        "business",
        frozenset(
            {
                "مدیریت",
                "mba",
                "اقتصاد",
                "حسابداری",
                "بازرگانی",
                "مالی",
                "بورس",
                "کارآفرینی",
                "business",
                "finance",
                "marketing",
                "accounting",
            }
        ),
    ),
    (
        "humanities",
        frozenset(
            {
                "حقوق",
                "روان",
                "جامعه",
                "ادبیات",
                "زبان",
                "تاریخ",
                "فلسفه",
                "علوم",
                "انسانی",
                "حقوق",
                "law",
                "psychology",
            }
        ),
    ),
    (
        "arts",
        frozenset({"هنر", "طراحی", "موسیقی", "سینما", "گرافیک", "معماری داخلی", "عکاسی", "art", "design"}),
    ),
    (
        "science",
        frozenset(
            {
                "فیزیک",
                "شیمی",
                "ریاضی",
                "آمار",
                "نجوم",
                "علوم",
                "زیست",
                "ژنتیک",
                "physics",
                "chemistry",
                "biology",
            }
        ),
    ),
)

_DEGREE_LEVEL = {
    EvaluationRequest.DEGREE_DIPLOMA: 1,
    EvaluationRequest.DEGREE_BACHELOR: 2,
    EvaluationRequest.DEGREE_MASTER: 3,
    EvaluationRequest.DEGREE_PHD: 4,
}

_DEGREE_NEXT = {
    EvaluationRequest.DEGREE_DIPLOMA: EvaluationRequest.DEGREE_BACHELOR,
    EvaluationRequest.DEGREE_BACHELOR: EvaluationRequest.DEGREE_MASTER,
    EvaluationRequest.DEGREE_MASTER: EvaluationRequest.DEGREE_PHD,
    EvaluationRequest.DEGREE_PHD: EvaluationRequest.DEGREE_PHD,
}

# کشورهایی که برای هر خوشه رشته historically بهتر عمل می‌کنند
_CLUSTER_COUNTRY_AFFINITY: dict[str, dict[str, float]] = {
    "engineering": {"canada": 6, "china": 8, "spain": 4, "germany": 9, "italy": 5},
    "medical": {"canada": 8, "china": 7, "spain": 5, "germany": 6, "italy": 6},
    "business": {"canada": 7, "spain": 8, "china": 5, "germany": 7, "italy": 6},
    "humanities": {"spain": 7, "canada": 6, "china": 3, "germany": 6, "italy": 7},
    "arts": {"spain": 8, "canada": 5, "china": 3, "germany": 5, "italy": 8},
    "science": {"canada": 8, "china": 7, "spain": 5, "germany": 8, "italy": 6},
}


@dataclass
class ApplicantProfile:
    """سیگنال‌های استخراج‌شده از فرم — یک‌بار محاسبه می‌شود."""

    eval_req: EvaluationRequest
    gpa: float | None
    gpa_uncertain: bool
    gpa_note: str
    lang_score: float | None
    lang_ielts_equiv: float | None
    age: int | None
    clusters: set[str]
    study_text: str
    field_text: str
    desired_text: str
    desired_countries: list[str]
    research_score: int
    degree_level: int
    target_degree_level: int
    has_language_cert: bool
    language_test: str
    is_graduate_track: bool
    wants_direct_medicine: bool
    pathway_notes: list[str] = field(default_factory=list)
    scholarship_target: str = ""
    resolved_field_slugs: list[str] = field(default_factory=list)
    resolved_desired_slugs: list[str] = field(default_factory=list)


@dataclass
class CatalogSnapshot:
    """کش داده‌های سایت برای یک درخواست."""

    majors: list[Major]
    universities: list[University]
    achievements: list[MonthlyAchievement]
    faqs: list[FAQ]
    blogs: list[dict[str, Any]]
    country_codes: frozenset[str]
    majors_by_country: dict[str, list[Major]]
    majors_global: list[Major]
    unis_by_country: dict[str, list[University]]
    major_uni_links: dict[tuple[str, str], frozenset[str]] = field(default_factory=dict)

    def majors_for_country(self, code: str) -> list[Major]:
        local = self.majors_by_country.get(code, [])
        if not self.majors_global:
            return local
        return local + self.majors_global

    def uni_slugs_for_major(self, major_slug: str, country_code: str) -> frozenset[str]:
        return self.major_uni_links.get((major_slug, country_code), frozenset())


@dataclass
class ScoredItem:
    score: float
    reasons: list[str] = field(default_factory=list)


def _persian_digits_to_en(text: str) -> str:
    from .numeric_normalize import digits_to_en

    return digits_to_en(text)


def parse_average_grade_detail(raw: str) -> tuple[float | None, bool, str]:
    """معدل را به مقیاس ۰–۲۰ برمی‌گرداند؛ uncertain برای تبدیل درصد یا ابهام."""
    if not raw:
        return None, False, ""
    s = _persian_digits_to_en(raw.strip().replace(",", "."))
    if "%" in s or "درصد" in s:
        m = re.search(r"(\d+(?:\.\d+)?)", s)
        if m:
            pct = float(m.group(1))
            if 0 < pct <= 100:
                return round(pct * 0.2, 2), True, f"معدل {pct:g}٪ به مقیاس ۲۰ تبدیل شد"
        return None, True, "فرمت درصد معدل نامشخص است"

    m = re.search(r"(\d+(?:\.\d+)?)", s)
    if not m:
        return None, False, ""
    val = float(m.group(1))

    if val <= 4.5:
        return round(val * 5.0, 2), False, ""

    if 5.0 <= val <= 20.0:
        return round(val, 2), False, ""

    if 20.0 < val <= 100.0:
        return round(val * 0.2, 2), True, f"مقدار {val:g} به‌عنوان درصد (از ۱۰۰) به مقیاس ۲۰ تبدیل شد"

    return None, True, f"مقدار معدل ({val:g}) قابل تفسیر نیست؛ کارشناس در تماس اصلاح می‌کند"


def parse_average_grade(raw: str) -> float | None:
    return parse_average_grade_detail(raw)[0]


def parse_language_score(raw: str) -> float | None:
    if not raw:
        return None
    s = _persian_digits_to_en(raw)
    m = re.search(r"(\d+(?:\.\d+)?)", s)
    return float(m.group(1)) if m else None


def language_to_ielts_equiv(test_type: str, raw_score: float | None) -> float | None:
    """تبدیل تقریبی نمرات آزمون‌های مختلف به معادل IELTS."""
    if raw_score is None or test_type in ("", EvaluationRequest.TEST_NONE):
        return None
    if test_type == EvaluationRequest.TEST_IELTS:
        return min(9.0, max(0.0, raw_score))
    if test_type == EvaluationRequest.TEST_TOEFL:
        if raw_score <= 9:
            return min(9.0, raw_score)
        return min(9.0, max(4.0, 3.5 + (raw_score - 30) * 0.036))
    if test_type == EvaluationRequest.TEST_DUOLINGO:
        return min(9.0, max(4.0, 4.0 + max(0.0, raw_score - 85) * 0.025))
    if test_type == EvaluationRequest.TEST_PTE:
        return min(9.0, max(4.0, 4.0 + max(0.0, raw_score - 35) * 0.04))
    if test_type == EvaluationRequest.TEST_DELF:
        return 6.5 if raw_score >= 3 else (6.0 if raw_score >= 2 else 5.0)
    if test_type == EvaluationRequest.TEST_TESTDAF:
        return 6.5 if raw_score >= 4 else (6.0 if raw_score >= 3 else 5.0)
    if test_type == EvaluationRequest.TEST_YOS:
        return min(7.0, max(5.0, 4.5 + raw_score * 0.015))
    if raw_score <= 9.0:
        return raw_score
    return min(9.0, 4.0 + raw_score / 20.0)


def _wants_direct_medicine(profile: ApplicantProfile) -> bool:
    if "medical" not in profile.clusters:
        return False
    blob = _normalize_persian(profile.study_text).lower()
    return any(k in blob for k in _MEDICINE_KEYWORDS)


def _major_text_blob(major: Major) -> str:
    return _normalize_persian(
        f"{major.title} {major.short_description or ''} {major.description or ''}"
    ).lower()


def _is_direct_medicine_major(major: Major) -> bool:
    blob = _major_text_blob(major)
    return any(k in blob for k in _MEDICINE_KEYWORDS)


def _is_dental_major(major: Major) -> bool:
    blob = _major_text_blob(major)
    return any(k in blob for k in _DENTAL_MAJOR_KEYWORDS)


def _is_generic_medicine_major(major: Major) -> bool:
    """پزشکی عمومی / MBBS بدون تخصص یا حوزه دندان."""
    if _is_dental_major(major):
        return False
    blob = _major_text_blob(major)
    if not any(k in blob for k in _MEDICINE_KEYWORDS):
        return False
    if any(k in blob for k in _POSTGRAD_TRACK_KEYWORDS):
        return False
    return True


def _is_postgrad_health_major(major: Major) -> bool:
    """برنامه‌های مرتبط با سلامت، تخصص یا ادامه تحصیل حوزه‌ای."""
    blob = _major_text_blob(major)
    if _is_dental_major(major):
        return True
    if any(k in blob for k in _HEALTH_SCIENCE_KEYWORDS):
        return True
    if any(k in blob for k in _POSTGRAD_TRACK_KEYWORDS) and (
        _is_direct_medicine_major(major) or "سلامت" in blob or "health" in blob
    ):
        return True
    return False


def _dental_to_medicine_major_adjustment(
    profile: ApplicantProfile, major: Major, country_code: str
) -> tuple[float, list[str]]:
    """اولویت دندان/علوم سلامت؛ جریمه پزشکی عمومی برای مقاطع بالاتر."""
    if field_desired_relation(profile) != "dental_to_medicine":
        return 0.0, []

    score = 0.0
    reasons: list[str] = []

    if _is_dental_major(major):
        score += 42.0
        if profile.degree_level >= 3:
            reasons.append(
                "ادامه در حوزه دندانپزشکی/تخصص دندان با سوابق فعلی شما سازگارتر از پزشکی عمومی است"
            )
        else:
            reasons.append("رشته دندانپزشکی با زمینه تحصیلی و علاقه شما به حوزه سلامت هم‌خوان است")
    elif _is_postgrad_health_major(major) and not _is_generic_medicine_major(major):
        score += 24.0
        reasons.append("برنامه مرتبط با علوم سلامت و سابقه دندانپزشکی شما")
    elif _is_generic_medicine_major(major):
        if profile.degree_level >= 3:
            score -= 58.0
            reasons.append(
                "پزشکی عمومی (مثل MBBS) معمولاً با دکتری/ارشد دندانپزشکی هم‌راستا نیست"
            )
        elif profile.degree_level == 2:
            score -= 30.0
            reasons.append("ورود مستقیم به پزشکی عمومی برای این پروفایل کمتر توصیه می‌شود")
        else:
            score -= 12.0
            if country_code == "china":
                score += 6.0
                reasons.append("در چین مسیر MBBS رایج‌تر است؛ با وجود این، مسیر دندان/سلامت هم بررسی شود")

    return score, reasons


def _pathway_country_adjustment(profile: ApplicantProfile, code: str) -> tuple[float, list[str]]:
    """جریمه/پاداش کشور بر اساس مسیر تحصیلی واقع‌بینانه."""
    if not profile.wants_direct_medicine:
        return 0.0, []

    score = 0.0
    reasons: list[str] = []
    western = frozenset({"canada", "spain", "germany", "italy"})

    if profile.degree_level <= 1:
        if code in western:
            score -= 20.0
            reasons.append(
                "برای پزشکی در این کشور معمولاً ابتدا لیسانس مرتبط (مثلاً زیست/پرستاری) لازم است"
            )
        if code == "china":
            score += 12.0
            reasons.append("چین مسیر MBBS و پیش‌دانشگاهی پزشکی شناخته‌شده‌تری دارد")
    elif profile.degree_level == 2:
        if code in western:
            score -= 10.0
            reasons.append("ورود مستقیم به پزشکی پس از لیسانس در این کشور محدود است")
        if code == "china":
            score += 8.0

    if profile.language_test == EvaluationRequest.TEST_NONE and code in western:
        if ev_timeline_soon(profile):
            score -= 8.0
            reasons.append("بدون مدرک زبان، اپلای زیر یک سال به این کشور پرریسک است")

    return score, reasons


def ev_timeline_soon(profile: ApplicantProfile) -> bool:
    return profile.eval_req.apply_timeline == EvaluationRequest.APPLY_SOON


def _pathway_major_adjustment(
    profile: ApplicantProfile, major: Major, country_code: str
) -> tuple[float, list[str]]:
    if not profile.wants_direct_medicine or not _is_direct_medicine_major(major):
        return 0.0, []
    if profile.degree_level <= 1:
        if country_code == "china":
            return 8.0, ["مسیر MBBS/پیش‌دانشگاهی پزشکی در چین برای دیپلم متداول‌تر است"]
        return -50.0, [
            "پذیرش مستقیم پزشکی با دیپلم در این مقصد معمولاً ممکن نیست — "
            "گام بعدی: لیسانس مرتبط (زیست، پرستاری و …)"
        ]
    if profile.degree_level == 2:
        if country_code == "china":
            return 4.0, []
        return -15.0, ["برای پزشکی معمولاً مسیر لیسانس مرتبط یا آمادگی بیشتر لازم است"]
    return 0.0, []


def _expand_field_tokens(text: str) -> list[str]:
    tokens = tokenize_query(text)
    expanded: list[str] = []
    text_n = _normalize_persian(text).lower()
    for token in tokens:
        expanded.append(token)
        for key, syns in _FIELD_SYNONYMS.items():
            if key in text_n or token in syns:
                expanded.extend(syns)
                expanded.append(key)
    return list(dict.fromkeys(expanded))


def parse_world_rank(rank_str: str) -> float:
    if not rank_str:
        return 400.0
    nums = [int(x) for x in re.findall(r"\d+", rank_str)]
    if not nums:
        return 400.0
    if len(nums) >= 2 and ("-" in rank_str or "–" in rank_str):
        return (nums[0] + nums[1]) / 2.0
    return float(nums[0])


def _get_active_country_codes() -> frozenset[str]:
    try:
        from .models import StudyCountry

        codes = set(StudyCountry.objects.filter(is_active=True).values_list("code", flat=True))
        codes &= set(_COUNTRY_LABELS.keys()) - {"other"}
        if codes:
            return frozenset(codes)
    except Exception:
        pass
    return _DEFAULT_COUNTRIES


def _country_meta(code: str) -> dict[str, str]:
    try:
        from .models import StudyCountry

        sc = StudyCountry.objects.filter(code=code, is_active=True).first()
        if sc:
            return {
                "name": sc.name,
                "headline": sc.headline or "",
                "intro": (sc.intro or "")[:200],
            }
    except Exception:
        pass
    return {
        "name": _COUNTRY_LABELS.get(code, code),
        "headline": _COUNTRY_INTRO.get(code, ""),
        "intro": _COUNTRY_INTRO.get(code, ""),
    }


def _detect_clusters(text: str) -> set[str]:
    text_l = _normalize_persian(text).lower()
    found: set[str] = set()
    for name, keywords in _FIELD_CLUSTERS:
        for kw in keywords:
            if kw in text_l:
                found.add(name)
                break
    return found


def _text_match_score_fast(query: str, *texts: str) -> float:
    """تطابق سبک برای پیش‌فیلتر — بدون fuzzy سنگین."""
    if not query.strip():
        return 0.0
    hay = " ".join(_normalize_persian(t).lower() for t in texts if t)
    if not hay:
        return 0.0
    q = _normalize_persian(query).lower()
    if q in hay:
        return 1.0
    tokens = [t for t in _expand_tokens(_expand_field_tokens(query)) if len(t) >= 2]
    if not tokens:
        tokens = [q]
    hits = sum(1 for t in tokens if t in hay)
    return min(1.0, hits / len(tokens)) if tokens else 0.0


def _text_match_score(query: str, *texts: str) -> float:
    if not query.strip():
        return 0.0
    tokens = _expand_tokens(_expand_field_tokens(query))
    if not tokens:
        tokens = [_normalize_persian(query).lower()]
    hay = " ".join(_normalize_persian(t).lower() for t in texts if t)
    if not hay:
        return 0.0
    words = [w for w in re.split(r"[\s,،؛/]+", hay) if len(w) >= 2]
    if len(words) > 48:
        words = words[:48]
    scores: list[float] = []
    for token in tokens:
        if len(token) < 2:
            continue
        if token in hay:
            scores.append(1.0)
            continue
        best = 0.0
        for word in words:
            if token in word or word in token:
                best = 1.0
                break
            if abs(len(word) - len(token)) > 8:
                continue
            ratio = _fuzzy_ratio(token, word)
            if ratio > best:
                best = ratio
                if best >= 0.92:
                    break
        scores.append(best)
    if not scores:
        return 0.0
    avg = sum(scores) / len(scores)
    hit_ratio = sum(1 for s in scores if s >= 0.55) / len(scores)
    return min(1.0, avg * 0.75 + hit_ratio * 0.25)


def _parse_desired_countries(raw: str) -> list[str]:
    if not raw:
        return []
    mapping = {
        "china": "china",
        "چین": "china",
        "canada": "canada",
        "کانادا": "canada",
        "spain": "spain",
        "اسپانیا": "spain",
        "germany": "germany",
        "آلمان": "germany",
        "italy": "italy",
        "ایتالیا": "italy",
        "other": "",
        "سایر": "",
        "not_sure": "",
    }
    active = _get_active_country_codes()
    codes: list[str] = []
    for part in re.split(r"[,،]+", raw):
        p = part.strip().lower()
        code = mapping.get(p, p if p in active else "")
        if code and code not in codes:
            codes.append(code)
    return codes


def _build_applicant_profile(eval_req: EvaluationRequest) -> ApplicantProfile:
    gpa, gpa_uncertain, gpa_note = parse_average_grade_detail(eval_req.average_grade or "")
    lang_raw = parse_language_score(eval_req.language_score or "")
    test_type = eval_req.language_test_type or EvaluationRequest.TEST_NONE
    lang_ielts = language_to_ielts_equiv(test_type, lang_raw)
    age = None
    if eval_req.birth_year:
        try:
            from .utils import gregorian_to_jalali
            from datetime import date

            jy, _, _ = gregorian_to_jalali(date.today().year, date.today().month, date.today().day)
            age = max(15, jy - int(eval_req.birth_year))
        except Exception:
            age = None

    field_text = _normalize_persian(eval_req.field_of_study or "")
    desired_text = _normalize_persian(eval_req.desired_major or "")
    notes = _normalize_persian(eval_req.notes or "")
    study_text = " ".join(filter(None, [field_text, desired_text, notes]))

    degree_level = _DEGREE_LEVEL.get(eval_req.current_degree, 2)
    target_level = degree_level
    if eval_req.current_degree != EvaluationRequest.DEGREE_PHD:
        target_level = _DEGREE_LEVEL.get(_DEGREE_NEXT.get(eval_req.current_degree, eval_req.current_degree), degree_level)

    research = sum(
        [
            eval_req.has_journal_article,
            eval_req.has_conference_article,
            eval_req.has_book,
            eval_req.has_international_tests,
        ]
    )

    profile = ApplicantProfile(
        eval_req=eval_req,
        gpa=gpa,
        gpa_uncertain=gpa_uncertain,
        gpa_note=gpa_note,
        lang_score=lang_raw,
        lang_ielts_equiv=lang_ielts,
        age=age,
        clusters=_detect_clusters(study_text),
        study_text=study_text,
        field_text=field_text,
        desired_text=desired_text,
        desired_countries=_parse_desired_countries(eval_req.desired_countries or ""),
        research_score=research,
        degree_level=degree_level,
        target_degree_level=target_level,
        has_language_cert=bool(eval_req.has_ielts or eval_req.language_test_type != EvaluationRequest.TEST_NONE),
        language_test=test_type,
        is_graduate_track=target_level >= 3,
        wants_direct_medicine=False,
    )
    profile.wants_direct_medicine = _wants_direct_medicine(profile)
    if field_desired_relation(profile) == "dental_to_medicine":
        profile.pathway_notes.insert(
            0,
            "با سوابق دندانپزشکی و علاقه به پزشکی، اولویت پیشنهاد روی دندان، علوم سلامت و تخصص است "
            "نه ورود مجدد به پزشکی عمومی (MBBS).",
        )
    elif profile.wants_direct_medicine and profile.degree_level <= 2:
        profile.pathway_notes.append(
            "برای پزشکی، معمولاً ابتدا مقطع پایه (لیسانس مرتبط) یا مسیر MBBS/پیش‌دانشگاهی "
            "پیشنهاد می‌شود؛ کارشناس مسیر دقیق را در تماس توضیح می‌دهد."
        )
    if gpa_note and gpa_uncertain:
        profile.pathway_notes.append(gpa_note)
    return profile


def _resolve_text_to_major_slugs(
    text: str,
    majors: list[Major],
    *,
    limit: int = 3,
) -> list[str]:
    """تطبیق متن آزاد فرم با رشته‌های کاتالوگ (دقیق + فازی)."""
    if not text or not majors:
        return []
    from .major_search import _fuzzy_score_for_major

    norm_text = _normalize_persian(text).lower()
    scored: list[tuple[float, str]] = []
    for major in majors:
        fs = _fuzzy_score_for_major(major, text, fast=True)
        norm_title = _normalize_persian(major.title or "").lower()
        if norm_text == norm_title:
            fs = max(fs, 24.0)
        elif norm_text in norm_title or norm_title in norm_text:
            fs = max(fs, 18.0)
        if fs >= 5.5:
            scored.append((fs, major.slug))
    scored.sort(key=lambda x: (-x[0], x[1]))
    out: list[str] = []
    seen: set[str] = set()
    for _, slug in scored:
        if slug in seen:
            continue
        seen.add(slug)
        out.append(slug)
        if len(out) >= limit:
            break
    return out


def _enrich_profile_resolved_majors(profile: ApplicantProfile, catalog: CatalogSnapshot) -> None:
    """رشته‌های کاتالوگ نزدیک به متن فرم — برای امتیازدهی دقیق‌تر."""
    profile.resolved_field_slugs = _resolve_text_to_major_slugs(
        profile.field_text, catalog.majors, limit=3
    )
    profile.resolved_desired_slugs = _resolve_text_to_major_slugs(
        profile.desired_text, catalog.majors, limit=3
    )


def _build_major_uni_link_index() -> dict[tuple[str, str], frozenset[str]]:
    from .models import UniversityMajorLink

    rows = UniversityMajorLink.objects.filter(major__is_active=True).values_list(
        "major__slug", "university__slug", "university__country"
    )
    raw: dict[tuple[str, str], set[str]] = {}
    for major_slug, uni_slug, country in rows:
        if not major_slug or not uni_slug or not country:
            continue
        raw.setdefault((major_slug, country), set()).add(uni_slug)
    return {key: frozenset(slugs) for key, slugs in raw.items()}


def warm_evaluation_catalog() -> None:
    """پیش‌گرم کردن کش کاتالوگ هنگام باز شدن فرم — تحلیل سریع‌تر پس از ارسال."""
    _load_catalog()


def _load_catalog() -> CatalogSnapshot:
    cache_key = evaluation_catalog_cache_key()
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    country_codes = _get_active_country_codes()
    majors = list(
        Major.objects.filter(is_active=True).only(
            "pk",
            "slug",
            "title",
            "short_description",
            "country",
            "order",
        )
    )
    universities = list(
        University.objects.all().only(
            "pk",
            "slug",
            "name_fa",
            "name_en",
            "country",
            "world_rank",
            "short_description",
            "description",
            "city",
            "is_approved_by_mo_science",
        )
    )
    achievements = list(MonthlyAchievement.objects.filter(is_active=True)[:30])
    faqs = list(FAQ.objects.filter(is_active=True).select_related("category")[:80])
    blogs = load_blog_catalog(limit=80)

    majors_by_country: dict[str, list[Major]] = {c: [] for c in country_codes}
    majors_global: list[Major] = []
    unis_by_country: dict[str, list[University]] = {c: [] for c in country_codes}
    for m in majors:
        if m.country in majors_by_country:
            majors_by_country[m.country].append(m)
        elif not m.country:
            majors_global.append(m)
    for u in universities:
        if u.country in unis_by_country:
            unis_by_country[u.country].append(u)

    snapshot = CatalogSnapshot(
        majors=majors,
        universities=universities,
        achievements=achievements,
        faqs=faqs,
        blogs=blogs,
        country_codes=country_codes,
        majors_by_country=majors_by_country,
        majors_global=majors_global,
        unis_by_country=unis_by_country,
        major_uni_links=_build_major_uni_link_index(),
    )
    cache.set(cache_key, snapshot, _EVAL_CATALOG_TTL)
    return snapshot


def _prefilter_majors_for_scoring(
    profile: ApplicantProfile,
    majors: list[Major],
    *,
    limit: int = _EVAL_MAJOR_PREFILTER,
) -> list[Major]:
    """پیش‌فیلتر سریع رشته‌ها قبل از امتیازدهی کامل."""
    if len(majors) <= limit:
        return majors
    needles = [t for t in (profile.field_text, profile.desired_text, profile.study_text) if t]
    if not needles:
        return sorted(majors, key=lambda m: (m.order, m.pk))[:limit]

    def cheap_key(m: Major) -> float:
        blob = f"{m.title} {m.short_description}"
        return max(_text_match_score_fast(n, blob) for n in needles)

    return sorted(majors, key=lambda m: (-cheap_key(m), m.order, m.pk))[:limit]


def _universities_for_triple_scoring(
    unis: list[University],
    limit: int = _EVAL_MAX_UNIS_TRIPLE,
) -> list[University]:
    """فقط برترین دانشگاه‌ها (بر اساس رتبه جهانی) برای ترکیب سه‌گانه."""
    if len(unis) <= limit:
        return unis
    return sorted(
        unis,
        key=lambda u: parse_world_rank(u.world_rank or "") or 99999.0,
    )[:limit]


def _language_fit(profile: ApplicantProfile, country_code: str) -> tuple[float, list[str]]:
    reasons: list[str] = []
    score = 0.0
    thresholds = _LANG_THRESHOLDS.get(country_code, _LANG_THRESHOLDS["canada"])
    test = profile.language_test
    ielts = profile.lang_ielts_equiv

    if test != EvaluationRequest.TEST_NONE and test in _COUNTRY_LANG_TESTS.get(country_code, frozenset()):
        score += 12.0
        reasons.append(f"آزمون {profile.eval_req.get_language_test_type_display()} با این کشور سازگار است")

    if ielts is not None:
        if ielts >= thresholds["strong"]:
            score += 14.0
            reasons.append("نمره زبان (معادل IELTS) برای پذیرش قوی مناسب است")
        elif ielts >= thresholds["ok"]:
            score += 8.0
            reasons.append("نمره زبان در محدوده قابل قبول است")
        elif ielts >= thresholds["min"]:
            score += 3.0
        else:
            score -= 8.0
            reasons.append("توصیه: تقویت زبان قبل از اپلای جدی‌تر")
    elif not profile.has_language_cert:
        penalty = -6.0
        if ev_timeline_soon(profile) and country_code in ("canada", "germany", "spain", "italy"):
            penalty = -12.0
            reasons.append("بدون مدرک زبان و اپلای زیر یک سال، این مقصد پرریسک است")
        score += penalty

    return score, reasons


def _gpa_fit(profile: ApplicantProfile, country_code: str) -> tuple[float, list[str]]:
    reasons: list[str] = []
    if profile.gpa is None:
        return 0.0, reasons
    gpa = profile.gpa
    score = 0.0
    if gpa >= 17:
        score += 10.0
        if country_code == "canada":
            score += 6.0
            reasons.append("معدل قوی — رقابتی برای دانشگاه‌های برتر کانادا")
        else:
            reasons.append("معدل قوی برای پذیرش")
    elif gpa >= 15:
        score += 6.0
        reasons.append("معدل خوب برای بسیاری از برنامه‌ها")
    elif gpa >= 13:
        score += 3.0
        if country_code == "china":
            score += 4.0
            reasons.append("معدل متوسط — چین گزینه‌های متنوع‌تری دارد")
    else:
        score += 1.0
        if country_code in ("china", "spain"):
            score += 3.0
            reasons.append("با انتخاب دانشگاه مناسب، مسیر پذیرش همچنان ممکن است")
    return score, reasons


def _cluster_country_bonus(profile: ApplicantProfile, country_code: str) -> tuple[float, list[str]]:
    reasons: list[str] = []
    score = 0.0
    for cluster in profile.clusters:
        bonus = _CLUSTER_COUNTRY_AFFINITY.get(cluster, {}).get(country_code, 0)
        if bonus:
            score += bonus
    if score >= 6 and profile.clusters:
        reasons.append("هم‌خوانی حوزه تحصیلی شما با مقصدهای رایج این کشور")
    return score, reasons


def _catalog_data_bonus(catalog: CatalogSnapshot, code: str) -> float:
    """پاداش ملایم بر اساس پوشش داده — بدون سوگیری شدید به کشور پر‌داده."""
    unis = catalog.unis_by_country.get(code, [])
    majors = catalog.majors_for_country(code)
    if not unis and not majors:
        return -6.0
    n = max(len(catalog.country_codes), 1)
    avg_u = sum(len(catalog.unis_by_country.get(c, [])) for c in catalog.country_codes) / n
    avg_m = sum(len(catalog.majors_for_country(c)) for c in catalog.country_codes) / n
    u_ratio = len(unis) / max(avg_u, 1)
    m_ratio = len(majors) / max(avg_m, 1)
    return min(4.0, u_ratio * 1.4) + min(3.0, m_ratio * 1.1)


def _achievement_country_hints(catalog: CatalogSnapshot) -> dict[str, float]:
    """امتیاز غیرمستقیم از دستاوردهای موسسه به کشورها."""
    hints: dict[str, float] = {}
    for ach in catalog.achievements:
        blob = _normalize_persian(f"{ach.person_role} {ach.title} {ach.description}").lower()
        for code, label in _COUNTRY_LABELS.items():
            if code == "other":
                continue
            if code in blob or label in blob:
                hints[code] = hints.get(code, 0) + 2.0
    return hints


def _score_country(
    profile: ApplicantProfile,
    catalog: CatalogSnapshot,
    code: str,
    adaptive_weights=None,
    *,
    ach_hints: dict[str, float] | None = None,
    blog_hints: dict[str, float] | None = None,
) -> ScoredItem:
    reasons: list[str] = []
    if code not in catalog.country_codes:
        return ScoredItem(0.0, [])

    score = 40.0
    ev = profile.eval_req
    desired = profile.desired_countries

    if code in desired:
        idx = desired.index(code)
        score += 30.0 - idx * 2.0
        reasons.append("در لیست کشورهای مورد علاقه شما")

    if ev.target_country == code:
        if desired and code not in desired:
            score += 8.0
            reasons.append("کشور مقصد ثبت‌شده در فرم (خارج از اولویت‌های اصلی)")
        elif not desired:
            score += 18.0
            reasons.append("کشور مقصد اصلی در فرم")
        else:
            score += 12.0
            reasons.append("هم مقصد اصلی و هم در علاقه‌مندی‌های شما")

    if ev.has_financial_capacity:
        if code == "canada":
            score += 11.0
            reasons.append("تمکن مالی برای هزینه تحصیل در کانادا")
        elif code in ("spain", "germany", "italy"):
            score += 7.0
    else:
        if code == "china":
            score += 12.0
            reasons.append("هزینه و بورسیه مناسب‌تر در چین")
        if code == "spain":
            score += 8.0

    lang_s, lang_r = _language_fit(profile, code)
    score += lang_s
    reasons.extend(lang_r[:1])

    gpa_s, gpa_r = _gpa_fit(profile, code)
    score += gpa_s
    reasons.extend(gpa_r[:1])

    cl_s, cl_r = _cluster_country_bonus(profile, code)
    score += cl_s
    reasons.extend(cl_r[:1])

    path_s, path_r = _pathway_country_adjustment(profile, code)
    score += path_s
    reasons.extend(path_r[:1])

    if profile.is_graduate_track and profile.research_score >= 2 and code == "canada":
        score += 8.0
        reasons.append("سوابق پژوهشی برای ارشد/دکتری در کانادا مزیت است")

    if ev.has_international_tests and profile.is_graduate_track and code == "canada":
        score += 5.0

    if ev.apply_timeline == EvaluationRequest.APPLY_SOON and code in ("china", "spain"):
        score += 5.0

    if ach_hints is None:
        ach_hints = _achievement_country_hints(catalog)
    score += min(ach_hints.get(code, 0), 8.0)

    if blog_hints is None:
        blog_hints = blog_country_hints(
            catalog.blogs, profile, _COUNTRY_LABELS, catalog.country_codes
        )
    blog_boost = min(blog_hints.get(code, 0), 10.0)
    score += blog_boost
    if blog_boost >= 5.0:
        reasons.append("مطالب وبلاگ با مسیر تحصیلی شما در این کشور هم‌خوان است")

    if profile.scholarship_target:
        from .scholarship_catalog import SCHOLARSHIP_PROGRAMS

        prog_count = sum(1 for p in SCHOLARSHIP_PROGRAMS if p.country == code)
        if prog_count >= 2:
            score += min(9.0, prog_count * 2.5)
            reasons.append("فرصت‌های بورسیه و فاند شناخته‌شده در این کشور")
        elif prog_count == 1:
            score += 4.0

    score += _catalog_data_bonus(catalog, code)

    if adaptive_weights is not None:
        from .evaluation_learning import country_learning_boost

        learn_s, learn_r = country_learning_boost(adaptive_weights, profile, code)
        score += learn_s
        reasons.extend(learn_r[:1])

    if not reasons:
        reasons.append(_country_meta(code).get("intro", _COUNTRY_INTRO.get(code, "")))

    return ScoredItem(score, reasons[:4])


def _major_field_match(profile: ApplicantProfile, major: Major) -> tuple[float, list[str]]:
    reasons: list[str] = []
    texts = (major.title, major.short_description, major.description)
    field_match = _text_match_score(profile.field_text, *texts) if profile.field_text else 0.0
    desired_match = _text_match_score(profile.desired_text, *texts) if profile.desired_text else 0.0
    study_match = _text_match_score(profile.study_text, *texts)

    # رشته فعلی مهم‌تر از علاقه کلی
    combined = field_match * 0.45 + desired_match * 0.40 + study_match * 0.15
    score = combined * 70.0

    if major.slug in profile.resolved_desired_slugs:
        score += 30.0
        reasons.insert(0, f"تطابق دقیق با رشته هدف: «{profile.eval_req.desired_major}»")
    elif major.slug in profile.resolved_field_slugs:
        score += 22.0
        reasons.insert(0, f"تطابق دقیق با رشته تحصیلی: «{profile.eval_req.field_of_study}»")

    major_blob = _normalize_persian(f"{major.title} {major.short_description}").lower()
    rel = field_desired_relation(profile)
    if rel == "dental_to_medicine":
        if _is_dental_major(major):
            score += 12.0
            if not reasons:
                reasons.insert(0, f"هم‌راستا با رشته فعلی: «{profile.eval_req.field_of_study}»")
        elif field_match >= 0.5:
            score += 8.0
            reasons.insert(0, f"نزدیک به حوزه تحصیلی شما: «{profile.eval_req.field_of_study}»")
        elif profile.desired_text and profile.desired_text.lower() in major_blob:
            if _is_generic_medicine_major(major):
                score += 4.0
            else:
                score += 10.0
            reasons.append("علاقه شما به حوزه پزشکی/سلامت در امتیازدهی لحاظ شد")
    elif profile.desired_text and profile.desired_text.lower() in major_blob:
        score += 22.0
        reasons.insert(0, f"تطابق با رشته هدف: «{profile.eval_req.desired_major}»")
    elif field_match >= 0.62:
        reasons.insert(0, f"نزدیک به رشته تحصیلی شما: «{profile.eval_req.field_of_study or major.title}»")
    elif desired_match >= 0.55:
        reasons.append(f"مرتبط با علاقه شما: «{profile.eval_req.desired_major or major.title}»")

    for cluster in profile.clusters:
        keywords = next((kw for c, kw in _FIELD_CLUSTERS if c == cluster), frozenset())
        if any(k in major_blob for k in keywords):
            score += 10.0
            if not reasons:
                reasons.append("هم‌خوانی با حوزه تحصیلی شما")
            break

    score += max(0, 8 - major.order * 0.25)
    return score, reasons[:3]


def _score_major(
    profile: ApplicantProfile,
    major: Major,
    country_code: str,
    adaptive_weights=None,
) -> ScoredItem:
    if major.country and major.country != country_code:
        return ScoredItem(-1.0, [])

    score, reasons = _major_field_match(profile, major)
    path_s, path_r = _pathway_major_adjustment(profile, major, country_code)
    score += path_s
    reasons.extend(path_r[:1])
    dent_s, dent_r = _dental_to_medicine_major_adjustment(profile, major, country_code)
    score += dent_s
    reasons.extend(dent_r[:1])

    if score < 8:
        reasons.append("رشته فعال در کشور پیشنهادی")
        score += 6.0

    if adaptive_weights is not None:
        from .evaluation_learning import major_learning_boost

        learn_s, learn_r = major_learning_boost(adaptive_weights, profile, major.slug)
        score += learn_s
        reasons.extend(learn_r[:1])

    return ScoredItem(max(score, 0.0), reasons)


def _university_rank_fit(profile: ApplicantProfile, rank: float) -> float:
    """معدل بالا → دانشگاه رده بالاتر؛ معدل پایین → رده متوسط."""
    if profile.gpa is None:
        return max(0, 18.0 - rank / 25.0)
    if profile.gpa >= 17:
        return max(0, 28.0 - rank / 15.0)
    if profile.gpa >= 15:
        return max(0, 22.0 - rank / 20.0)
    return max(0, 16.0 - rank / 28.0)


def _score_university(
    profile: ApplicantProfile,
    uni: University,
    country_code: str,
    major: Major | None,
    adaptive_weights=None,
    catalog: CatalogSnapshot | None = None,
) -> ScoredItem:
    if uni.country != country_code:
        return ScoredItem(-1.0, [])

    reasons: list[str] = []
    score = 35.0

    rank = parse_world_rank(uni.world_rank or "")
    score += _university_rank_fit(profile, rank)
    if uni.world_rank:
        reasons.append(f"رتبه جهانی: {uni.world_rank}")

    if uni.is_approved_by_mo_science:
        score += 14.0
        reasons.append("مورد تأیید وزارت علوم")

    if major:
        coherence = _text_match_score(
            major.title,
            uni.short_description,
            uni.description,
            uni.name_fa,
            uni.name_en,
        )
        score += coherence * 22.0
        if coherence >= 0.45:
            reasons.append(f"برنامه‌ها با رشته «{major.title}» هم‌خوان است")
        elif coherence >= 0.28:
            reasons.append("احتمال برنامه‌های مرتبط در این دانشگاه")

    if major and catalog:
        linked = catalog.uni_slugs_for_major(major.slug, country_code)
        if linked:
            if uni.slug in linked:
                score += 22.0
                reasons.insert(0, f"این دانشگاه برنامه «{major.title}» را ارائه می‌دهد")
            else:
                score -= 6.0

    if profile.study_text:
        general = _text_match_score(profile.study_text, uni.name_fa, uni.name_en, uni.short_description)
        score += general * 8.0

    if adaptive_weights is not None:
        from .evaluation_learning import university_learning_boost

        learn_s, learn_r = university_learning_boost(
            adaptive_weights, profile, country_code, uni.slug
        )
        score += learn_s
        reasons.extend(learn_r[:1])

    return ScoredItem(score, reasons[:3])


def _compute_triple_score(
    country_item: ScoredItem,
    major_item: ScoredItem,
    uni_item: ScoredItem,
    profile: ApplicantProfile,
    rank: float,
) -> float:
    """امتیاز ترکیبی با وزن پویا."""
    major_w = 0.40
    uni_w = 0.36
    country_w = 0.24

    if profile.desired_text:
        major_w += 0.04
        country_w -= 0.02

    combined = (
        country_item.score * country_w
        + major_item.score * major_w
        + uni_item.score * uni_w
    )

    # پاداش انسجام: هر سه جزء امتیاز مثبت قوی
    if min(country_item.score, major_item.score, uni_item.score) > 25:
        combined += 6.0

    # جریمه اگر رشته ضعیف ولی دانشگاه قوی
    if major_item.score < 20 and rank < 80:
        combined -= 8.0

    return combined


def _compute_match_and_confidence(
    combined: float,
    profile: ApplicantProfile,
    has_university: bool,
    all_combined: list[float],
) -> tuple[int, str, str]:
    """درصد تطابق بر اساس رتبه نسبی در میان گزینه‌های بررسی‌شده."""
    if all_combined and len(all_combined) >= 2:
        sorted_vals = sorted(all_combined)
        rank = sum(1 for v in sorted_vals if v <= combined) / len(sorted_vals)
        spread = sorted_vals[-1] - sorted_vals[0]
        if spread > 8:
            pct = int(56 + rank * 38)
        else:
            pct = int(62 + rank * 30)
    elif all_combined:
        pct = 74
    else:
        pct = 72

    pct = min(94, max(56, pct))
    if profile.language_test == EvaluationRequest.TEST_NONE:
        pct = max(55, pct - 7)
    if profile.gpa_uncertain:
        pct = max(55, pct - 5)
    if profile.pathway_notes:
        pct = max(55, pct - 4)
    if has_university:
        pct = min(95, pct + 3)
    if profile.lang_ielts_equiv and profile.lang_ielts_equiv >= 6.5:
        pct = min(95, pct + 2)

    if pct >= 83 and has_university and (profile.lang_ielts_equiv or 0) >= 6.0:
        return pct, "high", "اطمینان بالا"
    if pct >= 68:
        return pct, "medium", "اطمینان متوسط"
    return pct, "low", "نیاز به بررسی کارشناس"


TripleCandidate = tuple[str, University | None, Major, float, list[str], ScoredItem, ScoredItem]


def _order_countries_for_search(
    country_scores: list[tuple[str, ScoredItem]],
    profile: ApplicantProfile,
) -> list[tuple[str, ScoredItem]]:
    desired = set(profile.desired_countries)
    preferred = [row for row in country_scores if row[0] in desired]
    rest = [row for row in country_scores if row[0] not in desired]
    return preferred + rest


def _pick_best_triple_candidate(
    candidates: list[TripleCandidate],
    profile: ApplicantProfile,
) -> TripleCandidate | None:
    if not candidates:
        return None

    ranked = sorted(candidates, key=lambda x: -x[3])
    best_score = ranked[0][3]
    threshold = best_score * 0.85

    pool = ranked
    if profile.desired_countries:
        desired_pool = [c for c in ranked if c[0] in profile.desired_countries and c[3] >= threshold]
        if desired_pool:
            pool = desired_pool

    if field_desired_relation(profile) == "dental_to_medicine":
        dental_pool = [
            c
            for c in pool
            if c[3] >= threshold and (_is_dental_major(c[2]) or _is_postgrad_health_major(c[2]))
        ]
        if dental_pool:
            dental_pool.sort(
                key=lambda c: (
                    0 if _is_dental_major(c[2]) else 1,
                    -c[3],
                )
            )
            return dental_pool[0]
        if profile.degree_level >= 3:
            non_generic = [
                c for c in pool if c[3] >= threshold and not _is_generic_medicine_major(c[2])
            ]
            if non_generic:
                return non_generic[0]

    if profile.wants_direct_medicine and profile.degree_level <= 1:
        for cand in pool:
            code, _, major, score, _, major_item, _ = cand
            if code == "china" and _is_direct_medicine_major(major) and score >= threshold:
                return cand
        for cand in pool:
            _, _, major, _, _, major_item, _ = cand
            if not _is_direct_medicine_major(major) and major_item.score >= 25:
                return cand

    return pool[0]


def _find_best_triple(
    profile: ApplicantProfile,
    catalog: CatalogSnapshot,
    country_scores: list[tuple[str, ScoredItem]],
    adaptive_weights=None,
) -> tuple[TripleCandidate | None, list[float]]:
    candidates: list[TripleCandidate] = []
    all_combined: list[float] = []

    for code, country_item in _order_countries_for_search(country_scores, profile)[:6]:
        majors = _prefilter_majors_for_scoring(
            profile, catalog.majors_for_country(code)
        )
        unis = _universities_for_triple_scoring(catalog.unis_by_country.get(code, []))

        if not majors:
            continue

        major_ranked = sorted(
            (
                (m, _score_major(profile, m, code, adaptive_weights))
                for m in majors
            ),
            key=lambda x: -x[1].score,
        )
        top_majors = [
            (m, mi)
            for m, mi in major_ranked[:_EVAL_MAX_MAJORS_TRIPLE]
            if mi.score > 5
        ]

        if not top_majors:
            continue

        if not unis:
            m, mi = top_majors[0]
            combined = country_item.score * 0.35 + mi.score * 0.65
            if len(all_combined) < _EVAL_MAX_COMBINED:
                all_combined.append(combined)
            reasons = country_item.reasons[:1] + mi.reasons[:2]
            candidates.append((code, None, m, combined, reasons, mi, ScoredItem(0.0, [])))
            continue

        for major, major_item in top_majors:
            linked_slugs = catalog.uni_slugs_for_major(major.slug, code)
            if linked_slugs:
                linked_unis = [u for u in unis if u.slug in linked_slugs]
                other_unis = [u for u in unis if u.slug not in linked_slugs]
                uni_pool = (
                    sorted(
                        linked_unis,
                        key=lambda u: parse_world_rank(u.world_rank or "") or 99999.0,
                    )
                    + sorted(
                        other_unis,
                        key=lambda u: parse_world_rank(u.world_rank or "") or 99999.0,
                    )
                )[:_EVAL_MAX_UNIS_TRIPLE]
            else:
                uni_pool = unis

            for uni in uni_pool:
                uni_item = _score_university(
                    profile, uni, code, major, adaptive_weights, catalog
                )
                if uni_item.score < 5:
                    continue
                rank = parse_world_rank(uni.world_rank or "")
                combined = _compute_triple_score(country_item, major_item, uni_item, profile, rank)
                if len(all_combined) < _EVAL_MAX_COMBINED:
                    all_combined.append(combined)
                reasons = (
                    country_item.reasons[:1]
                    + major_item.reasons[:1]
                    + uni_item.reasons[:1]
                )
                candidates.append(
                    (code, uni, major, combined, reasons, major_item, uni_item)
                )

    chosen = _pick_best_triple_candidate(candidates, profile)
    return chosen, all_combined


def _country_flag_url(code: str) -> str:
    iso = _COUNTRY_FLAG_ISO.get(code, code)
    try:
        from django.contrib.staticfiles.storage import staticfiles_storage

        return staticfiles_storage.url(f"img/flags/{iso}.svg")
    except Exception:
        return f"/static/img/flags/{iso}.svg"


def _serialize_country(code: str, item: ScoredItem) -> dict[str, Any]:
    meta = _country_meta(code)
    return {
        "code": code,
        "flag": _COUNTRY_FLAG_ISO.get(code, code),
        "flag_url": _country_flag_url(code),
        "name": meta["name"],
        "headline": meta["headline"] or meta["intro"],
        "hint": _country_card_hint(code, item.reasons),
        "score": round(item.score, 1),
        "reasons": item.reasons,
        "url": reverse("country_detail", kwargs={"country_code": code}),
    }


def _insights_need_blog_migration(insights: Any) -> bool:
    for line in insights or []:
        if not isinstance(line, str):
            return True
        text = line.strip()
        if text.startswith("مطلب «") or text.startswith("از مطلب «"):
            return True
    return False


def report_is_display_current(report: dict[str, Any] | None) -> bool:
    """آیا گزارش JSON ذخیره‌شده برای نمایش کافی است (بدون بازمحاسبه سنگین)."""
    if not report or not isinstance(report, dict):
        return False
    if not report.get("has_data"):
        return True
    if report.get("engine_version") != ENGINE_VERSION:
        return False
    if "blog_insight_items" not in report:
        return False
    if _insights_need_blog_migration(report.get("insights")):
        return False
    top = report.get("top_pick") or {}
    if not top.get("summary") or not (top.get("country") or {}).get("name"):
        return False
    return True


def enrich_stored_report(eval_req: EvaluationRequest, report: dict[str, Any]) -> dict[str, Any]:
    """متن‌های نمایشی را برای گزارش‌های ذخیره‌شده قدیمی به‌روز می‌کند."""
    if report_is_display_current(report):
        return report
    if not report.get("has_data"):
        return report
    fresh = build_evaluation_report(eval_req)
    if not fresh.get("has_data"):
        return report

    report = dict(report)
    report["coherence_note"] = fresh.get("coherence_note", report.get("coherence_note"))
    report["insights"] = _strip_legacy_blog_insight_lines(
        fresh.get("insights", report.get("insights") or [])
    )
    report["blog_insight_items"] = fresh.get(
        "blog_insight_items", report.get("blog_insight_items") or []
    )

    top = dict(report.get("top_pick") or {})
    fresh_top = fresh.get("top_pick") or {}
    for key in (
        "summary",
        "detail",
        "analysis",
        "blog_reading",
        "reasons",
        "match_percent",
        "confidence",
        "confidence_label",
    ):
        if key in fresh_top:
            top[key] = fresh_top[key]
    report["top_pick"] = top

    countries = []
    fresh_countries = fresh.get("countries") or []
    for i, country in enumerate(report.get("countries") or []):
        merged = dict(country)
        if i < len(fresh_countries):
            fc = fresh_countries[i]
            merged["hint"] = fc.get("hint", merged.get("hint"))
            merged["flag"] = fc.get("flag", merged.get("flag", merged.get("code")))
        countries.append(merged)
    report["countries"] = countries
    report["blogs"] = fresh.get("blogs", report.get("blogs"))
    report["language_pathway"] = fresh.get("language_pathway", report.get("language_pathway"))
    report["courses"] = fresh.get("courses", report.get("courses"))
    report["course_note"] = fresh.get("course_note", report.get("course_note"))
    report["majors"] = fresh.get("majors", report.get("majors"))
    report["universities"] = fresh.get("universities", report.get("universities"))
    report["scholarships"] = fresh.get("scholarships", report.get("scholarships"))
    report["scholarship_target"] = fresh.get("scholarship_target", report.get("scholarship_target"))
    report["pricing"] = fresh.get("pricing", report.get("pricing"))
    report["engine_version"] = fresh.get("engine_version", report.get("engine_version"))
    report["adaptive_learning"] = fresh.get("adaptive_learning", report.get("adaptive_learning"))
    return report


def _sync_language_pathway_display(
    report: dict[str, Any],
    eval_req: EvaluationRequest,
) -> dict[str, Any]:
    """مسیر زبان را با وضعیت فعلی پرونده همگام می‌کند (جایگاه و برجستگی)."""
    if not report.get("has_data"):
        return report
    profile = _build_applicant_profile(eval_req)
    code = ((report.get("top_pick") or {}).get("country") or {}).get("code", "")
    pathway = build_language_pathway(profile, country_code=code, limit=3)
    report = dict(report)
    report["language_pathway"] = pathway
    report["courses"] = pathway.get("courses", [])
    report["course_note"] = _build_course_note(pathway)
    return report


def get_evaluation_display_report(
    eval_req: EvaluationRequest | None,
    report: dict[str, Any],
    *,
    cache_token: str | None = None,
) -> dict[str, Any]:
    """
    گزارش آماده نمایش — از JSON ذخیره‌شده استفاده می‌کند؛
    فقط برای نسخه‌های قدیمی موتور، یک‌بار enrich (با کش) انجام می‌شود.
    """
    if report_is_display_current(report):
        report = _ensure_blog_reading(report)
    else:
        if cache_token:
            from django.core.cache import cache

            cache_key = f"eval_report_enriched:{cache_token}:v{ENGINE_VERSION}"
            cached = cache.get(cache_key)
            if isinstance(cached, dict):
                report = _ensure_blog_reading(cached)
                if eval_req is not None:
                    return _sync_language_pathway_display(report, eval_req)
                return report

        if eval_req is None:
            patched = dict(report)
            patched["insights"] = _strip_legacy_blog_insight_lines(
                patched.get("insights")
            )
            patched.setdefault("blog_insight_items", [])
            return _ensure_blog_reading(patched)

        enriched = enrich_stored_report(eval_req, report)
        if not isinstance(enriched, dict):
            enriched = dict(report) if isinstance(report, dict) else {}
        enriched = _ensure_blog_reading(enriched)
        if cache_token:
            from django.core.cache import cache

            cache.set(cache_key, enriched, timeout=86400)
        return _sync_language_pathway_display(enriched, eval_req)

    if eval_req is not None:
        report = _sync_language_pathway_display(report, eval_req)
    return report


def _serialize_major(major: Major, item: ScoredItem) -> dict[str, Any]:
    return {
        "id": major.pk,
        "title": major.title,
        "slug": major.slug,
        "short_description": (major.short_description or major.description or "")[:200],
        "image": major.get_image_url() if hasattr(major, "get_image_url") else "",
        "country": major.country,
        "country_name": _COUNTRY_LABELS.get(major.country, ""),
        "score": round(item.score, 1),
        "reasons": item.reasons,
        "url": reverse("major_details", kwargs={"slug": major.slug}),
    }


def _serialize_university(uni: University, item: ScoredItem) -> dict[str, Any]:
    image_url = ""
    if uni.image:
        try:
            image_url = uni.image.url
        except Exception:
            image_url = ""
    return {
        "id": uni.pk,
        "name_fa": uni.name_fa,
        "name_en": uni.name_en,
        "slug": uni.slug,
        "city": uni.city,
        "country": uni.country,
        "country_name": _COUNTRY_LABELS.get(uni.country, ""),
        "short_description": (uni.short_description or uni.description or "")[:280],
        "world_rank": uni.world_rank,
        "image_url": image_url,
        "score": round(item.score, 1),
        "reasons": item.reasons,
        "url": reverse("school_detail", kwargs={"slug": uni.slug}),
    }


def _alt_majors_for_country(
    catalog: CatalogSnapshot,
    profile: ApplicantProfile,
    code: str,
    exclude_ids: set[int],
    limit: int = 8,
    adaptive_weights=None,
) -> list[dict]:
    scored: list[tuple[float, dict]] = []
    for m in _prefilter_majors_for_scoring(profile, catalog.majors_for_country(code)):
        if m.pk in exclude_ids:
            continue
        item = _score_major(profile, m, code, adaptive_weights)
        if item.score > 8:
            scored.append((item.score, _serialize_major(m, item)))
    scored.sort(key=lambda x: -x[0])
    return [s[1] for s in scored[:limit]]


def _alt_universities_for_country(
    catalog: CatalogSnapshot,
    profile: ApplicantProfile,
    code: str,
    major: Major,
    exclude_ids: set[int],
    limit: int = 6,
    adaptive_weights=None,
) -> list[dict]:
    scored: list[tuple[float, dict]] = []
    for u in _universities_for_triple_scoring(catalog.unis_by_country.get(code, []), limit=24):
        if u.pk in exclude_ids:
            continue
        item = _score_university(profile, u, code, major, adaptive_weights, catalog)
        if item.score > 12:
            scored.append((item.score, _serialize_university(u, item)))
    scored.sort(key=lambda x: -x[0])
    return [s[1] for s in scored[:limit]]


def _score_blogs(
    catalog: CatalogSnapshot,
    profile: ApplicantProfile,
    country_code: str,
    *,
    scholarship_target: str = "",
    limit: int = 6,
) -> list[dict]:
    country_name = _COUNTRY_LABELS.get(country_code, "")
    return pick_scored_blogs(
        catalog.blogs,
        profile,
        country_code=country_code,
        country_name=country_name,
        scholarship_target=scholarship_target,
        limit=limit,
    )


def _faq_insights(profile: ApplicantProfile, catalog: CatalogSnapshot, country_code: str) -> list[str]:
    """نکات تکمیلی از FAQ مرتبط."""
    tokens = tokenize_query(profile.study_text)
    if not tokens:
        return []
    from .faq_search import _score_faq

    hits: list[tuple[float, FAQ]] = []
    for faq in catalog.faqs:
        s = _score_faq(faq, tokens, profile.study_text[:120])
        if s >= 8:
            hits.append((s, faq))
    hits.sort(key=lambda x: -x[0])
    out: list[str] = []
    for _, faq in hits[:2]:
        ans = _normalize_persian(faq.answer or "")
        if len(ans) > 120:
            ans = ans[:117] + "…"
        out.append(f"{faq.question} — {ans}")
    return out


def _next_degree_label(eval_req: EvaluationRequest) -> str:
    next_deg = _DEGREE_NEXT.get(eval_req.current_degree, "")
    if next_deg == eval_req.current_degree:
        return ""
    for val, label in EvaluationRequest.DEGREE_CHOICES:
        if val == next_deg:
            return label
    return ""


def _profile_insights(
    profile: ApplicantProfile,
    country_code: str,
    catalog: CatalogSnapshot,
    picker,
) -> list[str]:
    return collect_insights(
        profile,
        picker,
        _faq_insights(profile, catalog, country_code),
        next_degree_label=_next_degree_label(profile.eval_req),
    )


def _blog_insight_items(
    profile: ApplicantProfile,
    catalog: CatalogSnapshot,
    country_code: str,
    *,
    scholarship_target: str = "",
) -> list[dict[str, Any]]:
    country_name = _COUNTRY_LABELS.get(country_code, "")
    return blog_insights(
        catalog.blogs,
        profile,
        country_code=country_code,
        country_name=country_name,
        scholarship_target=scholarship_target,
        limit=3,
    )


def _strip_legacy_blog_insight_lines(insights: Any) -> list[str]:
    """حذف نکات قدیمی وبلاگ که به‌صورت متن بلند در insights ذخیره شده‌اند."""
    out: list[str] = []
    for line in insights or []:
        if not isinstance(line, str):
            continue
        text = line.strip()
        if text.startswith("مطلب «") or text.startswith("از مطلب «"):
            continue
        out.append(line)
    return out


def _strip_legacy_blog_analysis_lines(analysis: Any) -> list[str]:
    """حذف جملهٔ پیشنهاد مطالعهٔ وبلاگ وقتی به‌صورت لینک جداگانه نمایش داده می‌شود."""
    out: list[str] = []
    for line in analysis or []:
        if not isinstance(line, str):
            continue
        text = line.strip()
        if text.startswith("مطالعه پیشنهادی در وبلاگ:"):
            continue
        if text.startswith("برای جزئیات بیشتر، مقاله") and "» را ببینید" in text:
            continue
        out.append(line)
    return out


def _ensure_blog_reading(report: dict[str, Any]) -> dict[str, Any]:
    """لینک مقالهٔ پیشنهادی و حذف تکرار متن قدیمی در گزارش‌های ذخیره‌شده."""
    if not report.get("has_data"):
        return report
    report = dict(report)
    top = dict(report.get("top_pick") or {})
    analysis = list(top.get("analysis") or [])
    variant = "detail"
    for line in analysis:
        if isinstance(line, str) and line.strip().startswith("مطالعه پیشنهادی در وبلاگ:"):
            variant = "weblog"
            break
    top["analysis"] = _strip_legacy_blog_analysis_lines(analysis)

    blog_reading = top.get("blog_reading")
    if not blog_reading:
        blogs = report.get("blogs") or []
        if blogs:
            top_post = blogs[0]
            title = (top_post.get("title") or "").strip()
            url = (top_post.get("url") or "").strip()
            if title and url:
                blog_reading = {
                    "title": title,
                    "url": url,
                    "reason": (top_post.get("reasons") or ["نکات کاربردی"])[0],
                    "variant": variant,
                }
    if blog_reading:
        top["blog_reading"] = blog_reading
    report["top_pick"] = top
    return report


def _country_card_hint(code: str, reasons: list[str], picker=None) -> str:
    meta = _country_meta(code)
    intro = meta.get("headline") or meta.get("intro") or _COUNTRY_INTRO.get(code, "")
    if reasons:
        if picker and len(reasons) >= 2:
            lead = picker.choose(
                f"country_hint_{code}",
                [
                    f"{reasons[0]}؛ {reasons[1]}",
                    f"{reasons[0]} — {reasons[1]}",
                    f"به‌دلیل {reasons[0]} و {reasons[1]}",
                ],
            )
        else:
            lead = reasons[0]
        return f"{lead}. {intro}" if intro and intro not in lead else lead
    return intro


def _serialize_country_with_picker(code: str, item: ScoredItem, picker) -> dict[str, Any]:
    data = _serialize_country(code, item)
    data["hint"] = _country_card_hint(code, item.reasons, picker)
    return data


_BLOG_READING_HOOK = [
    " برای ادامه مسیر، مطلب «{title}» در وبلاگ ({reason}) را بخوانید.",
    " پیشنهاد مطالعه: «{title}» — {reason}.",
    " در وبلاگ، «{title}» با پرونده شما هم‌خوانی دارد ({reason}).",
]


def _append_blog_reading_hook(detail: str, blogs: list[dict], picker) -> str:
    if not blogs:
        return detail
    top = blogs[0]
    title = top.get("title") or ""
    reason = (top.get("reasons") or ["نکات کاربردی"])[0]
    hook = picker.choose("blog_hook", _BLOG_READING_HOOK).format(title=title, reason=reason)
    return detail + hook


def _blog_reading_hook(blogs: list[dict], picker) -> dict[str, Any] | None:
    """لینک مطالعهٔ پیشنهادی وبلاگ برای نمایش در بلوک تحلیل."""
    if not blogs:
        return None
    top = blogs[0]
    title = (top.get("title") or "").strip()
    url = (top.get("url") or "").strip()
    if not title or not url:
        return None
    reason = (top.get("reasons") or ["نکات کاربردی"])[0]
    variant = picker.choose("blog_hook_analysis", ["weblog", "detail"])
    return {"title": title, "url": url, "reason": reason, "variant": variant}


def _scholarship_insight(scholarship_target: str) -> str | None:
    if not scholarship_target:
        return None
    from .nav_degrees import get_degree_level

    level = get_degree_level(scholarship_target)
    if not level:
        return None
    return (
        f"تمرکز پرونده شما روی بورسیه و پذیرش {level.label} است؛ "
        "پیشنهادهای زیر با اولویت کشورها، دانشگاه‌ها و رشته‌هایی تنظیم شده‌اند "
        "که معمولاً فرصت بورسیه یا کمک‌هزینه بیشتری دارند."
    )


def _with_scholarship_insights(
    insights: list[str], scholarship_target: str
) -> list[str]:
    lead = _scholarship_insight(scholarship_target)
    if not lead:
        return insights
    return [lead, *insights]


def _with_learning_insights(insights: list[str], adaptive_weights) -> list[str]:
    from .evaluation_learning import learning_insight

    lead = learning_insight(adaptive_weights)
    if not lead or lead in insights:
        return insights
    return [lead, *insights]


def _uni_dict_for_scholarships(uni: University | None) -> dict[str, str] | None:
    if not uni:
        return None
    return {
        "name_fa": uni.name_fa or "",
        "name_en": getattr(uni, "name_en", "") or "",
        "slug": uni.slug or "",
        "city": getattr(uni, "city", "") or "",
    }


def _build_course_note(pathway: dict[str, Any]) -> str:
    courses = pathway.get("courses") or []
    prominence = pathway.get("prominence", "high")
    if prominence == "low":
        if not courses:
            return ""
        if pathway.get("tier") == "strong":
            return ""
        primary = next((c for c in courses if c.get("is_primary")), courses[0])
        title = primary.get("title") or "دوره زبان"
        return f"در صورت نیاز به تقویت، «{title}» پیشنهاد می‌شود — بخش تکمیلی پایین صفحه."
    if not courses:
        return (
            "چه الان و چه بعداً، تقویت زبان انگلیسی مهم‌ترین پیش‌نیاز پرونده شماست — "
            "مسیر پیشنهادی را در بخش زبان زیر همین بخش ببینید."
        )
    primary = next((c for c in courses if c.get("is_primary")), courses[0])
    title = primary.get("title") or "دوره زبان"
    note = pathway.get("pathway_note") or ""
    if note:
        return f"{note} پیشنهاد اصلی: «{title}» — جزئیات در بخش مسیر زبان زیر همین بخش."
    if len(courses) == 1:
        return (
            f"با توجه به وضعیت زبان پرونده، شرکت در دوره «{title}» "
            "می‌تواند قدم عملی بعدی شما باشد — جزئیات در بخش مسیر زبان زیر همین بخش."
        )
    t1 = courses[1].get("title") or ""
    return (
        f"پیشنهاد اصلی «{title}»"
        + (f" و تکمیلی «{t1}»" if t1 else "")
        + " — در بخش مسیر زبان زیر همین بخش."
    )


def _attach_pricing_to_report(
    report: dict[str, Any],
    profile: ApplicantProfile,
    country_code: str,
    *,
    scholarship_target: str = "",
) -> dict[str, Any]:
    from .evaluation_pricing import build_pricing_insights_for_report

    pricing = build_pricing_insights_for_report(
        profile, country_code, scholarship_target=scholarship_target
    )
    if pricing:
        report = dict(report)
        report["pricing"] = pricing
    return report


def build_evaluation_report(
    eval_req: EvaluationRequest,
    *,
    scholarship_target: str = "",
    progress_callback: Callable[[str, int, str], None] | None = None,
) -> dict[str, Any]:
    """گزارش پیشنهاد هوشمند منسجم."""
    from .evaluation_learning import (
        get_adaptive_weights,
        learning_insight,
        learning_report_meta,
    )

    def tick(step_id: str, percent: int, label: str, **extra: Any) -> None:
        if progress_callback:
            progress_callback(step_id, percent, label, **extra)

    tick("validate", 8, "بررسی و اعتبارسنجی اطلاعات فرم…")
    profile = _build_applicant_profile(eval_req)
    profile.scholarship_target = scholarship_target or ""
    tick("profile", 18, "ساخت پروفایل تحصیلی و زبانی…")
    catalog = _load_catalog()
    _enrich_profile_resolved_majors(profile, catalog)
    tick("countries", 28, "بارگذاری و مقایسه کشورها و دانشگاه‌ها…")
    picker = make_narrative_picker(eval_req)
    adaptive = get_adaptive_weights()
    learn_meta = learning_report_meta(adaptive)

    ach_hints = _achievement_country_hints(catalog)
    blog_hints = blog_country_hints(
        catalog.blogs, profile, _COUNTRY_LABELS, catalog.country_codes
    )
    country_scores: list[tuple[str, ScoredItem]] = []
    for code in catalog.country_codes:
        item = _score_country(
            profile,
            catalog,
            code,
            adaptive,
            ach_hints=ach_hints,
            blog_hints=blog_hints,
        )
        if item.score > 0:
            country_scores.append((code, item))
    country_scores.sort(key=lambda x: -x[1].score)

    if not country_scores:
        country_scores = [("canada", ScoredItem(48.0, ["پیشنهاد پیش‌فرض"]))]

    tick("countries", 38, "رتبه‌بندی کشورها، رشته‌ها و دانشگاه‌ها…")
    top_countries = [_serialize_country_with_picker(c, item, picker) for c, item in country_scores[:3]]
    country_codes_ordered = [c for c, _ in country_scores]
    from .scholarship_catalog import pick_scholarship_recommendations

    best, all_combined = _find_best_triple(profile, catalog, country_scores, adaptive)

    if best is None:
        tick("finalize", 100, "در حال ساخت خروجی…", ui_compact=True)
        return {
            "has_data": False,
            "engine_version": ENGINE_VERSION,
            "message": "در حال حاضر داده کافی برای پیشنهاد خودکار وجود ندارد؛ کارشناسان ما پس از تماس راهنمایی می‌کنند.",
        }

    code, top_uni, top_major, combined, reasons, major_item, uni_item = best
    country_item = next(ci for c, ci in country_scores if c == code)
    top_country = _serialize_country_with_picker(code, country_item, picker)
    match_pct, confidence, _ = _compute_match_and_confidence(
        combined, profile, top_uni is not None, all_combined
    )
    rel = field_desired_relation(profile)
    if rel == "dental_to_medicine":
        if _is_dental_major(top_major) or (
            _is_postgrad_health_major(top_major) and not _is_generic_medicine_major(top_major)
        ):
            match_pct = min(84, max(match_pct, 72))
            confidence = "medium" if profile.degree_level >= 3 else confidence
        elif _is_generic_medicine_major(top_major):
            match_pct = min(match_pct, 74)
            confidence = "low"
        else:
            match_pct = min(match_pct, 80)
            confidence = "medium" if confidence == "high" else confidence
    elif rel == "cross_field":
        match_pct = min(match_pct, 80)
        confidence = "medium" if confidence == "high" else confidence
    elif profile.degree_level >= 4 and _is_generic_medicine_major(top_major):
        match_pct = min(match_pct, 76)
        confidence = "low"
    conf_label = confidence_label(confidence, picker)

    if top_uni is None:
        top_major_ser = _serialize_major(top_major, major_item)
        tick("blogs", 68, "جستجو در وبلاگ و تجربیات موفق…")
        blogs = _score_blogs(
            catalog, profile, code, scholarship_target=scholarship_target
        )
        tick("pricing", 82, "برآورد هزینه از تعرفه خدمات…")
        tick("match", 94, "محاسبه درصد تطابق و سطح اطمینان…")
        summary_text = build_summary_partial(profile, top_country, top_major_ser, picker)
        analysis = build_analysis_points(
            profile, top_country, top_major_ser, picker, partial=True
        )
        blog_reading = _blog_reading_hook(blogs, picker)
        final_reasons = dedupe_reasons_against_narrative(
            reasons, summary=summary_text, analysis=analysis
        )
        tick("scholarships", 52, "بررسی بورسیه‌ها و فاندها…")
        language_pathway = build_language_pathway(profile, country_code=code, limit=3)
        courses = language_pathway.get("courses", [])
        scholarships = pick_scholarship_recommendations(
            profile,
            country_codes_ordered,
            scholarship_target=scholarship_target,
            limit=8,
            top_country_code=code,
            top_university=None,
        )
        tick("finalize", 96, "آماده‌سازی گزارش نهایی…")
        partial_report = {
            "has_data": True,
            "partial": True,
            "engine_version": ENGINE_VERSION,
            "applicant_name": eval_req.full_name,
            "top_pick": {
                "country": top_country,
                "university": None,
                "major": top_major_ser,
                "match_percent": match_pct,
                "confidence": confidence,
                "confidence_label": conf_label,
                "reasons": final_reasons,
                "summary": summary_text,
                "detail": "",
                "analysis": analysis,
                "blog_reading": blog_reading,
            },
            "countries": top_countries,
            "majors": _alt_majors_for_country(
                catalog, profile, code, {top_major.pk}, adaptive_weights=adaptive
            ),
            "universities": [],
            "blogs": blogs,
            "language_pathway": language_pathway,
            "courses": courses,
            "course_note": _build_course_note(language_pathway),
            "insights": _with_learning_insights(
                _with_scholarship_insights(
                    _profile_insights(profile, code, catalog, picker),
                    scholarship_target,
                ),
                adaptive,
            ),
            "blog_insight_items": _blog_insight_items(
                profile, catalog, code, scholarship_target=scholarship_target
            ),
            "coherence_note": build_coherence_note_partial(
                top_major.title, top_country["name"], picker
            ),
            "scholarship_target": scholarship_target or "",
            "scholarships": scholarships,
            "adaptive_learning": learn_meta,
        }
        return _attach_pricing_to_report(
            partial_report, profile, code, scholarship_target=scholarship_target
        )

    uni_ser = _serialize_university(top_uni, uni_item)
    major_ser = _serialize_major(top_major, major_item)
    tick("blogs", 68, "جستجو در وبلاگ و تجربیات موفق…")
    blogs = _score_blogs(
        catalog, profile, code, scholarship_target=scholarship_target
    )
    tick("pricing", 82, "برآورد هزینه از تعرفه خدمات…")
    tick("match", 94, "محاسبه درصد تطابق و سطح اطمینان…")
    summary_text = build_summary_full(profile, top_country, uni_ser, major_ser, picker)
    analysis = build_analysis_points(
        profile, top_country, major_ser, picker, partial=False, university=uni_ser
    )
    blog_reading = _blog_reading_hook(blogs, picker)
    final_reasons = dedupe_reasons_against_narrative(
        reasons, summary=summary_text, analysis=analysis
    )
    top_pick = {
        "country": top_country,
        "university": uni_ser,
        "major": major_ser,
        "match_percent": match_pct,
        "confidence": confidence,
        "confidence_label": conf_label,
        "reasons": final_reasons,
        "summary": summary_text,
        "detail": "",
        "analysis": analysis,
        "blog_reading": blog_reading,
    }

    tick("scholarships", 52, "بررسی بورسیه‌ها و فاندها…")
    language_pathway = build_language_pathway(profile, country_code=code, limit=3)
    courses = language_pathway.get("courses", [])
    scholarships = pick_scholarship_recommendations(
        profile,
        country_codes_ordered,
        scholarship_target=scholarship_target,
        limit=8,
        top_country_code=code,
        top_university=_uni_dict_for_scholarships(top_uni),
    )
    tick("finalize", 96, "آماده‌سازی گزارش نهایی…")
    full_report = {
        "has_data": True,
        "engine_version": ENGINE_VERSION,
        "applicant_name": eval_req.full_name,
        "top_pick": top_pick,
        "countries": top_countries,
        "majors": _alt_majors_for_country(
            catalog, profile, code, {top_major.pk}, adaptive_weights=adaptive
        ),
        "universities": _alt_universities_for_country(
            catalog, profile, code, top_major, {top_uni.pk}, adaptive_weights=adaptive
        ),
        "blogs": blogs,
        "language_pathway": language_pathway,
        "courses": courses,
        "course_note": _build_course_note(language_pathway),
        "insights": _with_learning_insights(
            _with_scholarship_insights(
                _profile_insights(profile, code, catalog, picker),
                scholarship_target,
            ),
            adaptive,
        ),
        "blog_insight_items": _blog_insight_items(
            profile, catalog, code, scholarship_target=scholarship_target
        ),
        "coherence_note": build_coherence_note_full(
            top_major.title, top_uni.name_fa, top_country["name"], picker
        ),
        "scholarship_target": scholarship_target or "",
        "scholarships": scholarships,
        "adaptive_learning": learn_meta,
    }
    return _attach_pricing_to_report(
        full_report, profile, code, scholarship_target=scholarship_target
    )
