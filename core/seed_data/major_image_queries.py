"""
نگاشت عنوان فارسی رشته → عبارت جستجوی ویکی‌پدیا (انگلیسی) برای تصویر مرتبط.

اولویت: (عنوان، کشور) → عنوان دقیق → قوانین از طولانی‌ترین به کوتاه‌ترین → استخراج کلیدواژه.
"""
from __future__ import annotations

import hashlib
import re
import unicodedata

# جستجوی اختصاصی برای ترکیب (عنوان، کشور)
COUNTRY_SPECIFIC_QUERIES: dict[tuple[str, str], str] = {
    ("زبان و ادبیات اسپانیایی", "spain"): "Spanish language",
    ("زبان چینی", "china"): "Chinese language",
    ("پزشکی عمومی (MBBS)", "china"): "Bachelor of Medicine, Bachelor of Surgery",
    ("طب سنتی چین", "china"): "Traditional Chinese medicine",
    ("مهندسی نساجی و پوشاک", "china"): "Textile engineering",
    ("مدیریت هتل و مهمان‌نوازی", "spain"): "Hospitality management",
    ("گردشگری", "spain"): "Tourism",
    ("هتلداری", "spain"): "Hotel management",
    ("مهندسی منابع طبیعی و جنگل", "canada"): "Forestry",
    ("مدیریت بین‌الملل", "canada"): "International business",
}

# عنوان دقیق → مقاله ویکی‌پدیا
EXACT_WIKI_QUERIES: dict[str, str] = {
    "آمار": "Statistics",
    "آمار زیستی": "Biostatistics",
    "آموزش ابتدایی": "Primary education",
    "آموزش ریاضی": "Mathematics education",
    "آموزش زبان انگلیسی": "English language education",
    "آموزش علوم تجربی": "Science education",
    "آموزش هنر": "Art education",
    "آموزش کودکان استثنایی": "Special education",
    "آموزش و پرورش ابتدایی": "Primary education",
    "آموزش و پرورش پیش‌دبستانی": "Early childhood education",
    "آهنگسازی": "Musical composition",
    "اتاق عمل": "Operating theater",
    "ادبیات انگلیسی": "English literature",
    "ادبیات فارسی": "Persian literature",
    "ادبیات عرب": "Arabic literature",
    "ارتوز و پروتز": "Orthotics and prosthetics",
    "ارگونومی": "Ergonomics",
    "اقتصاد": "Economics",
    "اقتصاد بین‌الملل": "International economics",
    "اقتصاد کشاورزی": "Agricultural economics",
    "امنیت ملی": "National security",
    "امنیت سایبری": "Cybersecurity",
    "امور بانکی": "Banking",
    "امور بین‌الملل": "International relations",
    "امور تربیتی": "Educational sciences",
    "امور شهری و محیط زیست": "Urban planning",
    "انرژی": "Energy engineering",
    "اپیدمیولوژی": "Epidemiology",
    "ایمنی‌شناسی": "Immunology",
    "باستان‌شناسی": "Archaeology",
    "بازاریابی": "Marketing",
    "بهداشت عمومی": "Public health",
    "برنامه‌ریزی شهری": "Urban planning",
    "برنامه‌ریزی سیستم‌های اقتصادی": "Economic planning",
    "بیمارستان‌داری": "Hospital administration",
    "بیوتکنولوژی": "Biotechnology",
    "بیولوژی": "Biology",
    "بیولوژی سلولی مولکولی": "Cell biology",
    "بیومکانیک": "Biomechanics",
    "بیومدیکال": "Biomedical engineering",
    "بیومهندسی": "Bioengineering",
    "بیوانفورماتیک": "Bioinformatics",
    "پرستاری": "Nursing",
    "پزشکی": "Medicine",
    "پزشکی اجتماعی": "Social medicine",
    "پزشکی ورزشی": "Sports medicine",
    "پلیمر": "Polymer science",
    "تاریخ": "History",
    "تاریخ اسلام": "Islamic history",
    "تربیت بدنی": "Physical education",
    "تربیت بدنی و علوم ورزشی": "Sports science",
    "ترجمه": "Translation studies",
    "تغذیه": "Nutrition",
    "تکنولوژی آموزشی": "Educational technology",
    "تکنولوژی اطلاعات": "Information technology",
    "تکنولوژی غذایی": "Food technology",
    "تکنولوژی نفت": "Petroleum technology",
    "تکنولوژی‌های نوین پزشکی": "Medical technology",
    "جامعه‌شناسی": "Sociology",
    "جغرافیا": "Geography",
    "جغرافیا و برنامه‌ریزی شهری": "Urban geography",
    "جغرافیا و برنامه‌ریزی روستایی": "Rural geography",
    "جمعیت‌شناسی": "Demography",
    "حسابداری": "Accounting",
    "حقوق": "Law",
    "حقوق بین‌الملل": "International law",
    "حقوق جزا و جرم‌شناسی": "Criminal law",
    "حقوق تجارت بین‌الملل": "Commercial law",
    "حفاظت محیط زیست": "Environmental protection",
    "حفاظت و مرمت آثار تاریخی": "Conservation and restoration",
    "خبرنگاری": "Journalism",
    "خاک‌شناسی": "Soil science",
    "داروسازی": "Pharmacy",
    "داروسازی بالینی": "Clinical pharmacy",
    "دامپزشکی": "Veterinary medicine",
    "دندانپزشکی": "Dentistry",
    "دندانپزشکی عمومی": "Dentistry",
    "راه و ساختمان": "Civil engineering",
    "روان‌شناسی": "Psychology",
    "روان‌شناسی بالینی": "Clinical psychology",
    "روان‌شناسی تربیتی": "Educational psychology",
    "روان‌شناسی صنعتی و سازمانی": "Industrial and organizational psychology",
    "روان‌شناسی شناختی": "Cognitive psychology",
    "روابط عمومی": "Public relations",
    "ریاضی": "Mathematics",
    "ریاضی کاربردی": "Applied mathematics",
    "زبان و ادبیات انگلیسی": "English studies",
    "زبان و ادبیات آلمانی": "German studies",
    "زبان و ادبیات فرانسه": "French studies",
    "زبان‌شناسی": "Linguistics",
    "زبان‌شناسی کاربردی": "Applied linguistics",
    "زمین‌شناسی": "Geology",
    "زیست‌شناسی": "Biology",
    "زیست‌شناسی دریا": "Marine biology",
    "زیست‌فناوری": "Biotechnology",
    "زیست‌فناوری پزشکی": "Medical biotechnology",
    "علوم اعصاب": "Neuroscience",
    "علوم داده": "Data science",
    "علوم شناختی": "Cognitive science",
    "ساختمان": "Building engineering",
    "ساختمان‌های آبی": "Hydraulic engineering",
    "سنجش از دور و GIS": "Remote sensing",
    "سیاست‌گذاری عمومی": "Public policy",
    "سینما": "Filmmaking",
    "شهرسازی": "Urban planning",
    "شیلات": "Fisheries science",
    "شیمی": "Chemistry",
    "شیمی آلی": "Organic chemistry",
    "شیمی تجزیه": "Analytical chemistry",
    "شیمی فیزیک": "Physical chemistry",
    "شیمی کاربردی": "Applied chemistry",
    "صنایع": "Industrial engineering",
    "صنایع غذایی": "Food engineering",
    "صنایع نفت": "Petroleum engineering",
    "طراحی صنعتی": "Industrial design",
    "طراحی شهری": "Urban design",
    "طراحی لباس": "Fashion design",
    "طراحی گرافیک": "Graphic design",
    "طراحی محیط": "Environmental design",
    "طراحی بازی و رسانه‌های تعاملی": "Game design",
    "علوم اجتماعی": "Social science",
    "علوم اقتصادی": "Economics",
    "علوم تربیتی": "Education",
    "علوم تربیتی — برنامه‌ریزی آموزشی": "Curriculum studies",
    "علوم تربیتی — مدیریت آموزشی": "Educational administration",
    "علوم تربیتی — مشاوره": "School counseling",
    "علوم سیاسی": "Political science",
    "علوم قرآن و حدیث": "Islamic studies",
    "علوم قضایی": "Forensic science",
    "علوم کتابداری و اطلاع‌رسانی": "Library science",
    "علوم کامپیوتر": "Computer science",
    "علوم کامپیوتر — نرم‌افزار": "Software engineering",
    "علوم کامپیوتر — سخت‌افزار": "Computer hardware",
    "علوم کامپیوتر — هوش مصنوعی": "Artificial intelligence",
    "علوم کامپیوتر — امنیت اطلاعات": "Information security",
    "علوم کامپیوتر — شبکه": "Computer network",
    "علوم کشاورزی": "Agronomy",
    "علوم دامی": "Animal science",
    "علوم زیستی": "Biology",
    "علوم ارتباطات": "Communication studies",
    "علوم و مهندسی غذایی": "Food science",
    "فقه و مبانی حقوق اسلامی": "Islamic jurisprudence",
    "فلسفه": "Philosophy",
    "فلسفه و حکمت اسلامی": "Islamic philosophy",
    "فناوری اطلاعات": "Information technology",
    "فناوری اطلاعات سلامت": "Health informatics",
    "فناوری نانو": "Nanotechnology",
    "فیزیوتراپی": "Physical therapy",
    "فیزیک": "Physics",
    "فیزیک کاربردی": "Applied physics",
    "فیزیک مهندسی": "Engineering physics",
    "فیزیک هسته‌ای": "Nuclear physics",
    "قضاوت": "Judiciary",
    "کاردرمانی": "Occupational therapy",
    "کامپیوتر": "Computer science",
    "کامپیوتر — نرم‌افزار": "Software engineering",
    "کامپیوتر — سخت‌افزار": "Computer hardware",
    "کامپیوتر — شبکه": "Computer network",
    "کامپیوتر — هوش مصنوعی": "Artificial intelligence",
    "کامپیوتر — امنیت": "Computer security",
    "کامپیوتر — مهندسی نرم‌افزار": "Software engineering",
    "کشاورزی": "Agriculture",
    "کشاورزی — زراعت": "Crop science",
    "کشاورزی — باغبانی": "Horticulture",
    "کشاورزی — علوم دامی": "Animal science",
    "کشاورزی — منابع طبیعی": "Natural resource management",
    "گرافیک": "Graphic design",
    "مددکاری اجتماعی": "Social work",
    "مدیریت": "Management",
    "مدیریت بازرگانی": "Business administration",
    "مدیریت بیمه": "Insurance",
    "مدیریت صنعتی": "Industrial management",
    "مدیریت مالی": "Finance",
    "مدیریت گردشگری": "Tourism management",
    "مدیریت دولتی": "Public administration",
    "مدیریت کشاورزی": "Agribusiness",
    "مدیریت بیمارستان": "Health administration",
    "مدیریت زنجیره تأمین": "Supply chain management",
    "مدیریت منابع انسانی": "Human resource management",
    "MBA و مدیریت کسب‌وکار": "Master of Business Administration",
    "مطالعات بین‌فرهنگی": "Intercultural communication",
    "معماری": "Architecture",
    "معماری داخلی": "Interior design",
    "معماری منظر": "Landscape architecture",
    "مهندسی آب": "Water resources engineering",
    "مهندسی اپتیک و لیزر": "Optical engineering",
    "مهندسی پزشکی": "Biomedical engineering",
    "مهندسی پلیمر": "Polymer engineering",
    "مهندسی پتروشیمی": "Chemical engineering",
    "مهندسی نفت": "Petroleum engineering",
    "مهندسی نساجی": "Textile engineering",
    "مهندسی معدن": "Mining engineering",
    "مهندسی شهرسازی": "Urban engineering",
    "مهندسی عمران": "Civil engineering",
    "مهندسی راه و ساختمان": "Civil engineering",
    "مهندسی رباتیک": "Robotics",
    "مهندسی هوافضا": "Aerospace engineering",
    "مهندسی خودرو": "Automotive engineering",
    "مهندسی مکانیک": "Mechanical engineering",
    "مهندسی مکاترونیک": "Mechatronics",
    "مهندسی مواد و متالورژی": "Materials science",
    "مهندسی شیمی": "Chemical engineering",
    "مهندسی صنایع": "Industrial engineering",
    "مهندسی صنایع غذایی": "Food engineering",
    "مهندسی کشاورزی": "Agricultural engineering",
    "مهندسی منابع طبیعی": "Natural resource management",
    "مهندسی محیط زیست": "Environmental engineering",
    "مهندسی انرژی": "Energy engineering",
    "مهندسی برق": "Electrical engineering",
    "مهندسی برق — قدرت": "Power engineering",
    "مهندسی برق — الکترونیک": "Electronics",
    "مهندسی برق — مخابرات": "Telecommunications engineering",
    "مهندسی برق — کنترل": "Control engineering",
    "مهندسی کامپیوتر": "Computer engineering",
    "مهندسی کامپیوتر — نرم‌افزار": "Software engineering",
    "مهندسی کامپیوتر — سخت‌افزار": "Computer hardware",
    "مهندسی کامپیوتر — شبکه": "Computer network",
    "مهندسی کامپیوتر — هوش مصنوعی": "Artificial intelligence",
    "مهندسی کامپیوتر — امنیت": "Computer security",
    "مهندسی دریا": "Naval architecture",
    "مهندسی نرم‌افزار": "Software engineering",
    "مهندسی فناوری اطلاعات": "Information technology",
    "مهندسی حمل و نقل": "Transport engineering",
    "مهندسی ایمنی": "Safety engineering",
    "مهندسی بهداشت حرفه‌ای": "Occupational safety and health",
    "مهندسی بهداشت محیط": "Environmental health engineering",
    "مهندسی شیلات": "Fisheries engineering",
    "مهندسی جنگل": "Forestry",
    "مهندسی باغبانی": "Horticultural engineering",
    "مهندسی ماشین‌های کشاورزی": "Agricultural machinery",
    "هنرهای تجسمی": "Visual arts",
    "هنرهای نمایشی": "Performing arts",
    "هنرهای سنتی": "Traditional arts",
    "هنر اسلامی": "Islamic art",
    "هنرهای دیجیتال": "Digital art",
    "هوانوردی": "Aviation",
    "هوش مصنوعی": "Artificial intelligence",
    "عکاسی": "Photography",
    "موسیقی": "Music",
    "نمایش": "Theatre",
    "چاپ": "Printing",
    "صنایع دستی": "Handicraft",
    "فرش": "Carpet",
    "علوم ورزشی": "Sports science",
    "علوم ورزشی کاربردی": "Sports science",
    "علوم قضایی و خدمات حقوقی": "Criminal justice",
    "علوم محیطی": "Environmental science",
    "مشاوره": "Counseling psychology",
    "گردشگری": "Tourism",
    "هتلداری": "Hotel management",
}

# قوانین جزئی‌تر (از طولانی‌ترین عبارت)
_SUBSTRING_RULES: list[tuple[str, str]] = [
    ("هوش مصنوعی", "Artificial intelligence"),
    ("امنیت سایبری", "Cybersecurity"),
    ("علوم داده", "Data science"),
    ("زیست‌شناسی", "Biology"),
    ("زیست", "Biology"),
    ("پزشکی", "Medicine"),
    ("دندان", "Dentistry"),
    ("دارو", "Pharmacy"),
    ("پرستاری", "Nursing"),
    ("مهندسی کامپیوتر", "Computer engineering"),
    ("علوم کامپیوتر", "Computer science"),
    ("کامپیوتر", "Computer science"),
    ("مهندسی برق", "Electrical engineering"),
    ("مهندسی مکانیک", "Mechanical engineering"),
    ("مهندسی عمران", "Civil engineering"),
    ("مهندسی شیمی", "Chemical engineering"),
    ("مهندسی نفت", "Petroleum engineering"),
    ("مهندسی", "Engineering"),
    ("MBA", "Master of Business Administration"),
    ("مدیریت", "Management"),
    ("اقتصاد", "Economics"),
    ("حقوق", "Law"),
    ("معماری", "Architecture"),
    ("روان‌شناسی", "Psychology"),
    ("آموزش", "Education"),
    ("تربیتی", "Education"),
    ("هنر", "Art"),
    ("موسیقی", "Music"),
    ("زبان", "Linguistics"),
    ("ادبیات", "Literature"),
    ("کشاورزی", "Agriculture"),
    ("محیط زیست", "Environmental science"),
    ("شیمی", "Chemistry"),
    ("فیزیک", "Physics"),
    ("ریاضی", "Mathematics"),
    ("آمار", "Statistics"),
    ("جغرافیا", "Geography"),
    ("تاریخ", "History"),
    ("فلسفه", "Philosophy"),
    ("جامعه", "Sociology"),
    ("سیاسی", "Political science"),
    ("بازاریابی", "Marketing"),
    ("حسابداری", "Accounting"),
    ("بورسیه", "Scholarship"),
]

# برای تمایز بصری در جستجو وقتی مقاله دقیق پیدا نشد
COUNTRY_SEARCH_CONTEXT: dict[str, str] = {
    "canada": "Canada higher education",
    "spain": "Spain university",
    "china": "China university",
}

# عناوین ویکی که معمولاً تصویر نامرتبط دارند
_REJECTED_WIKI_TITLE_FRAGMENTS: tuple[str, ...] = (
    "disambiguation",
    "list of",
    "index of",
    "outline of",
    "category:",
    "template:",
    "wikipedia:",
    "flag of",
    "coat of arms",
    "map of",
    "emblem of",
)


def _normalize_title(title: str) -> str:
    t = (title or "").strip()
    t = unicodedata.normalize("NFKC", t)
    t = re.sub(r"\s+", " ", t)
    return t


def build_wikipedia_query(title: str, country: str = "") -> str:
    """
    عبارت جستجو برای ویکی‌پدیا — مرتبط با رشته و در صورت نیاز با زمینه کشور.
    """
    t = _normalize_title(title)
    if not t:
        return "Academic discipline"

    country = (country or "").strip().lower()
    key = (t, country)
    if key in COUNTRY_SPECIFIC_QUERIES:
        return COUNTRY_SPECIFIC_QUERIES[key]

    if t.startswith("دبیری "):
        base = t[6:].strip()
        if base in EXACT_WIKI_QUERIES:
            return EXACT_WIKI_QUERIES[base]
        return build_wikipedia_query(base, country)

    if t in EXACT_WIKI_QUERIES:
        return EXACT_WIKI_QUERIES[t]

    # حذف پسوند بعد از — و تطبیق مجدد
    if " — " in t:
        head = t.split(" — ", 1)[0].strip()
        if head in EXACT_WIKI_QUERIES:
            return EXACT_WIKI_QUERIES[head]
        tail = t.split(" — ", 1)[1].strip()
        for persian, english in _SUBSTRING_RULES:
            if persian in tail:
                return english

    for persian, english in _SUBSTRING_RULES:
        if persian in t:
            return english

    return "Academic discipline"


def _country_search_context(country: str) -> str:
    code = (country or "").strip().lower()
    if code in COUNTRY_SEARCH_CONTEXT:
        return COUNTRY_SEARCH_CONTEXT[code]
    if not code:
        return ""
    label = code.replace("_", " ").title()
    return f"{label} university"


def build_wikipedia_fallback_query(title: str, country: str = "") -> str:
    """جستجوی دوم با زمینه کشور برای تمایز تصویر بین مقاصد."""
    base = build_wikipedia_query(title, country)
    country = (country or "").strip().lower()
    ctx = _country_search_context(country)
    if ctx and base != "Academic discipline":
        return f"{base} {ctx}"
    if ctx:
        return ctx
    return base


def is_acceptable_wikipedia_title(wiki_title: str) -> bool:
    low = (wiki_title or "").lower()
    return not any(fragment in low for fragment in _REJECTED_WIKI_TITLE_FRAGMENTS)


# پسوندهای جستجوی تصویری — برای تنوع عکس بین رشته‌های مشابه
_MAJOR_VISUAL_SUFFIXES: tuple[str, ...] = (
    "university students classroom",
    "laboratory research",
    "lecture hall education",
    "professional practice",
    "campus study",
    "hands-on training",
    "modern facility",
    "field work",
    "equipment technology",
    "science education",
    "graduate students",
    "research center",
    "medical school",
    "engineering workshop",
    "library study",
    "internship program",
    "clinical training",
    "computer lab",
    "art studio",
    "business school",
    "science experiment",
    "hospital training",
    "architecture studio",
    "law school",
    "agriculture field",
)


def build_major_image_search_queries(
    title: str,
    country: str = "",
    *,
    slug: str = "",
    pk: int = 0,
) -> list[str]:
    """
    فهرست عبارات جستجو برای تصویر هر رشته — ترتیب بر اساس pk متفاوت می‌شود
    تا رشته‌های هم‌نام در کشورهای مختلف عکس یکسان نگیرند.
    """
    base = build_wikipedia_query(title, country)
    fallback = build_wikipedia_fallback_query(title, country)
    country_label = (country or "").strip().replace("_", " ").title()
    country_ctx = _country_search_context(country)
    seed = int(pk or 0) or int(hashlib.md5((slug or title).encode()).hexdigest()[:8], 16)

    queries: list[str] = []
    if base != "Academic discipline":
        queries.append(base)
    if fallback and fallback != base:
        queries.append(fallback)
    if base != "Academic discipline" and country_label:
        queries.append(f"{base} {country_label}")
        queries.append(f"{base} {country_label} university")
    if base != "Academic discipline" and country_ctx:
        queries.append(f"{base} {country_ctx}")

    suffixes = list(_MAJOR_VISUAL_SUFFIXES)
    start = seed % len(suffixes)
    rotated = suffixes[start:] + suffixes[:start]
    for suffix in rotated:
        if base != "Academic discipline":
            queries.append(f"{base} {suffix}")

    if base != "Academic discipline":
        queries.append(f"{base} workshop")
        queries.append(f"{base} internship")

    seen: set[str] = set()
    unique: list[str] = []
    for q in queries:
        q = re.sub(r"\s+", " ", (q or "").strip())
        key = q.lower()
        if q and key not in seen:
            seen.add(key)
            unique.append(q)
    return unique
