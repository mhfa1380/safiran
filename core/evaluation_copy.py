"""
متن‌های توضیحی گزارش ارزیابی — واریانت‌های متنوع، پایدار برای هر کاربر، بدون تکرار در یک گزارش.
"""
from __future__ import annotations  # noqa: I001

import hashlib
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .evaluation_engine import ApplicantProfile, CatalogSnapshot
    from .models import EvaluationRequest


def applicant_display_name(full_name: str | None) -> str:
    """نام کامل متقاضی برای خطاب در گزارش — بدون برش به فقط نام کوچک."""
    cleaned = re.sub(r"\s+", " ", (full_name or "").strip())
    return cleaned or "دوست عزیز"


def narrative_seed(eval_req: EvaluationRequest) -> int:
    parts = [
        str(getattr(eval_req, "pk", "") or ""),
        eval_req.phone or "",
        eval_req.full_name or "",
        eval_req.field_of_study or "",
        str(eval_req.birth_year or ""),
        eval_req.email or "",
    ]
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
    return int(digest[:12], 16)


@dataclass
class NarrativePicker:
    """انتخاب قطعی متن بر اساس seed کاربر + جلوگیری از تکرار در یک گزارش."""

    seed: int
    _step: int = 0
    _used: set[str] = field(default_factory=set)

    def choose(self, category: str, options: list[str]) -> str:
        if not options:
            return ""
        pool = [o for o in options if o not in self._used]
        if not pool:
            pool = list(options)
        idx = (self.seed + self._step * 997 + sum(ord(c) for c in category)) % len(pool)
        self._step += 1
        choice = pool[idx]
        self._used.add(choice)
        return choice

    def choose_optional(self, category: str, options: list[str], *, enabled: bool) -> str:
        return self.choose(category, options) if enabled else ""


def make_narrative_picker(eval_req: EvaluationRequest) -> NarrativePicker:
    return NarrativePicker(seed=narrative_seed(eval_req))


def _dedupe_lines(lines: list[str], limit: int = 6) -> list[str]:
    out: list[str] = []
    seen_norm: set[str] = set()
    for line in lines:
        line = line.strip()
        if not line:
            continue
        norm = re.sub(r"\s+", " ", line)[:80].lower()
        if norm in seen_norm:
            continue
        seen_norm.add(norm)
        out.append(line)
        if len(out) >= limit:
            break
    return out


def _token_overlap(a: str, b: str) -> bool:
    if not a or not b:
        return False
    ta = {t for t in re.split(r"\s+", a) if len(t) >= 3}
    tb = {t for t in re.split(r"\s+", b) if len(t) >= 3}
    if not ta or not tb:
        return a[:20] in b or b[:20] in a
    return bool(ta & tb)


_DENTAL_KEYWORDS = frozenset(
    {"دندان", "dentistry", "dental", "ارتودنسی", "پروتز", "دندانپزشکی"}
)
_MED_DESIRED_KEYWORDS = frozenset({"پزشکی", "medicine", "mbbs", "md", "پزشک", "علوم پزشکی"})


def field_desired_relation(profile: ApplicantProfile) -> str:
    """رابطه رشته فعلی و رشته هدف در فرم."""
    field = (profile.field_text or "").lower()
    desired = (profile.desired_text or "").lower()
    if not desired:
        return "no_desired"
    if not field:
        return "unknown_field"

    field_dental = any(k in field for k in _DENTAL_KEYWORDS)
    desired_med = any(k in desired for k in _MED_DESIRED_KEYWORDS)

    if field == desired:
        return "aligned"

    # «پزشکی» داخل «دندانپزشکی» هم‌راستایی واقعی نیست
    if field_dental and desired_med:
        return "dental_to_medicine"

    if desired in field or field in desired:
        return "aligned"

    if field_dental or any(k in field for k in _MED_DESIRED_KEYWORDS):
        if desired_med or field_dental:
            return "medical_family_cross"
    return "cross_field"


_ANALYSIS_DENTAL_TO_MEDICINE = [
    "رشته فعلی شما در حوزه دندانپزشکی است و «{desired}» هدف جداگانه‌ای است؛ ورود مجدد به پزشکی عمومی (مثل MBBS) معمولاً با مقطع فعلی شما متفاوت است و بیشتر مسیر تخصص، فلوشیپ یا برنامه‌های مرتبط بررسی می‌شود.",
    "دکتری/کارشناسی دندانپزشکی با پزشکی عمومی یک مسیر نیست؛ پیشنهاد «{major}» در {country} نقطه شروع بررسی است و برنامه دقیق در مشاوره تعیین می‌شود.",
]

_ANALYSIS_CROSS_FIELD = [
    "رشته فعلی («{field}») با علاقه‌مندی «{desired}» متفاوت است؛ پیشنهاد زیر بر اساس اولویت فرم شماست و در تماس، مسیر واقع‌بینانه (تغییر رشته، مقطع یا کشور) مشخص می‌شود.",
]

_ANALYSIS_ALIGNED = [
    "سوابق تحصیلی و رشته هدف شما در یک خط هستند؛ تمرکز بعدی روی زبان، معدل و انتخاب دانشگاه دقیق است.",
]

_ANALYSIS_PHD_PATHWAY = [
    "با مقطع {degree} فعلی، معمولاً پذیرش در مقطع پایین‌تر (مثل لیسانس عمومی پزشکی) پیشنهاد نمی‌شود؛ گزینه‌های تخصص، پژوهش یا برنامه‌های مرتبط با سابقه شما بررسی می‌شود.",
]

_ANALYSIS_PARTIAL_COUNTRY = [
    "فهرست دانشگاه‌های {country} در سایت در حال تکمیل است؛ در تماس، لیست هدف با بودجه و زمان‌بندی شما شخصی‌سازی می‌شود.",
]


# --- واریانت‌ها ---

_SUMMARY_PARTIAL = [
    "{name} عزیز، با توجه به {degree} در «{field}»، مسیر اولیه ما برای شروع بررسی پرونده، «{major}» در {country} است.",
    "{name} گرامی، بر اساس اطلاعاتی که ثبت کردید، «{major}» در {country} بیشترین هم‌خوانی را با شرایط شما دارد.",
]

_SUMMARY_PARTIAL_CROSS = [
    "{name} عزیز، با {degree} در «{field}» و علاقه‌مندی به «{desired}»، «{major}» در {country} به‌عنوان مسیر اولیه بررسی پرونده پیشنهاد شده است.",
    "{name} گرامی، رشته فعلی و هدف شما متفاوت است؛ بر همین اساس «{major}» در {country} برای گام بعدی ارزیابی انتخاب شده است.",
]

_SUMMARY_DENTAL_PATHWAY = [
    "{name} عزیز، با {degree} در «{field}» و علاقه به «{desired}»، ادامه در «{major}» در {country} از نظر سوابق شما منطقی‌تر از ورود مجدد به پزشکی عمومی (MBBS) است.",
    "{name} گرامی، با توجه به دندانپزشکی و هدف حوزه پزشکی، «{major}» در {country} به‌عنوان مسیر اولیه (تخصص/ادامه حوزه دندان یا سلامت) پیشنهاد شده است.",
]

_SUMMARY_FULL = [
    "{name} عزیز، با {degree} و رشته «{field}»{gpa_part}، مسیر پیشنهادی: «{major}» در {uni} ({city}، {country}).",
    "{name} گرامی، ترکیب «{major}» — {uni}، {city} ({country}) با {degree} شما در ارزیابی اولیه در صدر قرار گرفت{gpa_part}.",
    "برای {name} عزیز با {degree} در «{field}»{gpa_part}، {uni} در {city} ({country}) برای رشته «{major}» منطقی‌ترین گزینه آغازین است.",
]

_SUMMARY_GPA_TAIL = [
    " معدل حدود {gpa:.1f} در این ارزیابی لحاظ شده است.",
    " (معدل تقریبی {gpa:.1f})",
    " — معدل شما حدود {gpa:.1f} ثبت شده.",
]

_SUMMARY_CLOSING_PARTIAL = [
    " کارشناسان برای دانشگاه دقیق و زمان‌بندی اپلای با شما تماس می‌گیرند.",
    " گام بعدی: هماهنگی تماس برای جزئیات پذیرش و مدارک.",
    " تیم ما پس از بررسی دستی، مسیر دقیق‌تر را در تماس پیشنهاد می‌دهد.",
]

_SUMMARY_LANG_NONE = [
    " قدم فوری: برنامه‌ریزی آزمون زبان.",
    " اولویت کوتاه‌مدت: آمادگی IELTS یا معادل.",
    " پیش از اپلای جدی، برنامه آزمون زبان را شروع کنید.",
]

_SUMMARY_FINANCIAL = [
    " تمکن مالی ثبت‌شده، محدوده انتخاب را گسترده‌تر می‌کند.",
    " با بودجه اعلام‌شده، مقاصد پرهزینه‌تر هم قابل بررسی است.",
    " از نظر مالی، گزینه‌های بیشتری در دسترس دارید.",
]

_DETAIL_INTRO_PARTIAL = [
    "با {degree} و رشته «{field}»، «{major}» در {country} با اولویت‌های فرم شما هم‌خوان ارزیابی شد.",
    "ارزیابی اولیه نشان می‌دهد «{major}» در {country} با مسیر تحصیلی فعلی شما ({degree}، «{field}») سازگار است.",
    "بر پایه اطلاعات فرم، {country} و رشته «{major}» نقطه شروع منطقی برای {degree} شماست.",
]

_DETAIL_INTRO_FULL = [
    "ترکیب «{major}» در {uni} ({city}، {country}) با {degree} و «{field}» شما در مدل ما بالاترین انسجام را داشت.",
    "{uni} در {city} برای رشته «{major}» — با توجه به {degree} و «{field}» — گزینه اول پیشنهاد شده است.",
    "پیشنهاد اولیه: {major} در {uni} ({country})؛ این انتخاب با سوابق تحصیلی شما ({degree}، «{field}») منطبق است.",
]

_DETAIL_DESIRED_MAJOR = [
    "علاقه شما به «{desired}» در این پیشنهاد در نظر گرفته شده است.",
    "رشته هدف «{desired}» هم‌راستا با مسیر پیشنهادی است.",
    "تمرکز شما روی «{desired}» در امتیازدهی رشته اثرگذار بود.",
]

_DETAIL_NO_UNI = [
    "فهرست دانشگاه‌های این کشور در سایت تکمیل می‌شود؛ در تماس، گزینه‌های دقیق با بودجه و زمان‌بندی شما هماهنگ می‌شود.",
    "دانشگاه‌های این مقصد به‌زودی در سایت اضافه می‌شوند — کارشناسان در مشاوره، لیست هدف را شخصی‌سازی می‌کنند.",
    "انتخاب نهایی دانشگاه پس از تماس تلفنی، با توجه به معدل، زبان و بودجه شما انجام می‌شود.",
]

_DETAIL_CLOSING_FULL = [
    "این پیشنهاد نقطه شروع است؛ برای بورسیه، ویزا و ددلاین‌ها با کارشناسان هماهنگ کنید.",
    "گزارش خودکار است — انتخاب نهایی دانشگاه و استراتژی اپلای در جلسه مشاوره تکمیل می‌شود.",
    "برای برنامه دقیق پذیرش و مدارک، یک جلسه مشاوره تخصصی توصیه می‌شود.",
]

_GPA_PHRASES_HIGH = [
    "معدل {gpa:.1f} برای رقابت در دانشگاه‌های معتبر نقطه قوت است.",
    "با معدل {gpa:.1f}، پروفایل شما در رده رقابتی قرار می‌گیرد.",
    "معدل {gpa:.1f} شانس پذیرش در برنامه‌های سطح بالا را تقویت می‌کند.",
]

_GPA_PHRASES_MID = [
    "معدل حدود {gpa:.1f} برای بسیاری از برنامه‌ها قابل اتکاست.",
    "با معدل {gpa:.1f}، طیف مناسبی از دانشگاه‌ها در دسترس است.",
    "معدل {gpa:.1f} در محدوده قابل قبول بسیاری از مقاصد است.",
]

_GPA_PHRASES_LOW = [
    "با معدل حدود {gpa:.1f} و انتخاب استراتژیک دانشگاه، مسیر پذیرش باز می‌ماند.",
    "معدل {gpa:.1f} مانع قطعی نیست — کشور و دانشگاه هدف تعیین‌کننده است.",
    "حتی با معدل {gpa:.1f}، با برنامه‌ریزی درست می‌توان پذیرش گرفت.",
]

_LANG_NONE = [
    "هنوز مدرک زبان ثبت نشده — پیشنهاد می‌کنیم برای IELTS یا معادل برنامه بچینید.",
    "بدون مدرک زبان، اولویت کوتاه‌مدت شما آمادگی آزمون معتبر است.",
    "قدم بعدی: ثبت‌نام آزمون زبان قبل از جمع‌آوری مدارک اپلای.",
]

_LANG_STRONG = [
    "نمره زبان شما برای بسیاری از برنامه‌ها قابل اتکاست.",
    "زبان از نقاط قوت پرونده شماست — در انگیزه‌نامه به آن اشاره کنید.",
    "سطح زبان فعلی، دامنه دانشگاه‌های هدف را گسترش می‌دهد.",
]

_LANG_WEAK = [
    "تقویت نمره زبان، مستقیماً گزینه‌های پذیرش را بیشتر می‌کند.",
    "با دوره تقویتی یا آزمون مجدد، شانس پذیرش بهبود می‌یابد.",
    "سرمایه‌گذاری روی زبان، بازده سریعی در پرونده مهاجرت تحصیلی دارد.",
]

_COHERENCE_PARTIAL = [
    "«{major}» در {country} با اولویت‌های فرم شما هم‌خوان است؛ جزئیات دانشگاه در تماس تکمیل می‌شود.",
    "مسیر «{major}» — {country} انسجام خوبی با پروفایل شما دارد؛ گام بعدی: مشاوره تخصصی.",
    "پیشنهاد اولیه ({major}، {country}) بر اساس داده‌های زنده سایت و اطلاعات فرم شماست.",
]

_COHERENCE_FULL = [
    "{country}، {uni} و «{major}» با هم منطبق ارزیابی شدند — نقطه شروع مشاوره تخصصی.",
    "کشور، دانشگاه و رشته در یک خط قرار گرفتند؛ این ترکیب پایه برنامه اپلای شماست.",
    "انسجام سه‌گانه ({major} در {uni}، {country}) در مدل ما بالاترین امتیاز را گرفت.",
]

_INSIGHT_GPA_HIGH = [
    "معدل شما برای رقابت در دانشگاه‌های رده بالا مناسب است؛ در مشاوره، لیست هدف دقیق‌تر می‌شود.",
    "از نظر معدل، می‌توانید دانشگاه‌های معتبرتری را در نظر بگیرید.",
    "معدل قوی‌تان اجازه می‌دهد روی بورسیه و برنامه‌های رقابتی‌تر فکر کنید.",
]

_INSIGHT_GPA_LOW = [
    "معدل پایین‌تر مانع قطعی نیست — انتخاب درست کشور و دانشگاه تعیین‌کننده است.",
    "با استراتژی مناسب، حتی معدل متوسط هم به پذیرش واقعی منجر می‌شود.",
    "تمرکز روی دانشگاه‌هایی با آستانه پذیرش متناسب، شانس شما را بالا می‌برد.",
]

_INSIGHT_LANG_NONE = [
    "مدرک زبان هنوز ثبت نشده؛ هرچه زودتر برای IELTS یا معادل برنامه بچینید.",
    "بدون زبان معتبر، دایره دانشگاه‌های قابل اپلای محدود می‌ماند.",
    "آمادگی زبان را هم‌زمان با جمع‌آوری مدارک شروع کنید تا عقب نمانید.",
]

_INSIGHT_LANG_WEAK = [
    "نمره زبان فعلی را با تقویت یا آزمون مجدد ارتقا دهید — اثر مستقیم روی پذیرش دارد.",
    "یک نمره زبان بهتر، گاهی مهم‌تر از تغییر کشور مقصد است.",
    "دوره فشرده زبان می‌تواند در چند ماه گزینه‌های شما را دو برابر کند.",
]

_INSIGHT_LANG_STRONG = [
    "نمره زبان از نقاط قوت پرونده است — در رزومه و انگیزه‌نامه برجسته‌اش کنید.",
    "سطح زبان شما درب‌های بیشتری به برنامه‌های انگلیسی‌زبان باز می‌کند.",
    "زبان را در استراتژی اپلای به‌عنوان مزیت رقابتی بنویسید.",
]

_INSIGHT_RESEARCH = [
    "سوابق پژوهشی برای ارشد/دکتری ارزشمند است — در رزومه و انگیزه‌نامه شفاف توضیح دهید.",
    "مقالات و فعالیت پژوهشی شما را در مدارک اپلای برجسته کنید.",
    "پژوهش‌تان می‌تواند جبران‌کننده نقاط ضعف دیگر پرونده باشد.",
]

_INSIGHT_GRE = [
    "GRE/GMAT برای برخی برنامه‌های ارشد و دکتری همچنان مزیت جدی است.",
    "اگر برنامه هدف GRE می‌خواهد، زمان‌بندی آزمون را جلو بیندازید.",
    "نمره آزمون بین‌المللی می‌تواند رزومه شما را از رقبا جدا کند.",
]

_INSIGHT_NEXT_DEGREE = [
    "گام منطقی بعدی در مسیر تحصیلی: {label}.",
    "بر اساس مدرک فعلی، مقطع بعدی پیشنهادی: {label}.",
    "مسیر تحصیلی شما به‌سمت {label} ادامه پیدا می‌کند.",
]

_INSIGHT_SERVICE_FULL = [
    "سپردن کامل فرآیند به موسسه، ریسک جا ماندن ددلاین را کم می‌کند.",
    "هماهنگی یکپارچه اپلای، ویزا و مدارک با تیم موسسه توصیه می‌شود.",
    "پشتیبانی کامل موسسه برای پرونده‌های چندمرحله‌ای مفید است.",
]

_INSIGHT_TIMELINE_SOON = [
    "با افق اپلای زیر یک سال، زمان‌بندی فشرده اما قابل اجراست — سریع اقدام کنید.",
    "ددلاین نزدیک است؛ اولویت با زبان و مدارک اصلی است.",
    "برای اپلای زیر یک سال، همین هفته برنامه زبان و مدارک را شروع کنید.",
]

_INSIGHT_FINANCIAL = [
    "تمکن مالی اعلام‌شده، مقاصد پرهزینه‌تر را هم در محدوده بررسی قرار می‌دهد.",
    "بودجه شما اجازه می‌دهد کشورهای با هزینه بالاتر را هم مقایسه کنید.",
    "از نظر مالی، محدودیت شدیدی در انتخاب اولیه دیده نمی‌شود.",
]

_INSIGHT_MARITAL_MARRIED = [
    "با وضعیت تأهل، از همان ابتدا شرایط همراهی و ویزای همراهان را در برنامه اپلای لحاظ کنید تا در میانه مسیر دچار تأخیر نشوید.",
    "اگر قصد مهاجرت همراه خانواده را دارید، زمان‌بندی مدارک و تمکن مالی را برای همه اعضا یکجا ببینید.",
]

_INSIGHT_MARITAL_SINGLE = [
    "با وضعیت مجردی، در انتخاب مقصد و زمان‌بندی انعطاف بیشتری دارید؛ از این مزیت برای اولویت‌بندی کشورها استفاده کنید.",
]

_INSIGHT_CONFERENCE = [
    "مقاله کنفرانسی شما نقطه قوت پرونده است؛ در رزومه و انگیزه‌نامه حتماً به آن اشاره کنید.",
    "سوابق کنفرانسی برای ارشد و دکتری ارزشمند است — در تماس با کارشناس، نحوه ارائه آن را دقیق می‌چینیم.",
]

_INSIGHT_BOOK = [
    "چاپ یا ترجمه کتاب در رزومه شما متمایز است؛ در بخش دستاوردها و انگیزه‌نامه شفاف توضیح دهید.",
    "کتاب منتشرشده می‌تواند در مصاحبه و پذیرش تحصیلی به‌عنوان مزیت جدی مطرح شود.",
]

_INSIGHT_DEFAULT = [
    "پروفایل شما برای بررسی تخصصی آماده است؛ مسیر دقیق در تماس هماهنگ می‌شود.",
    "این گزارش نقطه شروع است — کارشناسان جزئیات را با شما تکمیل می‌کنند.",
    "اطلاعات فرم کافی است؛ گام بعدی: جلسه مشاوره برای برنامه شخصی.",
]

_CONFIDENCE_LABELS = {
    "high": ["اطمینان بالا", "تطابق قوی", "پیشنهاد قابل اتکا"],
    "medium": ["اطمینان متوسط", "تطابق خوب", "نیاز به تأیید کارشناس"],
    "low": ["نیاز به بررسی کارشناس", "پیشنهاد اولیه", "تطابق محتاطانه"],
}


def gpa_phrase(profile: ApplicantProfile, picker: NarrativePicker) -> str:
    if not profile.gpa:
        return ""
    gpa = profile.gpa
    if gpa >= 17:
        pool = _GPA_PHRASES_HIGH
    elif gpa >= 15:
        pool = _GPA_PHRASES_MID
    else:
        pool = _GPA_PHRASES_LOW
    return picker.choose("gpa", [t.format(gpa=gpa) for t in pool])


def language_phrase(profile: ApplicantProfile, picker: NarrativePicker) -> str:
    from .models import EvaluationRequest

    if profile.language_test == EvaluationRequest.TEST_NONE:
        return picker.choose("lang_none", _LANG_NONE)
    if profile.lang_ielts_equiv and profile.lang_ielts_equiv >= 6.5:
        return picker.choose("lang_strong", _LANG_STRONG)
    if profile.lang_ielts_equiv and profile.lang_ielts_equiv < 6.0:
        return picker.choose("lang_weak", _LANG_WEAK)
    return ""


def build_summary_partial(
    profile: ApplicantProfile,
    country: dict[str, Any],
    major: dict[str, Any],
    picker: NarrativePicker,
) -> str:
    ev = profile.eval_req
    name = applicant_display_name(ev.full_name)
    rel = field_desired_relation(profile)
    ctx = {
        "name": name,
        "degree": ev.get_current_degree_display(),
        "field": ev.field_of_study,
        "desired": ev.desired_major or "",
        "major": major["title"],
        "country": country["name"],
    }
    major_title_l = (major.get("title") or "").lower()
    if rel == "dental_to_medicine" and any(k in major_title_l for k in _DENTAL_KEYWORDS):
        parts = [picker.choose("summary_dental_path", _SUMMARY_DENTAL_PATHWAY).format(**ctx)]
    elif rel in ("cross_field", "dental_to_medicine", "medical_family_cross"):
        parts = [picker.choose("summary_partial_cross", _SUMMARY_PARTIAL_CROSS).format(**ctx)]
    else:
        parts = [picker.choose("summary_partial", _SUMMARY_PARTIAL).format(**ctx)]
    if profile.gpa:
        parts.append(picker.choose("summary_gpa", _SUMMARY_GPA_TAIL).format(gpa=profile.gpa))
    parts.append(picker.choose("summary_close_partial", _SUMMARY_CLOSING_PARTIAL))
    return "".join(parts)


def build_summary_full(
    profile: ApplicantProfile,
    country: dict[str, Any],
    university: dict[str, Any],
    major: dict[str, Any],
    picker: NarrativePicker,
) -> str:
    from .models import EvaluationRequest

    ev = profile.eval_req
    name = applicant_display_name(ev.full_name)
    gpa_part = (
        picker.choose("summary_gpa", _SUMMARY_GPA_TAIL).format(gpa=profile.gpa)
        if profile.gpa
        else ""
    )
    ctx = {
        "name": name,
        "degree": ev.get_current_degree_display(),
        "field": ev.field_of_study,
        "gpa_part": gpa_part,
        "major": major["title"],
        "uni": university["name_fa"],
        "city": university["city"],
        "country": country["name"],
    }
    text = picker.choose("summary_full", _SUMMARY_FULL).format(**ctx)
    if profile.language_test == EvaluationRequest.TEST_NONE:
        text += picker.choose("summary_lang", _SUMMARY_LANG_NONE)
    elif ev.has_financial_capacity:
        text += picker.choose("summary_fin", _SUMMARY_FINANCIAL)
    return text


def build_analysis_points(
    profile: ApplicantProfile,
    country: dict[str, Any],
    major: dict[str, Any],
    picker: NarrativePicker,
    *,
    partial: bool = False,
    university: dict[str, Any] | None = None,
) -> list[str]:
    """نکات تحلیلی بدون تکرار خلاصه — برای لیست در صفحه نتیجه."""
    ev = profile.eval_req
    rel = field_desired_relation(profile)
    lines: list[str] = []

    if rel == "dental_to_medicine":
        major_title_l = (major.get("title") or "").lower()
        if any(k in major_title_l for k in _DENTAL_KEYWORDS):
            lines.append(
                picker.choose(
                    "analysis_dental_pick",
                    [
                        "پیشنهاد «{major}» بر اساس سوابق دندانپزشکی شماست؛ برای ورود به پزشکی عمومی معمولاً مسیر جداگانه‌ای (مثل MBBS) بررسی می‌شود.",
                        "ادامه در حوزه دندان/سلامت در {country} با مقطع فعلی شما سازگارتر ارزیابی شد.",
                    ],
                ).format(major=major["title"], country=country["name"])
            )
        else:
            lines.append(
                picker.choose("analysis_dental_med", _ANALYSIS_DENTAL_TO_MEDICINE).format(
                    desired=ev.desired_major or "پزشکی",
                    major=major["title"],
                    country=country["name"],
                )
            )
    elif rel in ("cross_field", "medical_family_cross"):
        lines.append(
            picker.choose("analysis_cross", _ANALYSIS_CROSS_FIELD).format(
                field=ev.field_of_study,
                desired=ev.desired_major or major["title"],
            )
        )
    elif rel == "aligned":
        lines.append(picker.choose("analysis_aligned", _ANALYSIS_ALIGNED))

    if profile.degree_level >= 4 and any(
        k in (major.get("title") or "").lower() for k in _MED_DESIRED_KEYWORDS
    ):
        lines.append(
            picker.choose("analysis_phd", _ANALYSIS_PHD_PATHWAY).format(
                degree=ev.get_current_degree_display()
            )
        )

    for note in profile.pathway_notes[:1]:
        if note:
            lines.append(note)

    gpa = gpa_phrase(profile, picker)
    if gpa:
        lines.append(gpa)
    lang = language_phrase(profile, picker)
    if lang:
        lines.append(lang)

    if partial and not university:
        lines.append(
            picker.choose("analysis_partial_country", _ANALYSIS_PARTIAL_COUNTRY).format(
                country=country["name"]
            )
        )
    elif university:
        lines.append(
            picker.choose(
                "detail_close_full",
                [
                    "گام بعدی: جلسه مشاوره برای ددلاین، بورسیه و لیست نهایی دانشگاه‌ها.",
                    "برای ویزا و استراتژی اپلای، هماهنگی با کارشناس توصیه می‌شود.",
                ],
            )
        )

    return _dedupe_lines(lines, limit=5)


def build_detail_partial(
    profile: ApplicantProfile,
    country: dict[str, Any],
    major: dict[str, Any],
    picker: NarrativePicker,
) -> str:
    """سازگاری با گزارش‌های قدیمی — متن تحلیل یک‌خطی."""
    points = build_analysis_points(profile, country, major, picker, partial=True)
    return " ".join(points)


def build_detail_full(
    profile: ApplicantProfile,
    country: dict[str, Any],
    university: dict[str, Any],
    major: dict[str, Any],
    picker: NarrativePicker,
) -> str:
    points = build_analysis_points(
        profile, country, major, picker, partial=False, university=university
    )
    if profile.eval_req.has_financial_capacity:
        points.append(picker.choose("summary_fin", _SUMMARY_FINANCIAL))
    return " ".join(_dedupe_lines(points, limit=5))


def build_coherence_note_partial(
    major_title: str,
    country_name: str,
    picker: NarrativePicker,
) -> str:
    return picker.choose(
        "coherence_partial",
        [
            "این پیشنهاد نقطه شروع مشاوره است؛ جزئیات دانشگاه و زمان‌بندی در تماس نهایی می‌شود.",
            "برای برنامه دقیق اپلای در {country}، کارشناسان مسیر را با شما هماهنگ می‌کنند.",
        ],
    ).format(major=major_title, country=country_name)


def dedupe_reasons_against_narrative(
    reasons: list[str],
    *,
    summary: str = "",
    analysis: list[str] | None = None,
    limit: int = 4,
) -> list[str]:
    """حذف دلایلی که تکرار خلاصه یا تحلیل هستند."""
    blob = " ".join([summary, *(analysis or [])]).lower()
    out: list[str] = []
    seen: set[str] = set()
    for reason in reasons:
        r = reason.strip()
        if not r:
            continue
        norm = re.sub(r"\s+", " ", r)[:72].lower()
        if norm in seen:
            continue
        if _token_overlap(norm, blob):
            continue
        seen.add(norm)
        out.append(r)
        if len(out) >= limit:
            break
    return out


def build_coherence_note_full(
    major_title: str,
    uni_name: str,
    country_name: str,
    picker: NarrativePicker,
) -> str:
    return picker.choose("coherence_full", _COHERENCE_FULL).format(
        major=major_title, uni=uni_name, country=country_name
    )


def confidence_label(confidence: str, picker: NarrativePicker) -> str:
    pool = _CONFIDENCE_LABELS.get(confidence, _CONFIDENCE_LABELS["medium"])
    return picker.choose(f"conf_{confidence}", pool)


def collect_insights(
    profile: ApplicantProfile,
    picker: NarrativePicker,
    faq_insights: list[str],
    *,
    next_degree_label: str = "",
) -> list[str]:
    from .models import EvaluationRequest

    ev = profile.eval_req
    blocks: list[tuple[str, list[str]]] = []

    for note in profile.pathway_notes[:2]:
        blocks.append(("pathway", [note]))

    if profile.gpa and profile.gpa >= 17:
        blocks.append(("ins_gpa_high", _INSIGHT_GPA_HIGH))
    elif profile.gpa and profile.gpa < 13:
        blocks.append(("ins_gpa_low", _INSIGHT_GPA_LOW))

    if profile.language_test == EvaluationRequest.TEST_NONE:
        blocks.append(("ins_lang_none", _INSIGHT_LANG_NONE))
    elif profile.lang_ielts_equiv and profile.lang_ielts_equiv < 6.0:
        blocks.append(("ins_lang_weak", _INSIGHT_LANG_WEAK))
    elif profile.lang_ielts_equiv and profile.lang_ielts_equiv >= 6.5:
        blocks.append(("ins_lang_strong", _INSIGHT_LANG_STRONG))

    if profile.research_score >= 2 and profile.is_graduate_track:
        blocks.append(("ins_research", _INSIGHT_RESEARCH))

    if ev.has_international_tests and profile.is_graduate_track:
        blocks.append(("ins_gre", _INSIGHT_GRE))

    if next_degree_label:
        blocks.append(
            (
                "ins_next_deg",
                [t.format(label=next_degree_label) for t in _INSIGHT_NEXT_DEGREE],
            )
        )

    if ev.service_scope == EvaluationRequest.SERVICE_FULL:
        blocks.append(("ins_service", _INSIGHT_SERVICE_FULL))

    if ev.apply_timeline == EvaluationRequest.APPLY_SOON:
        blocks.append(("ins_timeline", _INSIGHT_TIMELINE_SOON))

    if ev.has_financial_capacity:
        blocks.append(("ins_fin", _INSIGHT_FINANCIAL))

    if ev.marital_status == EvaluationRequest.MARITAL_MARRIED:
        blocks.append(("ins_married", _INSIGHT_MARITAL_MARRIED))
    elif ev.marital_status == EvaluationRequest.MARITAL_SINGLE:
        blocks.append(("ins_marital_single", _INSIGHT_MARITAL_SINGLE))

    if ev.has_conference_article:
        blocks.append(("ins_conference", _INSIGHT_CONFERENCE))

    if ev.has_book:
        blocks.append(("ins_book", _INSIGHT_BOOK))

    # ترتیب بلوک‌ها بر اساس seed — هر کاربر ترتیب متفاوت
    order = list(range(len(blocks)))
    order.sort(key=lambda i: (picker.seed + i * 31) % 997)
    shuffled_blocks = [blocks[i] for i in order]

    insights: list[str] = []
    for cat, variants in shuffled_blocks:
        insights.append(picker.choose(cat, variants))

    for faq_line in faq_insights[:2]:
        if faq_line and faq_line not in insights:
            insights.append(faq_line)

    if len(insights) < 3:
        insights.append(picker.choose("ins_default", _INSIGHT_DEFAULT))

    return _dedupe_lines(insights, limit=8)
