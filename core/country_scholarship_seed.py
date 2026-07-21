"""
داده اولیه راهنماهای بورسیه کشور — از منابع رسمی دانشگاه‌ها و نهادهای دولتی.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

# لینک رسمی هر برنامه — صفحه خود بورسیه/فاند، نه صفحه عمومی دانشگاه یا پورتال نامرتبط.
OFFICIAL_URL_BY_SLUG: dict[str, str] = {
    # کانادا — کارشناسی
    "york-global-leader": "https://futurestudents.yorku.ca/financing-your-degree/international-scholarships",
    "waterloo-international-entrance": "https://uwaterloo.ca/future-students/node/706",
    "entrance-general": "https://www.educanada.ca/scholarships-bourses/non_can/index.aspx?lang=eng",
    # کانادا — تحصیلات تکمیلی
    "mccall-macbain": "https://mccallmacbainscholars.org/apply/",
    "graduate-ta-ra": "https://www.educanada.ca/scholarships-bourses/non_can/index.aspx?lang=eng",
    "university-entrance-master": "https://www.educanada.ca/scholarships-bourses/non_can/index.aspx?lang=eng",
    "phd-funding-package": "https://www.grad.ubc.ca/awards/minimum-funding-policy-phd-students",
    "ontario-trillium": "https://graduatestudies.uoguelph.ca/current/funding/scholarships/gov-fundedawards/ots",
    # چین
    "csca-requirement": "https://csca.cn/home",
    "university-president-bachelor": "https://www.campuschina.org/content/details3_74775.html",
    "provincial-bachelor": "https://www.campuschina.org/content/details3_74775.html",
    "provincial-master": "https://www.campuschina.org/content/details3_74775.html",
    "university-phd-fellowship": "https://www.campuschina.org/content/details3_74775.html",
    # اسپانیا
    "university-merit-bachelor": "https://www.educacionfpydeportes.gob.es/servicios-al-ciudadano/catalogo/estudiantes/becas-ayudas/para-estudiar.html",
    "regional-bachelor": "https://www.becaseducacion.gob.es/portada.htm",
    "ujaen-talent-master": "https://www.ujaen.es/internacional/en/international-calls/talent-attraction-scholarships-masters-degrees-202627",
    "fpi-spain": "https://www.csic.es/es/formacion-y-empleo/formacion-de-personal-investigador/doctorado/contratos-predoctorales",
    "la-caixa-master": "https://lacaixafoundation.org/en/postgraduate-fellowships-abroad-call",
}


def _programs(guide, Scholarship, items: list[dict]) -> None:
    for item in items:
        slug = item["slug"]
        if slug in OFFICIAL_URL_BY_SLUG:
            item = {**item, "official_url": OFFICIAL_URL_BY_SLUG[slug]}
        Scholarship.objects.update_or_create(
            guide=guide,
            slug=slug,
            defaults={**item, "is_active": True},
        )


def refresh_scholarship_official_urls(apps=None) -> int:
    """همگام‌سازی official_url همه بورسیه‌ها با OFFICIAL_URL_BY_SLUG."""
    if apps is None:
        from core.models import CountryScholarship as Scholarship
    else:
        Scholarship = apps.get_model("core", "CountryScholarship")
    updated = 0
    for slug, url in OFFICIAL_URL_BY_SLUG.items():
        updated += Scholarship.objects.filter(slug=slug).exclude(official_url=url).update(
            official_url=url
        )
    return updated


def _guide(Guide, country, target_degree: str, data: dict[str, Any]):
    return Guide.objects.update_or_create(
        country=country,
        target_degree=target_degree,
        defaults={**data, "is_active": True},
    )[0]


def seed_canada_graduate(StudyCountry, Guide, Scholarship) -> None:
    country = StudyCountry.objects.filter(code="canada").first()
    if not country:
        return

    country.scholarship_info = (
        "<p>کانادا بورسیه کارشناسی، فاند ارشد/دکتری و برنامه‌های استانی دارد.</p>"
        "<p>"
        "<a href=\"/کشور/canada/بورسیه/?target_degree=bachelor\">کارشناسی</a> · "
        "<a href=\"/کشور/canada/بورسیه/?target_degree=master\">ارشد</a> · "
        "<a href=\"/کشور/canada/بورسیه/?target_degree=phd\">دکتری</a>"
        "</p>"
    )
    country.save(update_fields=["scholarship_info"])

    # ─── ارشد ───
    master_guide = _guide(
        Guide,
        country,
        "master",
        {
            "headline": "بورسیه و فاند ارشد کانادا برای دانشجویان بین‌المللی",
            "intro": (
                "فاند ارشد در کانادا ترکیبی از بورسیه‌های دانشگاهی، کمک‌هزینه استانی "
                "(در انتاریو) و دستیار آموزشی/پژوهشی (TA/RA) است. "
                "بسیاری از بورسیه‌های فدرال سطح مستر مثل CGRS-M فقط برای شهروندان کانادا است؛ "
                "دانشجوی بین‌المللی باید روی بورسیه دانشگاه، استانی و فاند استاد تمرکز کند."
            ),
            "overview": (
                "<h3>مسیرهای اصلی تأمین مالی ارشد</h3>"
                "<ul>"
                "<li><strong>Ontario Graduate Scholarship (OGS):</strong> در انتاریو برای ارشد و دکتری؛ "
                "۵٬۰۰۰ دلار کانادا در هر ترم (معمولاً ۲–۳ ترم).</li>"
                "<li><strong>بورسیه ورودی دانشگاه:</strong> merit-based در McGill، UBC، Toronto و غیره.</li>"
                "<li><strong>McCall MacBain:</strong> بورسیه تمام‌هزینه بسیار رقابتی در McGill (بین‌المللی واجد شرایط).</li>"
                "<li><strong>TA/RA:</strong> دستیار تدریس یا پژوهش با استاد — اغلب پوشش بخشی شهریه + مقرری.</li>"
                "</ul>"
                "<p><em>برنامه CGRS-M (جایگزین CGS-M) حدود ۲۷٬۰۰۰ دلار است اما "
                "<strong>فقط برای شهروندان کانادا و مقیم دائم</strong> — نه دانشجوی بین‌المللی.</em></p>"
            ),
            "application_guide": (
                "<ol>"
                "<li>پذیرش ارشد را زود ارسال کنید (آذر–بهمن برای سپتامبر بعد).</li>"
                "<li>در ایمیل به استاد، علاقه به TA/RA را مطرح کنید.</li>"
                "<li>فرم OGS را از طریق دانشگاه انتاریو (نه مستقیم) پیگیری کنید.</li>"
                "<li>بورسیه‌های خارجی مثل McCall MacBain مهلت جدا دارند.</li>"
                "</ol>"
            ),
            "search_keywords": "بورسیه ارشد کانادا, OGS, McCall MacBain, فاند ارشد کانادا, graduate funding",
            "meta_title": "بورسیه ارشد کانادا ۲۰۲۶ | OGS، فاند استاد و بورسیه دانشگاهی",
            "meta_description": (
                "راهنمای بورسیه کارشناسی ارشد کانادا: OGS، McCall MacBain، "
                "بورسیه ورودی دانشگاه‌ها و TA/RA با لینک رسمی."
            ),
            "meta_keywords": "بورسیه ارشد کانادا, OGS, master scholarship canada, فاند ارشد",
        },
    )
    _programs(
        master_guide,
        Scholarship,
        [
            {
                "slug": "ontario-graduate-scholarship",
                "program_key": "ca-ogs",
                "name": "Ontario Graduate Scholarship (OGS)",
                "provider": "دولت استان انتاریو",
                "coverage": "۵٬۰۰۰ دلار کانادا در هر ترم تحصیلی (اغلب ۱۰٬۰۰۰–۱۵٬۰۰۰ در سال)",
                "eligibility": (
                    "<p>دانشجویان ارشد و دکتری تمام‌وقت در دانشگاه‌های منتخب انتاریو؛ "
                    "<strong>دانشجویان بین‌المللی واجد شرایط</strong> (مثلاً U of T). "
                    "معدل حدود A- در دو سال آخر تحصیل.</p>"
                ),
                "deadlines": "از طریق دانشگاه — معمولاً بهمن/اسفند برای سال تحصیلی بعد",
                "official_url": "https://www.sgs.utoronto.ca/awards/ontario-graduate-scholarship/",
                "min_gpa": Decimal("16.50"),
                "lang_requirement": "IELTS 7+ یا معادل (شرط پذیرش دانشگاه)",
                "highlights": "قابل ترکیب با فاند استاد در برخی موارد\n"
                "رقابتی در سطح دانشگاه/دانشکده",
                "tags": "انتاریو, ارشد, بین‌المللی",
                "is_featured": True,
                "order": 1,
            },
            {
                "slug": "mccall-macbain",
                "program_key": "ca-mccall-macbain",
                "name": "McCall MacBain Scholarship (McGill)",
                "provider": "McGill University / McCall MacBain Foundation",
                "coverage": "شهریه + مقرری زندگی + برنامه رهبری (بورسیه کامل)",
                "eligibility": (
                    "<p>برای ارشد یا حرفه‌ای در McGill؛ شهروندان همه کشورها. "
                    "حداکثر حدود ۳۰ بورسیه کامل و ۱۰۰ جایزه ورودی در سال. "
                    "رزومه رهبری، خدمت اجتماعی و تعالی علمی.</p>"
                ),
                "deadlines": "اپلای بین‌المللی ۲۰۲۶–۲۰۲۷: حدود ۱۹ آگوست ۲۰۲۶ (سایت mccallmacbainscholars.org)",
                "official_url": OFFICIAL_URL_BY_SLUG["mccall-macbain"],
                "min_gpa": Decimal("17.00"),
                "lang_requirement": "شرط زبان McGill",
                "highlights": "یکی از کامل‌ترین بورسیه‌های ارشد کانادا\n"
                "بین‌المللی واجد شرایط",
                "tags": "تمام‌هزینه, ارشد, رقابتی",
                "is_featured": True,
                "order": 2,
            },
            {
                "slug": "ubc-graduate-funding",
                "program_key": "ca-ubc-grad",
                "name": "فاند تحصیلات تکمیلی UBC",
                "provider": "University of British Columbia",
                "coverage": "ترکیب بورسیه merit، TA/RA و کمک‌هزینه بین‌المللی",
                "eligibility": (
                    "<p>حدود ۳۵٪ دانشجویان ارشد UBC بین‌المللی هستند. "
                    "بسته مالی اغلب از پیشنهاد دانشکده هنگام پذیرش می‌آید.</p>"
                ),
                "deadlines": "هم‌زمان با اپلای ارشد — دسامبر–ژانویه برای سپتامبر",
                "official_url": "https://www.grad.ubc.ca/prospective-students/international-students/funding-international-students",
                "min_gpa": Decimal("16.00"),
                "lang_requirement": "IELTS 6.5–7.0 بسته به برنامه",
                "highlights": "تمرکز بر پکیج استاد و دانشکده\n"
                "امکان 4-Year Fellowship برای برترین‌ها",
                "tags": "فاند, ارشد, ونکوور",
                "is_featured": False,
                "order": 3,
            },
            {
                "slug": "graduate-ta-ra",
                "program_key": "ca-ta-ra",
                "name": "دستیاری آموزشی/پژوهشی (TA/RA)",
                "provider": "دانشگاه‌های کانادا",
                "coverage": "معمولاً ۱۵٬۰۰۰–۲۵٬۰۰۰ دلار کانادا در سال + بخشی از شهریه",
                "eligibility": (
                    "<p>وابسته به استاد راهنما و بودجه پروژه؛ رایج در STEM و علوم اجتماعی. "
                    "قرارداد سالانه با تمدید بر اساس عملکرد.</p>"
                ),
                "deadlines": "مذاکره پس از پذیرش یا همراه با اپلای",
                "official_url": OFFICIAL_URL_BY_SLUG["graduate-ta-ra"],
                "min_gpa": Decimal("15.50"),
                "lang_requirement": "IELTS 6.5+",
                "highlights": "رایج‌ترین مسیر عملی برای بین‌المللی‌ها\n"
                "نیاز به ارتباط با استاد",
                "tags": "TA, RA, فاند",
                "is_featured": False,
                "order": 4,
            },
            {
                "slug": "university-entrance-master",
                "program_key": "ca-master-entrance",
                "name": "بورسیه ورودی ارشد دانشگاه‌ها",
                "provider": "دانشگاه‌های کانادا",
                "coverage": "۵٬۰۰۰ تا ۳۰٬۰۰۰ دلار — یک‌باره یا تمدیدشونده",
                "eligibility": (
                    "<p>بر اساس معدل، SOP و توصیه‌نامه؛ هر دانشگاه فهرست جدا دارد. "
                    "برخی خودکار، برخی نیاز به فرم جدا.</p>"
                ),
                "deadlines": "متفاوت — اغلب هم‌زمان پذیرش",
                "official_url": OFFICIAL_URL_BY_SLUG["university-entrance-master"],
                "min_gpa": Decimal("16.00"),
                "lang_requirement": "بسته به برنامه",
                "highlights": "گسترده‌ترین دسته برای بین‌المللی\n"
                "مقایسه چند دانشگاه ضروری است",
                "tags": "ارشد, merit",
                "is_featured": False,
                "order": 5,
            },
        ],
    )

    # ─── دکتری ───
    phd_guide = _guide(
        Guide,
        country,
        "phd",
        {
            "headline": "بورسیه و فاند دکتری کانادا — CGRS-D، OGS و فاند پژوهشی",
            "intro": (
                "دکتری در کانادا اغلب با بسته مالی استاد (funding package) شروع می‌شود؛ "
                "علاوه بر آن بورسیه‌های ملی جدید CGRS-D (جایگزین Vanier) برای پژوهشگران "
                "بین‌المللیِ در حال تحصیل در کانادا وجود دارد."
            ),
            "overview": (
                "<h3>برنامه‌های مهم دکتری</h3>"
                "<ul>"
                "<li><strong>CGRS-D:</strong> ۴۰٬۰۰۰ دلار/سال به مدت ۳۶ ماه؛ "
                "بین‌المللی‌های <em>ثبت‌نام‌شده در دکتری کانادا</em> واجد شرایط "
                "(سقف ۱۵٪ برای متقاضیان بین‌المللی در هر آژانس).</li>"
                "<li><strong>OGS:</strong> ۵٬۰۰۰ دلار/ترم در انتاریو.</li>"
                "<li><strong>فاند استاد:</strong> شهریه + ۲۰٬۰۰۰–۳۵٬۰۰۰ دلار/سال در STEM.</li>"
                "</ul>"
                "<p>برنامه Vanier (۵۰٬۰۰۰/سال) دیگر پذیرش نمی‌کند و با CGRS-D جایگزین شده است.</p>"
            ),
            "application_guide": (
                "<ol>"
                "<li>قبل از اپلای با استادان هم‌راستا تماس بگیرید (Proposal کوتاه).</li>"
                "<li>بسته فاند پیشنهادی دانشکده را در نامه پذیرش بخوانید.</li>"
                "<li>CGRS-D از طریق دانشگاه و آژانس NSERC/SSHRC/CIHR نامزد می‌شود.</li>"
                "</ol>"
            ),
            "search_keywords": "بورسیه دکتری کانادا, CGRS-D, Vanier, فاند دکتری, PhD funding canada",
            "meta_title": "بورسیه دکتری کانادا ۲۰۲۶ | CGRS-D، OGS و فاند استاد",
            "meta_description": (
                "راهنمای فاند دکتری کانادا: CGRS-D (۴۰٬۰۰۰ دلار/سال)، OGS، "
                "فاند پژوهشی استاد و نکات اپلای بین‌المللی."
            ),
            "meta_keywords": "بورسیه دکتری کانادا, CGRS-D, PhD scholarship, فاند دکتری",
        },
    )
    _programs(
        phd_guide,
        Scholarship,
        [
            {
                "slug": "cgrs-d",
                "program_key": "ca-vanier",
                "name": "Canada Graduate Research Scholarship – Doctoral (CGRS-D)",
                "provider": "CIHR / NSERC / SSHRC",
                "coverage": "۴۰٬۰۰۰ دلار کانادا در سال — ۳۶ ماه",
                "eligibility": (
                    "<p>جایگزین Vanier CGS از ۲۰۲۵. "
                    "شامل شهروند کانادا، مقیم دائم و "
                    "<strong>دانشجوی بین‌المللی ثبت‌نام‌شده در دکتری کانادا</strong> در زمان اپلای. "
                    "حداکثر ۳۶ ماه تحصیل تمام‌وقت در دکتری. "
                    "سقف ۱۵٪ جوایز برای متقاضیان بین‌المللی در هر آژانس.</p>"
                ),
                "deadlines": "نامزدی دانشگاه: اکتبر ۲۰۲۵ (CIHR/NSERC ۱ اکتبر، SSHRC ۸ اکتبر) — سالانه",
                "official_url": "https://www.nserc-crsng.gc.ca/Students-Etudiants/PG-CS/cgrsd-besrd_eng.asp",
                "min_gpa": Decimal("17.00"),
                "lang_requirement": "رزومه پژوهشی قوی",
                "highlights": "بورسیه ملی سطح دکتری\n"
                "جایگزین رسمی Vanier",
                "tags": "دکتری, دولتی, پژوهشی",
                "is_featured": True,
                "order": 1,
            },
            {
                "slug": "ogs-phd",
                "program_key": "ca-ogs-phd",
                "name": "Ontario Graduate Scholarship (OGS) — دکتری",
                "provider": "استان انتاریو",
                "coverage": "۵٬۰۰۰ دلار/ترم (تا ۱۵٬۰۰۰ در سال در صورت ۳ ترم)",
                "eligibility": (
                    "<p>دکتری تمام‌وقت در دانشگاه انتاریو؛ بین‌المللی واجد شرایط؛ "
                    "معدل A- در دو سال آخر.</p>"
                ),
                "deadlines": "از طریق دانشگاه — بهمن/اسفند",
                "official_url": "https://www.sgs.utoronto.ca/awards/ontario-graduate-scholarship/",
                "min_gpa": Decimal("16.50"),
                "lang_requirement": "شرط زبان دانشگاه",
                "highlights": "مکمل فاند استاد\n"
                "رقابت درون‌دانشگاهی",
                "tags": "انتاریو, دکتری",
                "is_featured": True,
                "order": 2,
            },
            {
                "slug": "phd-funding-package",
                "program_key": "ca-phd-package",
                "name": "بسته فاند دکتری (Funding Package)",
                "provider": "دانشگاه و استاد راهنما",
                "coverage": "اغلب شهریه + ۲۰٬۰۰۰–۳۵٬۰۰۰ دلار/سال (۴–۵ سال)",
                "eligibility": (
                    "<p>رایج در مهندسی، علوم پایه و CS. "
                    "پذیرش منوط به تأیید استاد و بودجه پروژه است.</p>"
                ),
                "deadlines": "هم‌زمان اپلای دکتری (آذر–بهمن)",
                "official_url": OFFICIAL_URL_BY_SLUG["phd-funding-package"],
                "min_gpa": Decimal("16.50"),
                "lang_requirement": "IELTS 6.5–7.5",
                "highlights": "مسیر اصلی بین‌المللی‌ها\n"
                "شفاف‌سازی مبلغ در نامه پذیرش",
                "tags": "فاند, دکتری, RA",
                "is_featured": False,
                "order": 3,
            },
            {
                "slug": "ontario-trillium",
                "program_key": "ca-ontario-trillium",
                "name": "Ontario Trillium Scholarship (OTS)",
                "provider": "استان انتاریو",
                "coverage": "۴۰٬۰۰۰ دلار/سال — حداکثر ۴ سال (دکتری)",
                "eligibility": (
                    "<p>برای دکتری بین‌المللی در انتاریو؛ نامزدی توسط دانشگاه. "
                    "<strong>توجه:</strong> برخی دانشگاه‌ها اعلام کرده‌اند پذیرش جدید OTS "
                    "از سوی وزارت متوقف شده — وضعیت را در دانشگاه مقصد بررسی کنید.</p>"
                ),
                "deadlines": "بدون اپلای مستقیم — نامزدی دانشکده",
                "official_url": OFFICIAL_URL_BY_SLUG["ontario-trillium"],
                "min_gpa": Decimal("17.00"),
                "lang_requirement": "A- average",
                "highlights": "مختص بین‌المللی\n"
                "بسیار رقابتی",
                "tags": "دکتری, انتاریو",
                "is_featured": False,
                "order": 4,
            },
        ],
    )


def seed_china_all(StudyCountry, Guide, Scholarship) -> None:
    country = StudyCountry.objects.filter(code="china").first()
    if not country:
        return

    country.scholarship_info = (
        "<p>چین بزرگ‌ترین برنامه بورسیه دولتی برای خارجی‌ها (CSC) را دارد: "
        "معافیت شهریه، خوابگاه و مقرری ماهانه.</p>"
        "<p><a href=\"/کشور/china/بورسیه/?target_degree=bachelor\">کارشناسی</a> · "
        "<a href=\"/کشور/china/بورسیه/?target_degree=master\">ارشد</a> · "
        "<a href=\"/کشور/china/بورسیه/?target_degree=phd\">دکتری</a></p>"
    )
    country.save(update_fields=["scholarship_info"])

    common_csc = {
        "provider": "China Scholarship Council (CSC)",
        "official_url": "https://www.campuschina.org/",
        "lang_requirement": "HSK4+ برای چینی‌زبان؛ IELTS 6.0+ یا TOEFL 80+ برای انگلیسی‌زبان",
    }

    # ─── کارشناسی ───
    bachelor = _guide(
        Guide,
        country,
        "bachelor",
        {
            "headline": "بورسیه کارشناسی چین (CSC و بورسیه دانشگاهی)",
            "intro": (
                "بورسیه دولتی چین (CSC) برای کارشناسی شامل شهریه، بیمه، خوابگاه و "
                "مقرری ۲٬۵۰۰ یوان/ماه است. از دوره ۲۰۲۶/۲۰۲۷ برای برخی متقاضیان "
                "آزمون CSCA نیز لازم است."
            ),
            "overview": (
                "<h3>پوشش CSC (دولتی)</h3>"
                "<ul>"
                "<li>شهریه: معافیت کامل</li>"
                "<li>اقامت: خوابگاه رایگان یا کمک هزینه</li>"
                "<li>بیمه: ۸۰۰ یوان/سال</li>"
                "<li>مقرری: <strong>۲٬۵۰۰ یوان/ماه</strong> (کارشناسی)</li>"
                "</ul>"
                "<p>اپلای معمولاً از طریق <strong>campuschina.org</strong> و با نامه پذیرش "
                "پیش‌مصوبه (Pre-admission) از دانشگاه.</p>"
            ),
            "application_guide": (
                "<ol>"
                "<li>دانشگاه DLI چین را انتخاب و Pre-admission بگیرید.</li>"
                "<li>در پورتال CSC نوع A (راهبری) یا B (خودمختار) را بررسی کنید.</li>"
                "<li>مدارک ترجمه‌شده و فرم فیزیکی سلامت را آماده کنید.</li>"
                "</ol>"
            ),
            "search_keywords": "بورسیه چین, CSC, بورسیه کارشناسی چین, campuschina",
            "meta_title": "بورسیه کارشناسی چین ۲۰۲۶ | CSC و بورسیه دانشگاهی",
            "meta_description": "راهنمای بورسیه کارشناسی چین: CSC با ۲۵۰۰ یوان/ماه، بورسیه رئیس دانشگاه و مهلت campuschina.",
            "meta_keywords": "بورسیه چین, CSC, بورسیه کارشناسی, تحصیل در چین",
        },
    )
    _programs(
        bachelor,
        Scholarship,
        [
            {
                **common_csc,
                "slug": "csc-bachelor",
                "program_key": "cn-csc",
                "name": "بورسیه دولتی چین (CSC) — کارشناسی",
                "coverage": "شهریه + خوابگاه + بیمه + ۲٬۵۰۰ یوان/ماه",
                "eligibility": (
                    "<p>غیرچینی؛ زیر ۲۵ سال؛ دیپلم دبیرستان؛ سلامت جسمی و روانی. "
                    "برای برخی رشته‌ها آزمون CSCA (از ۲۰۲۶/۲۰۲۷). "
                    "نامه Pre-admission از دانشگاه چین.</p>"
                ),
                "deadlines": "معمولاً تا ۱۵ فروردین ۱۴۰۵ (حدود ۴ آوریل ۲۰۲۶) — بسته به سفارت/دانشگاه",
                "min_gpa": Decimal("14.00"),
                "highlights": "محبوب‌ترین بورسیه کارشناسی\n"
                "صدها دانشگاه Designated",
                "tags": "دولتی, کارشناسی, CSC",
                "is_featured": True,
                "order": 1,
            },
            {
                "slug": "csca-requirement",
                "program_key": "cn-csca",
                "name": "آزمون CSCA (الزام جدید برخی متقاضیان)",
                "provider": "CSC / دانشگاه‌های چین",
                "coverage": "شرط ورود بورسیه — نه مبلغ مالی",
                "eligibility": (
                    "<p>برای متقاضیان کارشناسی بورسیه CSC از سال تحصیلی ۲۰۲۶/۲۰۲۷ "
                    "در برخی موارد آزمون شایستگی تحصیلی چین (CSCA) الزامی است. "
                    "جزئیات را در ابلاغیه سفارت و campuschina بخوانید.</p>"
                ),
                "deadlines": "قبل از ارسال پرونده CSC",
                "official_url": OFFICIAL_URL_BY_SLUG["csca-requirement"],
                "min_gpa": None,
                "lang_requirement": "مطابق برنامه",
                "highlights": "قانون جدید ۲۰۲۶\n"
                "عدم رعایت = رد پرونده",
                "tags": "CSCA, کارشناسی",
                "is_featured": False,
                "order": 2,
            },
            {
                "slug": "university-president-bachelor",
                "program_key": "cn-university-president",
                "name": "بورسیه رئیس دانشگاه (کارشناسی)",
                "provider": "دانشگاه‌های چین",
                "coverage": "۵۰٪ تا ۱۰۰٪ شهریه + گاهی خوابگاه",
                "eligibility": "<p>رقابت در سطح هر دانشگاه؛ جدا از یا همراه CSC.</p>",
                "deadlines": "متفاوت — معمولاً اسفند تا فروردین",
                "official_url": OFFICIAL_URL_BY_SLUG["university-president-bachelor"],
                "min_gpa": Decimal("15.00"),
                "lang_requirement": "HSK یا IELTS بسته به زبان تدریس",
                "highlights": "گزینه تکمیلی CSC\n"
                "زمان‌بندی مستقل",
                "tags": "دانشگاهی, کارشناسی",
                "is_featured": False,
                "order": 3,
            },
            {
                "slug": "provincial-bachelor",
                "program_key": "cn-provincial",
                "name": "بورسیه استانی چین",
                "provider": "دولت استانی",
                "coverage": "بخشی از شهریه + مقرری ماهانه",
                "eligibility": "<p>مثل یون‌نان، ژیانگسو و…؛ اغلب نیاز به پذیرش دانشگاه همان استان.</p>",
                "deadlines": "بهار هر سال",
                "official_url": OFFICIAL_URL_BY_SLUG["provincial-bachelor"],
                "min_gpa": Decimal("13.50"),
                "lang_requirement": "بسته به استان",
                "highlights": "رقابت کمتر از CSC مرکزی\n"
                "مناسب پرونده متوسط",
                "tags": "استانی, کارشناسی",
                "is_featured": False,
                "order": 4,
            },
        ],
    )

    # ─── ارشد ───
    master = _guide(
        Guide,
        country,
        "master",
        {
            "headline": "بورسیه ارشد چین — CSC و بورسیه استانی/دانشگاهی",
            "intro": (
                "بورسیه CSC ارشد مقرری ۳٬۰۰۰ یوان در ماه دارد و با پذیرش "
                "دانشگاه‌های معتبر چین (C9، پروژه ۹۸۵) قابل ترکیب است."
            ),
            "overview": (
                "<ul>"
                "<li>CSC Type A: نامزدی از سفارت/مرکز CSC کشور مبدأ</li>"
                "<li>CSC Type B: اپلای مستقیم به دانشگاه Designated</li>"
                "<li>مقرری ارشد: <strong>۳٬۰۰۰ یوان/ماه</strong></li>"
                "</ul>"
            ),
            "application_guide": (
                "<ol><li>استاد چینی برای رشته‌های پژوهشی توصیه می‌شود.</li>"
                "<li>دو نسخه اپلای: سفارت (A) و دانشگاه (B).</li></ol>"
            ),
            "search_keywords": "بورسیه ارشد چین, CSC master, 3000 yuan",
            "meta_title": "بورسیه ارشد چین ۲۰۲۶ | CSC با ۳۰۰۰ یوان/ماه",
            "meta_description": "راهنمای بورسیه کارشناسی ارشد چین: CSC، استانی و دانشگاهی با مبالغ رسمی ۲۰۲۶.",
            "meta_keywords": "بورسیه ارشد چین, CSC master, فاند ارشد چین",
        },
    )
    _programs(
        master,
        Scholarship,
        [
            {
                **common_csc,
                "slug": "csc-master",
                "program_key": "cn-csc",
                "name": "بورسیه دولتی چین (CSC) — ارشد",
                "coverage": "شهریه + خوابگاه + بیمه + ۳٬۰۰۰ یوان/ماه",
                "eligibility": (
                    "<p>زیر ۳۵ سال؛ مدرک کارشناسی؛ غیرچینی. "
                    "برنامه چینی‌زبان: HSK4؛ انگلیسی‌زبان: IELTS 6.0+.</p>"
                ),
                "deadlines": "ژانویه–آوریل (بسته به Type A/B و دانشگاه)",
                "min_gpa": Decimal("15.00"),
                "highlights": "کامل‌ترین بورسیه ارشد\n"
                "قابل ترکیب با پذیرش ۹۸۵/۲۱۱",
                "tags": "CSC, ارشد, دولتی",
                "is_featured": True,
                "order": 1,
            },
            {
                "slug": "csc-type-a-b",
                "program_key": "cn-csc-route",
                "name": "مسیر Type A و Type B",
                "provider": "CSC",
                "coverage": "همان پوشش CSC — تفاوت در کانال اپلای",
                "eligibility": (
                    "<p><strong>Type A:</strong> از طریق مرکز CSC در کشور مبدأ (مثلاً سفارت).<br>"
                    "<strong>Type B:</strong> مستقیم از پورتال دانشگاه میزبان.</p>"
                ),
                "deadlines": "Type A زودتر (دی–اسفند)؛ Type B تا بهار",
                "official_url": "https://www.campuschina.org/content/details3_74775.html",
                "min_gpa": None,
                "lang_requirement": "مطابق برنامه",
                "highlights": "انتخاب مسیر اشتباه = رد\n"
                "ایران: معمولاً Type A از سفارت",
                "tags": "CSC, راهنما",
                "is_featured": False,
                "order": 2,
            },
            {
                "slug": "provincial-master",
                "program_key": "cn-provincial",
                "name": "بورسیه استانی (ارشد)",
                "provider": "دولت استانی",
                "coverage": "شهریه جزئی + مقرری",
                "eligibility": "<p>گزینه جایگزین یا مکمل CSC در استان‌های کم‌رقابت‌تر.</p>",
                "deadlines": "بهار",
                "official_url": OFFICIAL_URL_BY_SLUG["provincial-master"],
                "min_gpa": Decimal("14.00"),
                "lang_requirement": "HSK/IELTS",
                "highlights": "رقابت کمتر\n"
                "مناسب پرونده خوب نه عالی",
                "tags": "استانی, ارشد",
                "is_featured": False,
                "order": 3,
            },
        ],
    )

    # ─── دکتری ───
    phd = _guide(
        Guide,
        country,
        "phd",
        {
            "headline": "بورسیه دکتری چین — CSC و فاند پژوهشی",
            "intro": (
                "دکتری با CSC شامل ۳٬۵۰۰ یوان/ماه است. "
                "پذیرش اغلب منوط به هم‌راستایی با استاد و طرح تحقیقاتی است."
            ),
            "overview": (
                "<p>مقرری دکتری CSC: <strong>۳٬۵۰۰ یوان/ماه</strong>. "
                "برای رشته‌های پزشکی و برخی آزمایشگاهی مبلغ ممکن است بالاتر باشد.</p>"
            ),
            "application_guide": (
                "<ol>"
                "<li>ایمیل به استاد با CV و طرح کوتاه (۲–۳ صفحه).</li>"
                "<li>نامه Pre-admission یا دعوت استاد.</li>"
                "<li>ثبت در campuschina و ارسال مدارک به سفارت.</li>"
                "</ol>"
            ),
            "search_keywords": "بورسیه دکتری چین, CSC PhD, 3500 yuan, فاند دکتری چین",
            "meta_title": "بورسیه دکتری چین ۲۰۲۶ | CSC ۳۵۰۰ یوان/ماه",
            "meta_description": "راهنمای فاند دکتری چین: CSC، CAS-TWAS و بورسیه دانشگاهی با مقرری رسمی.",
            "meta_keywords": "بورسیه دکتری چین, CSC PhD, فاند دکتری",
        },
    )
    _programs(
        phd,
        Scholarship,
        [
            {
                **common_csc,
                "slug": "csc-phd",
                "program_key": "cn-csc",
                "name": "بورسیه دولتی چین (CSC) — دکتری",
                "coverage": "شهریه + خوابگاه + بیمه + ۳٬۵۰۰ یوان/ماه",
                "eligibility": (
                    "<p>زیر ۴۰ سال؛ کارشناسی ارشد؛ طرح تحقیق و تماس استاد. "
                    "دو توصیه‌نامه پروفسور.</p>"
                ),
                "deadlines": "دی–فروردین (Type A/B)",
                "min_gpa": Decimal("15.50"),
                "highlights": "بالاترین مقرری CSC\n"
                "مناسب مسیر آکادمیک",
                "tags": "CSC, دکتری",
                "is_featured": True,
                "order": 1,
            },
            {
                "slug": "cas-twas",
                "program_key": "cn-cas-twas",
                "name": "CAS-TWAS President's Fellowship",
                "provider": "Chinese Academy of Sciences + TWAS",
                "coverage": "شهریه + سفر + مقرری دکتری (سطح CSC یا بالاتر)",
                "eligibility": (
                    "<p>برای دانشجویان کشورهای در حال توسعه در مؤسسات CAS. "
                    "رشته‌های STEM؛ استاد CAS الزامی.</p>"
                ),
                "deadlines": "معمولاً فروردین–اردیبهشت",
                "official_url": "https://twas.org/opportunity/cas-twas-presidents-phd-fellowship-programme",
                "min_gpa": Decimal("16.00"),
                "lang_requirement": "انگلیسی یا چینی",
                "highlights": "برای پژوهش در آکادمی علوم چین\n"
                "رقابتی در سطح جهانی",
                "tags": "CAS, دکتری, STEM",
                "is_featured": True,
                "order": 2,
            },
            {
                "slug": "university-phd-fellowship",
                "program_key": "cn-university-phd",
                "name": "فاند دکتری دانشگاه (University Fellowship)",
                "provider": "دانشگاه‌های ۹۸۵/۲۱۱",
                "coverage": "شهریه + خوابگاه + ۲٬۵۰۰–۳٬۵۰۰ یوان/ماه",
                "eligibility": "<p>جایگزین CSC در برخی دانشگاه‌ها؛ تابع بودجه دانشکده.</p>",
                "deadlines": "متفاوت",
                "official_url": OFFICIAL_URL_BY_SLUG["university-phd-fellowship"],
                "min_gpa": Decimal("15.00"),
                "lang_requirement": "مطابق استاد",
                "highlights": "مسیر موازی CSC\n"
                "برای استاد با گرنت",
                "tags": "دانشگاهی, دکتری",
                "is_featured": False,
                "order": 3,
            },
        ],
    )


def seed_spain_all(StudyCountry, Guide, Scholarship) -> None:
    country = StudyCountry.objects.filter(code="spain").first()
    if not country:
        return

    country.scholarship_info = (
        "<p>اسپانیا بورسیه‌های دولتی (MAEC-AECID)، بنیاد La Caixa و "
        "بورسیه merit دانشگاهی دارد. "
        "<strong>توجه:</strong> در convocatoriaهای اخیر MAEC-AECID، "
        "ایران معمولاً در فهرست کشورهای واجد شرایط نیست — "
        "فهرست سالانه را در aecid.es بررسی کنید.</p>"
        "<p><a href=\"/کشور/spain/بورسیه/?target_degree=master\">ارشد</a> · "
        "<a href=\"/کشور/spain/بورسیه/?target_degree=phd\">دکتری</a> · "
        "<a href=\"/کشور/spain/بورسیه/?target_degree=bachelor\">کارشناسی</a></p>"
    )
    country.save(update_fields=["scholarship_info"])

    # ─── کارشناسی ───
    bachelor = _guide(
        Guide,
        country,
        "bachelor",
        {
            "headline": "بورسیه کارشناسی اسپانیا برای دانشجویان بین‌المللی",
            "intro": (
                "بورسیه کارشناسی در اسپانیا عمدتاً merit دانشگاهی و منطقه‌ای است؛ "
                "برخلاف چین بورسیه دولتی تمام‌هزینه محدودتر است. "
                "هزینه زندگی و شهریه دولتی نسبت به آلمان و بریتانیا پایین‌تر است."
            ),
            "overview": (
                "<ul>"
                "<li>بورسیه‌های دانشگاه دولتی بر اساس معدل ورود</li>"
                "<li>تخفیف شهریه در دانشگاه‌های خصوصی</li>"
                "<li>برنامه‌های منطقه‌ای (بورس، مادرید، کاتالونیا)</li>"
                "</ul>"
            ),
            "application_guide": (
                "<ol>"
                "<li>از UNEDasiss یا مستقیم به دانشگاه اسپانیایی اپلای کنید.</li>"
                "<li>فرم بورسیه merit هر دانشگاه را جدا بخوانید.</li>"
                "<li>برای برنامه اسپانیایی‌زبان DELE B2 هدف بگیرید.</li>"
                "</ol>"
            ),
            "search_keywords": "بورسیه کارشناسی اسپانیا, تحصیل اسپانیا, scholarship spain bachelor",
            "meta_title": "بورسیه کارشناسی اسپانیا ۲۰۲۶ | merit و منطقه‌ای",
            "meta_description": "راهنمای بورسیه لیسانس اسپانیا: بورسیه دانشگاهی، منطقه‌ای و نکات اپلای.",
            "meta_keywords": "بورسیه اسپانیا, کارشناسی اسپانیا, scholarship spain",
        },
    )
    _programs(
        bachelor,
        Scholarship,
        [
            {
                "slug": "university-merit-bachelor",
                "program_key": "es-merit",
                "name": "بورسیه merit دانشگاه‌های دولتی",
                "provider": "دانشگاه‌های اسپانیا",
                "coverage": "تا ۵۰٪ شهریه یا کمک‌هزینه سالانه",
                "eligibility": (
                    "<p>بر اساس نمرات پذیرش و سوابق تحصیلی؛ "
                    "هر دانشگاه (Complutense، Barcelona، Granada و…) شرایط جدا دارد.</p>"
                ),
                "deadlines": "خرداد–تیر (برای ورود پاییز)",
                "official_url": OFFICIAL_URL_BY_SLUG["university-merit-bachelor"],
                "min_gpa": Decimal("15.00"),
                "lang_requirement": "DELE B2 یا IELTS 6.0 برای انگلیسی‌زبان",
                "highlights": "رایج‌ترین مسیر کارشناسی\n"
                "رقابت در سطح هر دانشگاه",
                "tags": "کارشناسی, merit",
                "is_featured": True,
                "order": 1,
            },
            {
                "slug": "regional-bachelor",
                "program_key": "es-regional",
                "name": "کمک‌هزینه‌های منطقه‌ای",
                "provider": "دولت خودمختار (بورس، کاتالونیا و…)",
                "coverage": "شهریه جزئی تا خوابگاه",
                "eligibility": "<p>بر اساس درآمد خانوار در برخی مناطق؛ برای مقیم همان منطقه.</p>",
                "deadlines": "تابستان–پاییز",
                "official_url": OFFICIAL_URL_BY_SLUG["regional-bachelor"],
                "min_gpa": Decimal("14.00"),
                "lang_requirement": "اسپانیایی",
                "highlights": "وابسته به اقامت/منطقه\n"
                "برای بودجه محدود",
                "tags": "منطقه‌ای, کارشناسی",
                "is_featured": False,
                "order": 2,
            },
        ],
    )

    # ─── ارشد ───
    master = _guide(
        Guide,
        country,
        "master",
        {
            "headline": "بورسیه ارشد اسپانیا — MAEC، La Caixa و دانشگاهی",
            "intro": (
                "ارشد در اسپانیا با بورسیه MAEC-AECID (برای کشورهای منتخب)، "
                "La Caixa و بورسیه‌های جذب استعداد دانشگاه‌ها (مثل Jaén، UC3M) "
                "قابل تأمین مالی است."
            ),
            "overview": (
                "<p><strong>مهم برای ایرانیان:</strong> در فهرست ۲۰۲۵/۲۰۲۶ MAEC-AECID "
                "کشورهای آسیا محدود به فیلیپین و اوکراین اعلام شده — "
                "ایران معمولاً واجد شرایط نیست. بورسیه دانشگاهی و La Caixa گزینه اصلی است.</p>"
            ),
            "application_guide": (
                "<ol>"
                "<li>فهرست کشورها را در buscador-becas aecid.es چک کنید.</li>"
                "<li>برای MAEC: IELTS 5.5 (حداقل 5 در هر بخش) یا DELE B2.</li>"
                "<li>بورسیه Talent Attraction دانشگاه Jaén را برای بین‌المللی در نظر بگیرید.</li>"
                "</ol>"
            ),
            "search_keywords": "بورسیه ارشد اسپانیا, MAEC-AECID, La Caixa, master spain",
            "meta_title": "بورسیه ارشد اسپانیا ۲۰۲۶ | MAEC، La Caixa و دانشگاهی",
            "meta_description": "راهنمای بورسیه ارشد اسپانیا با مبالغ واقعی، واجد شرایط بودن ایرانیان و لینک رسمی.",
            "meta_keywords": "بورسیه ارشد اسپانیا, MAEC, AECID, master scholarship spain",
        },
    )
    _programs(
        master,
        Scholarship,
        [
            {
                "slug": "maec-aecid-master",
                "program_key": "es-maec",
                "name": "بورسیه MAEC-AECID (ارشد)",
                "provider": "وزارت امور خارجه اسپانیا / AECID",
                "coverage": "شهریه + بیمه + ۶۰۰–۱٬۲۰۰ یورو/ماه + پرواز رفت‌وبرگشت",
                "eligibility": (
                    "<p>شهروندان کشورهای در حال توسعه در فهرش سالانه AECID "
                    "(آمریکای لاتین، آفریقا، خاورمیانه محدود، آسیا محدود). "
                    "<strong>ایران در فهرست ۲۰۲۵/۲۰۲۶ نیست</strong> — هر سال بررسی کنید.</p>"
                ),
                "deadlines": "معمولاً بهمن–اسفند برای سال تحصیلی بعد",
                "official_url": "https://www.aecid.es/buscador-becas-y-lectorados",
                "min_gpa": Decimal("15.50"),
                "lang_requirement": "IELTS 5.5 (کل) یا DELE B2 برای اسپانیایی",
                "highlights": "تمام‌هزینه برای واجد شرایط\n"
                "~۹۰ بورسیه ارشد در سال",
                "tags": "دولتی, ارشد",
                "is_featured": True,
                "order": 1,
            },
            {
                "slug": "ujaen-talent-master",
                "program_key": "es-ujaen-talent",
                "name": "Talent Attraction Scholarships (University of Jaén)",
                "provider": "University of Jaén",
                "coverage": "نوع A: ۱۰۰٪ شهریه + ۳٬۱۹۰ یورو/سال | نوع B: ۱۰۰٪ ثبت‌نام",
                "eligibility": (
                    "<p>۳۰ بورسیه برای دانشجویان بین‌المللی ممتاز ارشد (۲۰۲۵/۲۶). "
                    "فهرست کشورهای واجد شرایط در سایت UJA — "
                    "ایران در دوره‌های قبل در فهرست بود؛ سال جاری را چک کنید.</p>"
                ),
                "deadlines": "حدود ۱۵ فوریه (برای سال بعد در سایت ujaen.es)",
                "official_url": OFFICIAL_URL_BY_SLUG["ujaen-talent-master"],
                "min_gpa": Decimal("16.00"),
                "lang_requirement": "بسته به برنامه ارشد",
                "highlights": "مبلغ مشخص ارویی\n"
                "مناسب پرونده قوی",
                "tags": "ارشد, دانشگاهی",
                "is_featured": True,
                "order": 2,
            },
            {
                "slug": "la-caixa-master",
                "program_key": "es-la-caixa",
                "name": "Fundación la Caixa — Postgraduate Fellowships",
                "provider": "Fundación la Caixa",
                "coverage": "تا ۱۸٬۰۰۰ یورو شهریه + مقرری + سفر و بیمه",
                "eligibility": (
                    "<p>حدود ۱۲۰ فلوشیپ ارشد/دکتری در اسپانیا، پرتغال و اروپا. "
                    "باز برای شهروندان سراسر جهان در برخی فراخوان‌ها.</p>"
                ),
                "deadlines": "معمولاً بهمن–اسفند",
                "official_url": OFFICIAL_URL_BY_SLUG["la-caixa-master"],
                "min_gpa": Decimal("16.50"),
                "lang_requirement": "انگلیسی یا اسپانیایی",
                "highlights": "بنیاد معتبر خصوصی\n"
                "رقابت بالا",
                "tags": "ارشد, la Caixa",
                "is_featured": False,
                "order": 3,
            },
            {
                "slug": "upf-merit-master",
                "program_key": "es-upf-merit",
                "name": "Merit Based Scholarship (UPF Barcelona)",
                "provider": "UPF Barcelona School of Management",
                "coverage": "۲۵٪ شهریه (+ تا ۲۵٪ دیگر بر اساس نیاز مالی)",
                "eligibility": (
                    "<p>GPA حداقل ۳.۰ از ۴.۰؛ برای برنامه‌های MBA و ارشد مدیریت.</p>"
                ),
                "deadlines": "هم‌زمان اپلای برنامه",
                "official_url": "https://www.bsm.upf.edu/en/talent-scholarship",
                "min_gpa": Decimal("15.00"),
                "lang_requirement": "IELTS مطابق برنامه",
                "highlights": "تا ۵۰٪ شهریه\n"
                "برنامه انگلیسی‌زبان",
                "tags": "ارشد, merit",
                "is_featured": False,
                "order": 4,
            },
        ],
    )

    # ─── دکتری ───
    phd = _guide(
        Guide,
        country,
        "phd",
        {
            "headline": "بورسیه و فاند دکتری اسپانیا",
            "intro": (
                "دکتری در اسپانیا اغلب با قرارداد پژوهشی (FPI) یا "
                "فلوشیپ بنیاد La Caixa INPhINIT تأمین می‌شود — "
                "هر دو برای ملیت‌های مختلف باز هستند."
            ),
            "overview": (
                "<ul>"
                "<li><strong>INPhINIT Incoming:</strong> ~۲۶٬۰۰۰–۲۹٬۰۰۰ یورو ناخالص/سال، همه ملیت‌ها</li>"
                "<li><strong>FPI (دانشگاه):</strong> قرارداد دکتری دولتی اسپانیا</li>"
                "<li><strong>MAEC دکتری:</strong> مشابه ارشد — فهرست کشور محدود</li>"
                "</ul>"
            ),
            "application_guide": (
                "<ol>"
                "<li>با گروه تحقیقاتی تماس بگیرید.</li>"
                "<li>INPhINIT: ژانویه–فوریه deadline.</li>"
                "<li>FPI: فراخوان بهار دانشگاه.</li>"
                "</ol>"
            ),
            "search_keywords": "بورسیه دکتری اسپانیا, INPhINIT, FPI, PhD spain",
            "meta_title": "بورسیه دکتری اسپانیا ۲۰۲۶ | INPhINIT و FPI",
            "meta_description": "راهنمای فاند دکتری اسپانیا: La Caixa INPhINIT، FPI و MAEC با شرایط دقیق.",
            "meta_keywords": "بورسیه دکتری اسپانیا, INPhINIT, PhD funding spain",
        },
    )
    _programs(
        phd,
        Scholarship,
        [
            {
                "slug": "inphinit-incoming",
                "program_key": "es-inphinit",
                "name": "la Caixa INPhINIT — Incoming (دکتری)",
                "provider": "Fundación la Caixa",
                "coverage": "حدود ۲۶٬۰۰۰–۲۹٬۰۰۰ یورو ناخالص/سال + کمک اسکان و کنفرانس",
                "eligibility": (
                    "<p>۳۵ فلوشیپ سالانه برای دکتری در مراکز تحقیقاتی اسپانیا. "
                    "<strong>همه ملیت‌ها</strong>؛ حداکثر ۴ سال سابقه تحقیقات پس از کارشناسی.</p>"
                ),
                "deadlines": "معمولاً ژانویه–فوریه",
                "official_url": "https://inphinitlacaixa.org/en/inphinit-incoming-doctoral-fellowships",
                "min_gpa": Decimal("16.50"),
                "lang_requirement": "انگلیسی",
                "highlights": "بهترین گزینه بین‌المللی برای PhD\n"
                "بدون محدودیت MAEC",
                "tags": "دکتری, la Caixa",
                "is_featured": True,
                "order": 1,
            },
            {
                "slug": "fpi-spain",
                "program_key": "es-fpi",
                "name": "FPI — قرارداد دکتری دانشگاهی",
                "provider": "دانشگاه‌های اسپانیا / وزارت علوم",
                "coverage": "حدود ۱۶٬۲۵۰ یورو ناخالص/سال + بیمه اجتماعی",
                "eligibility": (
                    "<p>قرارداد کار پژوهشی ۴ ساله؛ نیاز به پذیرش در برنامه دکتری "
                    "و گروه تحقیقاتی. رقابت ملی و بین‌المللی.</p>"
                ),
                "deadlines": "فراخوان بهار (معمولاً مارس–آوریل)",
                "official_url": "https://www.csic.es/es/formacion-y-empleo/formacion-de-personal-investigador/doctorado/contratos-predoctorales",
                "min_gpa": Decimal("15.50"),
                "lang_requirement": "اسپانیایی یا انگلیسی بسته به گروه",
                "highlights": "مسیر استاندارد دکتری در اسپانیا\n"
                "قرارداد قانونی با حقوق",
                "tags": "FPI, دکتری",
                "is_featured": True,
                "order": 2,
            },
            {
                "slug": "maec-aecid-phd",
                "program_key": "es-maec-phd",
                "name": "MAEC-AECID (دکتری)",
                "provider": "AECID",
                "coverage": "شهریه + مقرری + بیمه + سفر",
                "eligibility": (
                    "<p>مشابه ارشد؛ فقط کشورهای فهرش سالانه. "
                    "ایران در convocatoria اخیر معمولاً نیست.</p>"
                ),
                "deadlines": "بهمن–اسفند",
                "official_url": "https://www.aecid.es/buscador-becas-y-lectorados",
                "min_gpa": Decimal("16.00"),
                "lang_requirement": "DELE B2 یا IELTS 5.5",
                "highlights": "تمام‌هزینه اگر واجد شرایط\n"
                "چک سالانه فهرست کشور",
                "tags": "دولتی, دکتری",
                "is_featured": False,
                "order": 3,
            },
        ],
    )


def seed_all_extended(apps) -> None:
    StudyCountry = apps.get_model("core", "StudyCountry")
    Guide = apps.get_model("core", "CountryScholarshipGuide")
    Scholarship = apps.get_model("core", "CountryScholarship")
    seed_canada_graduate(StudyCountry, Guide, Scholarship)
    seed_china_all(StudyCountry, Guide, Scholarship)
    seed_spain_all(StudyCountry, Guide, Scholarship)
    refresh_scholarship_official_urls(apps)


def unseed_extended(apps) -> None:
    Guide = apps.get_model("core", "CountryScholarshipGuide")
    StudyCountry = apps.get_model("core", "StudyCountry")
    codes = ["canada", "china", "spain"]
    degrees = ["master", "phd", "bachelor"]
    for code in codes:
        country = StudyCountry.objects.filter(code=code).first()
        if not country:
            continue
        for deg in degrees:
            if code == "canada" and deg == "bachelor":
                continue
            Guide.objects.filter(country=country, target_degree=deg).delete()
