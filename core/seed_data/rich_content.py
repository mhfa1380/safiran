"""
محتوای غنی، کاربردی و انسانی برای صفحات رشته و دانشگاه — با HTML دسته‌بندی‌شده.
"""
from __future__ import annotations

import re
from typing import Any

from .seo_content_shared import COUNTRY_SEO_HOOKS as _COUNTRY_SEO_HOOKS, evaluation_href as _evaluation_href

# دانشگاه‌های پرنمایش GSC با متن اختصاصی
_UNIVERSITY_RICH_INTROS: dict[str, str] = {
    "peking-university": (
        "دانشگاه پکن (Peking University) قدیمی‌ترین دانشگاه مدرن چین و یکی از "
        "پرتقاضاترین مقاصد برای دانشجویان ایرانی در رشته‌های پزشکی، حقوق، اقتصاد و "
        "مهندسی است. پردیس در پکن دسترسی به مراکز تحقیقاتی، بیمارستان‌های آموزشی "
        "و شبکه آلبومینی قوی را فراهم می‌کند."
    ),
    "fudan-university": (
        "دانشگاه فودان (Fudan University) در شانگهای از برترین دانشگاه‌های چین "
        "در حوزه پزشکی، مدیریت، روابط بین‌الملل و علوم انسانی است. موقعیت شهری "
        "آن فرصت کارآموزی در شرکت‌های چندملیتی و دسترسی به بورسیه CSC را تقویت می‌کند."
    ),
    "universidad-complutense-madrid": (
        "دانشگاه کمپلوتنسه مادرید (UCM) یکی از بزرگ‌ترین و قدیمی‌ترین دانشگاه‌های "
        "اسپانیا است و برای رشته‌های پزشکی، حقوق، ادبیات و علوم انسانی شهرت دارد. "
        "شهریه دولتی مناسب و زندگی دانشجویی در پایتخت از مزایای اصلی اپلای به UCM است."
    ),
    "universidad-de-granada": (
        "دانشگاه گرانادا در جنوب اسپانیا مقصد محبوب دانشجویان بین‌المللی است؛ "
        "به‌ویژه برای رشته‌های گردشگری، معماری، زبان و علوم انسانی. هزینه زندگی "
        "نسبت به مادرید و بارسلونا پایین‌تر است."
    ),
    "university-of-windsor": (
        "دانشگاه وینزر در انتاریوی کانادا، نزدیک مرز آمریکا، برای رشته‌های مهندسی، "
        "کسب‌وکار و بهداشت گزینه‌ای واقع‌بینانه با شانس پذیرش مناسب‌تر نسبت به "
        "دانشگاه‌های Tier-1 است و مسیر PGWP کانادا را پوشش می‌دهد."
    ),
    "shandong-university": (
        "دانشگاه شاندونگ (Shandong University) در جینان از دانشگاه‌های Project 985 "
        "چین است و در پزشکی، مهندسی و علوم پایه پذیرش فعال دارد. شهریه و هزینه "
        "زندگی نسبت به پکن و شانگهای مقرون‌به‌صرفه‌تر است."
    ),
    "universitat-de-valencia": (
        "دانشگاه والنسیا (Universitat de València) در ساحل مدیترانه اسپانیا مقصد محبوب "
        "دانشجویان ایرانی است — به‌ویژه در رشته‌های گردشگری، علوم و مهندسی. "
        "هزینه زندگی نسبت به مادرید و بارسلونا متعادل‌تر است."
    ),
    "sichuan-university": (
        "دانشگاه سیچوان (Sichuan University) در چنگدو از دانشگاه‌های 985 چین است "
        "و در پزشکی، دندانپزشکی و مهندسی برای متقاضیان بین‌المللی شناخته شده است."
    ),
    "hunan-university": (
        "دانشگاه هونان (Hunan University) در چانگشا ترکیبی از تاریخ کهن و رتبه‌بندی "
        "مدرن دارد و برای رشته‌های مهندسی، معماری و مدیریت گزینه مناسبی است."
    ),
    "sun-yat-sen-university": (
        "دانشگاه سون یات سن (Zhongshan University) در گوانگژو از قطب‌های پزشکی "
        "و علوم زیستی چین است و پذیرش بین‌المللی فعال دارد."
    ),
    "memorial-university": (
        "مموریال یونیورسیتی در نیوفاندلند کانادا یکی از دانشگاه‌های مقرون‌به‌صرفه "
        "با شهریه پایین‌تر نسبت به انتاریو و بریتیش کلمبیا است — مناسب برای شروع "
        "مسیر PGWP کانادا."
    ),
    "beihang-university": (
        "دانشگاه بیهانگ (Beihang / BUAA) در پکن تخصص اصلی‌اش هوافضا، مهندسی و "
        "فناوری است و برای علاقه‌مندان STEM چین بسیار پرطرفدار است."
    ),
    "york-university": (
        "یورک یونیورسیتی در تورonto کانادا یکی از بزرگ‌ترین دانشگاه‌های کشور است "
        "با تنوع رشته بالا و مسیرهای Co-op در برخی برنامه‌ها."
    ),
}

_FIELD_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("فناوری و مهندسی", ("مهندسی", "کامپیوتر", "نرم", "برق", "مکانیک", "هوش", "فناوری", "اطلاعات", "شبکه", "امنیت")),
    ("سلامت و پزشکی", ("پزشکی", "دندان", "پرستاری", "دارو", "بهداشت", "زیست", "فیزیوتراپی", "تغذیه", "سلامت")),
    ("مدیریت و مالی", ("مدیریت", "اقتصاد", "برنامه‌ریزی", "حسابداری", "MBA", "مالی", "بازرگانی", "کارآفرینی")),
    ("هنر و طراحی", ("طراحی", "هنر", "معماری", "موسیقی", "عکاسی", "سینما", "نمایش", "مد", "لباس")),
    ("علوم انسانی", ("حقوق", "روانشناسی", "علوم تربیتی", "زبان", "ادبیات", "تاریخ", "فلسفه", "جامعه")),
)


def _field_category(title: str) -> str:
    for label, keys in _FIELD_PATTERNS:
        if any(k in title for k in keys):
            return label
    return "تحصیلات تخصصی"


def _first_fact_row(rows: list, *, join: str = " — ") -> str:
    if not rows:
        return ""
    row = rows[0]
    if isinstance(row, (list, tuple)) and len(row) >= 2:
        return f"{row[0]}{join}{row[1]}"
    return str(row)


def _resolve_country_practical_info(country_code: str, country_label: str) -> dict[str, str]:
    """اطلاعات عملی کشور — اولویت با دادهٔ غنی جهانی، سپس جدول ثابت."""
    from .world_rich_country_facts import get_world_country_facts

    specifics: dict[str, dict[str, str]] = {
        "canada": {
            "lang": "IELTS ۶.۵ (یا معادل) برای اکثر برنامه‌ها؛ برخی کالج‌ها ۶.۰ می‌پذیرند.",
            "cost": "شهریه سالانه حدود ۱۵ تا ۳۵ هزار دلار کانادا + زندگی ۱۲ تا ۱۸ هزار دلار.",
            "visa": "ویزای Study Permit + PAL استان؛ تمکن مالی و طرح تحصیلی شفاف لازم است.",
            "work": "کار ۲۰ ساعت در هفته در ترم + PGWP پس از فارغ‌التحصیلی.",
            "scholarship": "بورسیه ورودی، TA/RA در ارشد و بورسیه‌های استانی.",
        },
        "china": {
            "lang": "برنامه انگلیسی‌زبان (IELTS ۶+) یا چینی (HSK ۴–۵) بسته به رشته.",
            "cost": "شهریه ۳ تا ۸ هزار دلار + زندگی ۵ تا ۱۰ هزار دلار در سال.",
            "visa": "ویزای X1/X2؛ فرم JW202 و معاینه پزشکی الزامی است.",
            "work": "کار دانشجویی محدود با مجوز دانشگاه.",
            "scholarship": "CSC، بورسیه دانشگاهی و Provincial scholarships.",
        },
        "spain": {
            "lang": "اسپانیایی B2 یا برنامه‌های انگلیسی‌زبان در رشته‌های محدود.",
            "cost": "شهریه دولتی ۸۰۰ تا ۳۵۰۰ یورو + زندگی ۸ تا ۱۲ هزار یورو.",
            "visa": "ویزای نوع D؛ تمکن مالی و بیمه درمانی.",
            "work": "۲۰ ساعت کار در هفته در سال تحصیلی.",
            "scholarship": "بورسیه‌های منطقه‌ای و کمک‌هزینه تحقیقاتی.",
        },
        "south_korea": {
            "lang": "TOPIK ۳–۴ یا برنامه‌های انگلیسی‌زبان (IELTS ۵.۵–۶.۵).",
            "cost": "شهریه ۴ تا ۱۲ هزار دلار + زندگی ۷ تا ۱۰ هزار دلار.",
            "visa": "D-2 Study Visa؛ مدارک مالی و پذیرش رسمی.",
            "work": "کار دانشجویی تا ۲۰ ساعت در هفته پس از ۶ ماه.",
            "scholarship": "GKS، بورسیه KGSP و بورسیه‌های دانشگاهی.",
        },
        "japan": {
            "lang": "JLPT N2 یا برنامه English-track (TOEFL/IELTS).",
            "cost": "شهریه ۵ تا ۱۵ هزار دلار + زندگی توکیو گران‌تر از شهرهای دیگر.",
            "visa": "Student Visa؛ Certificate of Eligibility از دانشگاه.",
            "work": "تا ۲۸ ساعت کار در هفته با مجوز.",
            "scholarship": "MEXT، JASSO و بورسیه‌های خصوصی.",
        },
        "germany": {
            "lang": "آلمانی B2/C1 یا برنامه انگلیسی‌زبان در رشته‌های STEM.",
            "cost": "شهریه ناچیز در دانشگاه دولتی + سمیستر ۱۵۰–۳۵۰ یورو + زندگی ۹–۱۲ هزار یورو.",
            "visa": "Blocked Account حدود ۱۱ هزار یورو + ویزای ملی نوع D.",
            "work": "۱۲۰ روز کار تمام‌وقت یا ۲۴۰ نیمه‌وقت در سال.",
            "scholarship": "DAAD، Deutschlandstipendium و بورسیه فدرال ایالت.",
        },
    }

    info = specifics.get(country_code)
    if info is None:
        facts = get_world_country_facts(country_code)
        if facts:
            tuition = _first_fact_row(facts.get("tuition") or [])
            living = _first_fact_row(facts.get("living_costs") or [], join=": ")
            cost_bits = [bit for bit in (tuition, living) if bit]
            scholarship = _first_fact_row(facts.get("scholarships") or [], join=": ")
            info = {
                "lang": (facts.get("language_note") or facts.get("lang_requirements") or "").strip()
                or "شرط زبان به دانشگاه و زبان تدریس بستگی دارد.",
                "cost": "؛ ".join(cost_bits)
                if cost_bits
                else f"شهریه و زندگی در {country_label} به شهر و نوع دانشگاه متغیر است.",
                "visa": (
                    f"{facts.get('visa_name', 'ویزای تحصیلی')} {country_label} "
                    f"با پذیرش رسمی، {facts.get('visa_finance', 'تمکن مالی')}."
                ),
                "work": (facts.get("work_rights") or "قوانین کار دانشجویی بسته به کشور متفاوت است.").strip(),
                "scholarship": scholarship
                or (facts.get("scholarship_intro") or "بورسیه ورودی و تحقیقاتی قابل بررسی است."),
            }
        else:
            info = {
                "lang": "IELTS ۶ تا ۷ یا معادل TOEFL/PTE بسته به دانشگاه.",
                "cost": "شهریه و زندگی به شهر و مقطع بستگی دارد؛ در مشاوره برآورد دقیق می‌شود.",
                "visa": f"ویزای تحصیلی {country_label} با پذیرش رسمی و تمکن مالی.",
                "work": "قوانین کار دانشجویی بسته به کشور متفاوت است.",
                "scholarship": "بورسیه ورودی و تحقیقاتی در بسیاری دانشگاه‌ها فعال است.",
            }
    return info


def _field_study_context(title: str, cat: str, country_label: str) -> str:
    notes = {
        "فناوری و مهندسی": (
            f"رشته {title} معمولاً در دانشکده‌های مهندسی و فناوری {country_label} "
            f"با تمرکز بر پروژه و کارآموزی ارائه می‌شود."
        ),
        "سلامت و پزشکی": (
            f"مسیر {title} در {country_label} اغلب شامل دوره‌های بالینی، آزمون ورودی "
            f"و کارآموزی بیمارستانی است."
        ),
        "مدیریت و مالی": (
            f"رشته {title} در دانشکده‌های اقتصاد، مدیریت و علوم اجتماعی {country_label} "
            f"تدریس می‌شود و برای بازار کار به زبان تخصصی و تحلیل داده متکی است."
        ),
        "هنر و طراحی": (
            f"برای {title} در {country_label} پورتفولیو و مصاحبه آکادمیک "
            f"اغلب به اندازه معدل اهمیت دارد."
        ),
        "علوم انسانی": (
            f"رشته {title} در دانشکده‌های علوم انسانی و حقوق {country_label} "
            f"با تاکید بر پژوهش و نگارش آکادمیک ارائه می‌شود."
        ),
    }
    return notes.get(
        cat,
        f"برنامه {title} در دانشگاه‌های {country_label} به صورت کارشناسی، "
        f"ارشد یا دکتری (بسته به مقطع) قابل پیگیری است.",
    )


def build_major_summary_answer(title: str, country_code: str, country_label: str) -> str:
    """پاسخ کوتاه و مستقیم به «تحصیل X در Y برای ایرانی‌ها چگونه است؟»"""
    from .world_rich_country_facts import get_world_country_facts

    cat = _field_category(title)
    info = _resolve_country_practical_info(country_code, country_label)
    facts = get_world_country_facts(country_code)
    cities = ""
    if facts and facts.get("cities"):
        city_names = [c[0] if isinstance(c, (list, tuple)) else str(c) for c in facts["cities"][:2]]
        cities = f" در شهرهایی مانند {' و '.join(city_names)}"

    field_ctx = _field_study_context(title, cat, country_label)
    return (
        f"تحصیل {title} در {country_label} برای دانشجویان ایرانی{cities} از مسیر پذیرش "
        f"رسمی دانشگاه، ارائه مدرک و ریزنمرات ترجمه‌شده، تمکن مالی و اثبات زبان انجام می‌شود. "
        f"{field_ctx} "
        f"شرط زبان: {info['lang']} "
        f"هزینه: {info['cost']} "
        f"ویزا: {info['visa']} "
        f"بورسیه: {info['scholarship']}"
    )


def _country_practical_block(country_code: str, country_label: str, title: str = "") -> str:
    hook, _extras = _COUNTRY_SEO_HOOKS.get(country_code, ("پذیرش بین‌المللی", "ویزای تحصیلی"))
    info = _resolve_country_practical_info(country_code, country_label)

    title_bit = f" برای <strong>{title}</strong>" if title else ""
    return f"""
<div class="guide-cards">
  <article class="guide-card guide-card--accent">
    <span class="guide-card__label">زبان</span>
    <h3 class="guide-card__title">شرط زبان{title_bit}</h3>
    <p>{info["lang"]}</p>
  </article>
  <article class="guide-card">
    <span class="guide-card__label">هزینه</span>
    <h3 class="guide-card__title">شهریه و زندگی</h3>
    <p>{info["cost"]}</p>
  </article>
  <article class="guide-card">
    <span class="guide-card__label">ویزا</span>
    <h3 class="guide-card__title">{hook}</h3>
    <p>{info["visa"]}</p>
  </article>
  <article class="guide-card">
    <span class="guide-card__label">کار و درآمد</span>
    <h3 class="guide-card__title">حین و پس از تحصیل</h3>
    <p>{info["work"]}</p>
  </article>
  <article class="guide-card">
    <span class="guide-card__label">بورسیه</span>
    <h3 class="guide-card__title">فرصت‌های مالی</h3>
    <p>{info["scholarship"]}</p>
  </article>
</div>
"""


def _guide_toc(anchors: list[tuple[str, str]]) -> str:
    items = "".join(f'<li><a href="#{aid}">{label}</a></li>' for aid, label in anchors)
    return f"""
<nav class="guide-toc" aria-label="فهرست مطالب">
  <p class="guide-toc__title">در این راهنما می‌خوانید</p>
  <ul>{items}</ul>
</nav>
"""


def _answer_search_query(
    query: str,
    *,
    name: str,
    country_label: str,
    country_code: str,
) -> str:
    """پاسخ مستقیم به جستجوی کاربر — بدون متن متا دربارهٔ خود جستجو."""
    q = (query or "").lower()
    summary = build_major_summary_answer(name, country_code, country_label)

    if any(k in q for k in ("بورسیه", "csc", "gks", "mext", "daad")):
        info = _resolve_country_practical_info(country_code, country_label)
        return (
            f"برای {name} در {country_label} بورسیه‌های ورودی و تحقیقاتی قابل بررسی است. "
            f"{info['scholarship']} "
            f"اپلای را حداقل ۶ تا ۹ ماه قبل از ترم هدف شروع کنید؛ معدل، زبان و رزومه "
            f"تعیین‌کننده سطح بورسیه هستند."
        )
    if any(k in q for k in ("تمکن", "هزینه زندگی", "هزینه تحصیل", "شهریه")):
        info = _resolve_country_practical_info(country_code, country_label)
        return (
            f"هزینه تحصیل {name} در {country_label}: {info['cost']} "
            f"هزینه‌های یک‌باره (ویزا، پرواز، بیمه و ترجمه مدارک) را جداگانه "
            f"در بودجه لحاظ کنید."
        )
    if any(k in q for k in ("بدون زبان", "بدون مدرک زبان", "اپلای بدون")):
        lang = _resolve_country_practical_info(country_code, country_label)["lang"]
        return (
            f"برخی برنامه‌های {name} در {country_label} پذیرش مشروط زبان می‌دهند؛ "
            f"ابتدا پذیرش آکادمیک و سپس تکمیل مدرک زبان یا دوره پیش‌نیاز. "
            f"شرط معمول: {lang}"
        )
    if "ویزا" in q:
        info = _resolve_country_practical_info(country_code, country_label)
        return (
            f"پس از پذیرش {name} باید ویزای تحصیلی {country_label} را با مدارک مالی، "
            f"بیمه و طرح تحصیلی شفاف اخذ کنید. {info['visa']}"
        )
    if any(k in q for k in ("بازار کار", "شغل", "کار بعد", "اقامت")):
        info = _resolve_country_practical_info(country_code, country_label)
        cat = _field_category(name)
        return (
            f"افق شغلی {name} در {country_label} به مهارت عملی، زبان تخصصی و کارآموزی بستگی دارد. "
            f"{info['work']} "
            f"در حوزه {cat} ارتباط با اساتید و پروژه از همان ترم اول مهم است."
        )
    if any(k in q for k in ("چگونه", "چطور", "راهنما", "شرایط", "پذیرش", "تحصیل")):
        return summary
    return summary


def _is_redundant_search_query(query: str, *, name: str, country_label: str) -> bool:
    q = (query or "").strip()
    if not q:
        return True
    if name in q and country_label and country_label in q:
        if any(k in q for k in ("چگونه", "چطور", "راهنما", "شرایط", "تحصیل")):
            return True
    normalized = re.sub(r"\s+", " ", q)
    page_q = f"تحصیل {name} در {country_label}"
    return normalized.startswith(page_q) or page_q in normalized


def _build_search_intent_section(
    queries: list[str],
    *,
    name: str,
    country_label: str,
    country_code: str,
) -> tuple[str, list[tuple[str, str]]]:
    """بخش HTML + FAQ اضافه از روی جستجوهای GSC."""
    if not queries:
        return "", []
    unique = [
        q
        for q in dict.fromkeys(queries)
        if q and not _is_redundant_search_query(q, name=name, country_label=country_label)
    ][:4]
    if not unique:
        return "", []

    cards = []
    extra_faqs = []
    for q in unique:
        answer = _answer_search_query(q, name=name, country_label=country_label, country_code=country_code)
        cards.append(
            f'<article class="guide-card guide-card--accent">'
            f'<span class="guide-card__label">سوال پرتکرار</span>'
            f'<h3 class="guide-card__title">{q}</h3>'
            f"<p>{answer}</p></article>"
        )
        extra_faqs.append((q, answer))
    html = (
        '<section class="guide-block" id="guide-search">'
        f'<h2 class="guide-block__title">سوالات مرتبط با {name} در {country_label}</h2>'
        f'<div class="guide-cards">{"".join(cards)}</div></section>'
    )
    return html, extra_faqs


def build_rich_major_short(title: str, country_label: str, country_code: str = "") -> str:
    text = build_major_summary_answer(title, country_code, country_label)
    if len(text) > 320:
        return text[:317].rstrip() + "…"
    return text


def build_rich_major_description(
    title: str,
    country_code: str,
    country_label: str,
    *,
    search_queries: list[str] | None = None,
) -> str:
    cat = _field_category(title)
    eval_link = _evaluation_href(country_code, major=title, ref="major-rich")

    anchors = [
        ("guide-intro", "معرفی و چشم‌انداز"),
    ]
    if search_queries:
        anchors.append(("guide-search", "پاسخ جستجوی شما"))
    anchors.extend(
        [
            ("guide-fit", "برای چه کسانی مناسب است؟"),
            ("guide-admission", "شرایط و مدارک"),
            ("guide-cost", "هزینه و بورسیه"),
            ("guide-path", "مسیر اپلای"),
            ("guide-career", "آینده شغلی"),
        ]
    )
    toc = _guide_toc(anchors)
    practical = _country_practical_block(country_code, country_label, title)
    search_html, _ = _build_search_intent_section(
        search_queries or [],
        name=title,
        country_label=country_label,
        country_code=country_code,
    )

    career_para = {
        "فناوری و مهندسی": (
            f"فارغ‌التحصیلان {title} معمولاً در تیم‌های نرم‌افزار، داده، سخت‌افزار، "
            f"امنیت سایبری یا پروژه‌های تحقیقاتی جذب می‌شوند. اگر هدف شما اقامت "
            f"پس از تحصیل است، رشته‌های STEM در {country_label} اغلب امتیاز بیشتری دارند."
        ),
        "سلامت و پزشکی": (
            f"مسیر {title} به آزمون‌های ورودی، کارآموزی بالینی و مجوزهای حرفه‌ای "
            f"وابسته است. زودتر مشخص کنید قصد دارید به ایران برگردید یا در {country_label} "
            f"رزیدنسی/مجوز بگیرید — این تصمیم روی انتخاب دانشگاه اثر مستقیم دارد."
        ),
        "هنر و طراحی": (
            f"برای {title} پورتفولیو اغلب مهم‌تر از معدل خام است. پیش از اپلای، "
            f"۳ تا ۵ نمونه کار حرفه‌ای، بیانیه هنری و رزومه آموزشی آماده کنید."
        ),
        "مدیریت و مالی": (
            f"رشته {title} در {country_label} به تجربه کاری، GMAT/GRE (در برخی مقاطع) "
            f"و مصاحبه وابسته است. دوره‌های Co-op یا internship شانس استخدام را بالا می‌برد."
        ),
    }.get(
        cat,
        f"بازار کار {title} به مهارت‌های عملی، زبان تخصصی و شبکه حرفه‌ای شما بستگی دارد. "
        f"از همان ترم اول روی پروژه، کارآموزی و ارتباط با اساتید برنامه داشته باشید.",
    )

    intro = build_major_summary_answer(title, country_code, country_label)

    return (
        f'<div class="guide-content">{toc}'
        f'<section class="guide-block" id="guide-intro">'
        f'<h2 class="guide-block__title">تحصیل {title} در {country_label}</h2>'
        f'<p class="guide-lead">{intro}</p>'
        f"<p>حوزه <strong>{cat}</strong> در {country_label} رقابتی است، اما با برنامه‌ریزی "
        f"۶ تا ۱۲ ماهه (زبان، مدارک، انتخاب دانشگاه و زمان‌بندی اپلای) شانس پذیرش واقعی وجود دارد.</p>"
        f"</section>"
        f"{search_html}"
        f'<section class="guide-block" id="guide-fit">'
        f'<h2 class="guide-block__title">این مسیر برای چه کسانی مناسب است؟</h2>'
        f"<ul>"
        f"<li>دانشجویانی که معدل قابل دفاع (معمولاً ۱۳.۵+ از ۲۰ برای کارشناسی) دارند</li>"
        f"<li>کسانی که حداقل ۶ ماه برای تقویت زبان برنامه دارند</li>"
        f"<li>متقاضیانی که بودجه شفاف برای شهریه + ۱ سال زندگی دارند</li>"
        f"<li>کسانی که هدف شغلی یا تحقیقاتی مشخص در {title} دارند</li>"
        f"</ul>"
        f'<aside class="guide-tip"><strong>نکته مشاوره:</strong> اگر معدل یا زبان شما هنوز کامل نیست، '
        f"پذیرش مشروط (Conditional) یا کالج/پات‌وی ورودی گزینه‌هایی هستند که نباید از قلم بیفتند.</aside>"
        f"</section>"
        f'<section class="guide-block" id="guide-admission">'
        f'<h2 class="guide-block__title">شرایط پذیرش و مدارک</h2>'
        f"{practical}"
        f'<div class="guide-table-wrap"><table class="guide-table">'
        f"<thead><tr><th>مدرک</th><th>توضیح کاربردی</th></tr></thead><tbody>"
        f"<tr><td>مدرک تحصیلی</td><td>دیپلم/کارشناسی/ارشد با ریزنمرات و ترجمه رسمی</td></tr>"
        f"<tr><td>زبان</td><td>IELTS/TOEFL یا زبان محلی بسته به برنامه</td></tr>"
        f"<tr><td>انگیزه‌نامه</td><td>هدف شغلی شفاف + ارتباط با {title}</td></tr>"
        f"<tr><td>رزومه و توصیه‌نامه</td><td>برای ارشد/دکتری تقریباً همیشه لازم است</td></tr>"
        f"<tr><td>پورتفولیو/آزمون</td><td>در رشته‌های هنری، پزشکی یا مهندسی خاص</td></tr>"
        f"</tbody></table></div>"
        f"</section>"
        f'<section class="guide-block" id="guide-cost">'
        f'<h2 class="guide-block__title">هزینه واقعی و بورسیه</h2>'
        f"<p>هزینه را در سه بخش ببینید: <strong>شهریه</strong>، <strong>اسکان و خوراک</strong>، "
        f"و <strong>هزینه‌های یک‌باره</strong> (ویزا، پرواز، بیمه، ترجمه مدارک). "
        f"بسیاری از دانشجویان فقط شهریه را حساب می‌کنند و بعداً با کمبود بودجه مواجه می‌شوند.</p>"
        f"<p>برای بورسیه، هرچه زودتر اپلای کنید بهتر است — بعضی برنامه‌ها ددلاین ۶ تا ۹ ماه "
        f"قبل از شروع ترم دارند. ارزیابی رایگان سفیران بر اساس معدل و رزومه شما دانشگاه‌هایی "
        f"را پیشنهاد می‌دهد که هم پذیرش و هم بورسیه واقع‌بینانه‌تر است.</p>"
        f"</section>"
        f'<section class="guide-block" id="guide-path">'
        f'<h2 class="guide-block__title">مسیر اپلای — قدم‌به‌قدم</h2>'
        f"<ol class=\"guide-steps\">"
        f"<li><strong>ارزیابی اولیه:</strong> معدل، زبان و بودجه را صادقانه بررسی کنید.</li>"
        f"<li><strong>لیست دانشگاه:</strong> ۳ سطح Dream / Match / Safe انتخاب کنید.</li>"
        f"<li><strong>مدارک:</strong> ترجمه رسمی، ریزنمرات و انگیزه‌نامه اختصاصی.</li>"
        f"<li><strong>اپلای آنلاین:</strong> فرم‌ها + اپلود مدارک + پرداخت کارمزد.</li>"
        f"<li><strong>پذیرش و ویزا:</strong> LoA، تمکن مالی، مصاحبه در صورت نیاز.</li>"
        f"</ol>"
        f'<p>برای دریافت لیست شخصی‌سازی‌شده دانشگاه‌های {title} در {country_label}، '
        f'<a href="{eval_link}">ارزیابی هوشمند رایگان</a> را تکمیل کنید یا '
        f'<a href="/رزرو-مشاوره/">جلسه مشاوره</a> رزرو نمایید.</p>'
        f"</section>"
        f'<section class="guide-block" id="guide-career">'
        f'<h2 class="guide-block__title">افق شغلی پس از تحصیل</h2>'
        f"<p>{career_para}</p>"
        f"</section></div>"
    )


def build_rich_university_short(uni: dict, country_label: str, country_code: str = "") -> str:
    hook, _ = _COUNTRY_SEO_HOOKS.get(country_code, ("پذیرش ۲۰۲۶", ""))
    rank = uni.get("world_rank") or "برتر"
    return (
        f"{uni['name_fa']} ({uni['name_en']}) — {uni['city']}، {country_label}. "
        f"رتبه {rank}، {hook}. راهنمای کاربردی پذیرش ایرانی‌ها: زبان، شهریه، بورسیه، "
        f"ویزا و مراحل اپلای با مشاوره تخصصی سفیران."
    )


def build_rich_university_description(
    uni: dict,
    country_code: str,
    country_label: str,
    *,
    slug: str = "",
    search_queries: list[str] | None = None,
) -> str:
    slug = slug or uni.get("slug", "")
    custom_intro = _UNIVERSITY_RICH_INTROS.get(slug, "")
    eval_link = _evaluation_href(country_code, ref=f"uni-{slug or 'content'}")

    approvals = []
    if uni.get("mo_science"):
        approvals.append("وزارت علوم ایران")
    if uni.get("mo_health"):
        approvals.append("وزارت بهداشت")
    approval_text = (
        " مورد تأیید " + " و ".join(approvals) + " است"
        if approvals
        else "در فهرست دانشگاه‌های قابل بررسی برای دانشجویان ایرانی قرار دارد"
    )

    intro_para = custom_intro or (
        f"<strong>{uni['name_en']}</strong> در <strong>{uni['city']}</strong> ({country_label}) "
        f"یکی از گزینه‌های جدی تحصیل abroad برای ایرانی‌هاست. این دانشگاه {approval_text}."
    )

    rank = uni.get("world_rank") or ""
    rank_line = (
        f"در رتبه‌بندی داخلی ما جایگاه <strong>{rank}</strong> در بین دانشگاه‌های "
        f"{country_label} دارد (مرجع QS حدود {uni.get('qs_rank_note', '—')})."
        if rank
        else f"در میان دانشگاه‌های شناخته‌شده {country_label} جایگاه قابل توجهی دارد."
    )

    anchors = [
        ("guide-uni-intro", "معرفی دانشگاه"),
    ]
    if search_queries:
        anchors.append(("guide-search", "پاسخ جستجوی شما"))
    anchors.extend(
        [
            ("guide-uni-why", "مزایا برای ایرانی‌ها"),
            ("guide-uni-admission", "پذیرش و زبان"),
            ("guide-uni-apply", "مراحل اپلای"),
        ]
    )
    toc = _guide_toc(anchors)
    practical = _country_practical_block(country_code, country_label)
    search_html, _ = _build_search_intent_section(
        search_queries or [],
        name=uni["name_fa"],
        country_label=country_label,
        country_code=country_code,
    )

    return (
        f'<div class="guide-content">{toc}'
        f'<section class="guide-block" id="guide-uni-intro">'
        f"<h2 class=\"guide-block__title\">معرفی {uni['name_fa']}</h2>"
        f'<p class="guide-lead">{intro_para} {rank_line}</p>'
        f"<p>موسسه سفیران در پرونده‌های پذیرش {uni['name_fa']} تجربه عملی دارد: از انتخاب "
        f"رشته و مقطع مناسب تا آماده‌سازی مدارک، ترجمه، پیگیری پذیرش و آماده‌سازی ویزا.</p>"
        f"</section>"
        f"{search_html}"
        f'<section class="guide-block" id="guide-uni-why">'
        f"<h2 class=\"guide-block__title\">چرا {uni['name_fa']}؟</h2>"
        f"<ul>"
        f"<li>پردیس در شهر دانشجویی {uni['city']} با دسترسی به امکانات پژوهشی</li>"
        f"<li>تنوع رشته در مقاطع کارشناسی، ارشد و دکتری</li>"
        f"<li>امکان پذیرش مشروط زبان در برخی برنامه‌ها</li>"
        f"<li>فرصت بورسیه ورودی و کمک‌هزینه تحقیقاتی (بسته به رشته)</li>"
        f"</ul>"
        f"</section>"
        f'<section class="guide-block" id="guide-uni-admission">'
        f"<h2 class=\"guide-block__title\">شرایط پذیرش در {uni['name_fa']}</h2>"
        f"{practical}"
        f"</section>"
        f'<section class="guide-block" id="guide-uni-apply">'
        f"<h2 class=\"guide-block__title\">مراحل اپلای</h2>"
        f"<ol class=\"guide-steps\">"
        f"<li><strong>ارزیابی رایگان:</strong> تطابق معدل و زبان با برنامه‌های {uni['name_fa']}</li>"
        f"<li><strong>انتخاب رشته:</strong> مقطع و ددلاین مناسب</li>"
        f"<li><strong>مدارک:</strong> ترجمه رسمی + انگیزه‌نامه اختصاصی</li>"
        f"<li><strong>پذیرش:</strong> Letter of Acceptance و آماده‌سازی ویزا</li>"
        f"</ol>"
        f'<aside class="guide-tip"><strong>از تجربه پرونده‌ها:</strong> ددلاین‌ها را جدی بگیرید — '
        f"اپلای دیرتر از ۲ هفته مانده به بستن پرونده، شانس بورسیه را کم می‌کند.</aside>"
        f'<p>برای بررسی شخصی شانس پذیرش در <strong>{uni["name_fa"]}</strong>، '
        f'<a href="{eval_link}">ارزیابی هوشمند رایگان</a> را تکمیل کنید.</p>'
        f"</section></div>"
    )


def build_rich_major_faqs(
    title: str,
    country_label: str,
    country_code: str = "",
    *,
    search_queries: list[str] | None = None,
) -> list[tuple[str, str]]:
    cat = _field_category(title)
    base = [
        (
            f"برای پذیرش {title} در {country_label} از ایران چه معدلی لازم است؟",
            f"برای {cat} معمولاً معدل ۱۳.۵ تا ۱۵ از ۲۰ پایه خوبی است؛ رشته‌های پزشکی و "
            f"مهندسی برتر ممکن است ۱۶+ بخواهند. اگر معدل شما پایین‌تر است، پات‌وی کالج، "
            f"پذیرش مشروط یا دانشگاه‌های با رتبه متوسط‌تر گزینه دارند — در ارزیابی رایگان "
            f"سفیران مسیر واقع‌بینانه پیشنهاد می‌شود.",
        ),
        (
            f"بهترین دانشگاه‌ها برای {title} در {country_label} کدام‌اند؟",
            f"«بهترین» به بودجه، زبان و هدف شغلی شما بستگی دارد. ما معمولاً لیست ۸ تا ۱۵ "
            f"دانشگاه را در سه سطح ریسک تقسیم می‌کنیم تا هم پذیرش داشته باشید هم بورسیه "
            f"واقع‌بینانه. صفحه ارزیابی هوشمند همین لیست را شخصی‌سازی می‌کند.",
        ),
        (
            f"هزینه تحصیل {title} در {country_label} چقدر است؟",
            f"شهریه سالانه بسته به شهر و دانشگاه از چند هزار تا بیش از ۳۰ هزار دلار/یورو "
            f"متغیر است. هزینه زندگی را جدا حساب کنید — به‌ویژه اگر همراه خانواده دارید. "
            f"در جلسه مشاوره برآورد دقیق‌تر با توجه به شهر مقصد ارائه می‌شود.",
        ),
        (
            f"آیا بورسیه {title} در {country_label} برای ایرانی‌ها فعال است؟",
            f"بله، در بسیاری کشورها بورسیه ورودی، تحقیقاتی و دولتی وجود دارد؛ "
            f"مثلاً CSC در چین، GKS در کره، MEXT در ژاپن یا بورسیه استانی کانادا. "
            f"زمان‌بندی اپلای حداقل ۶ ماه زودتر از ترم هدف برنامه‌ریزی شود.",
        ),
        (
            f"بازار کار فارغ‌التحصیلان {title} در {country_label} چطور است؟",
            f"در حوزه {cat} تقاضا به مهارت عملی، زبان تخصصی و کارآموزی شما بستگی دارد. "
            f"قوانین کار دانشجویی و اقامت پس از تحصیل کشور به کشور فرق می‌کند — "
            f"قبل از اپلای بدانید هدف شما تحصیل کوتاه‌مدت است یا مهاجرت بلندمدت.",
        ),
        (
            f"چقدر طول می‌کشد تا برای {title} در {country_label} پذیرش بگیرم؟",
            "از شروع آماده‌سازی زبان تا ویزا معمولاً ۶ تا ۱۴ ماه زمان می‌برد. "
            "اگر زبان آماده باشد، فقط اپلای و ویزا ۳ تا ۶ ماه است. هرچه زودتر ارزیابی کنید، "
            "ددلاین از دست نمی‌رود.",
        ),
    ]
    _, extra = _build_search_intent_section(
        search_queries or [],
        name=title,
        country_label=country_label,
        country_code=country_code,
    )
    seen = {q for q, _ in base}
    for q, a in extra:
        if q not in seen:
            base.append((q, a))
            seen.add(q)
    return base


def build_rich_university_faqs(
    uni: dict,
    country_label: str,
    country_code: str = "",
    *,
    search_queries: list[str] | None = None,
) -> list[tuple[str, str]]:
    name = uni["name_fa"]
    city = uni.get("city") or country_label
    base = [
        (
            f"آیا {name} برای دانشجویان ایرانی مناسب است؟",
            f"بله؛ {uni['name_en']} در {city} پذیرش بین‌المللی فعال دارد. موفقیت به معدل، "
            f"زبان، انگیزه‌نامه و انتخاب رشته مناسب بستگی دارد. تیم سفیران بر اساس رزومه واقعی "
            f"شما می‌گوید این دانشگاه در سطح Dream است یا Match.",
        ),
        (
            f"حداقل معدل و زبان برای اپلای {name} چقدر است؟",
            f"برای کارشناسی معمولاً معدل ۱۳.۵+ و IELTS ۶ تا ۶.۵ (یا معادل) رایج است. "
            f"رشته‌های پزشکی و MBA شرایط سخت‌گیرانه‌تری دارند. پذیرش مشروط زبان "
            f"در برخی برنامه‌های {name} ممکن است.",
        ),
        (
            f"هزینه تحصیل و زندگی در {name} ({city}) چقدر است؟",
            f"شهریه سالانه بسته به رشته متفاوت است؛ زندگی در {city} به نوع اسکان "
            f"(خوابگاه/اجاره مشترک) وابسته است. در مشاوره هزینه را به تفکیک شهریه، "
            f"اسکان و هزینه‌های یک‌باره می‌بینید.",
        ),
        (
            f"آیا بورسیه در {name} وجود دارد؟",
            "بورسیه ورودی، تحقیقاتی و گاهی بورسیه دولتی کشور مقصد قابل بررسی است. "
            "هرچه اپلای زودتر ارسال شود، شانس بورسیه بیشتر است.",
        ),
        (
            f"چقدر طول می‌کشد پذیرش {name} صادر شود؟",
            "معمولاً ۴ تا ۱۰ هفته پس از ارسال کامل مدارک پاسخ اولیه می‌آید. "
            "کل مسیر تا ویزا ۴ تا ۸ ماه برنامه‌ریزی شود.",
        ),
        (
            f"آیا {name} مورد تأیید وزارت علوم یا بهداشت ایران است؟",
            "وضعیت تأیید به رشته و مقطع بستگی دارد. قبل از ثبت‌نام نهایی، آخرین فهرست "
            "وزارتخانه‌ها را بررسی کنید — مشاوران سفیران در این مورد راهنمایی می‌کنند.",
        ),
    ]
    _, extra = _build_search_intent_section(
        search_queries or [],
        name=name,
        country_label=country_label,
        country_code=country_code,
    )
    seen = {q for q, _ in base}
    for q, a in extra:
        if q not in seen:
            base.append((q, a))
            seen.add(q)
    return base


def university_dict_from_model(uni: Any) -> dict:
    return {
        "slug": uni.slug,
        "name_fa": uni.name_fa,
        "name_en": uni.name_en or "",
        "city": uni.city or "",
        "world_rank": uni.world_rank,
        "qs_rank_note": getattr(uni, "qs_rank_note", None) or "مرجع QS",
        "website": uni.website or "",
        "mo_science": uni.is_approved_by_mo_science,
        "mo_health": uni.is_approved_by_mo_health,
    }
