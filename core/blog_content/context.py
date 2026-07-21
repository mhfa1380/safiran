"""داده‌های زمینه کشورها و موسسه برای تولید محتوا."""
from __future__ import annotations

INSTITUTE = "موسسه سفیران آینده روشن"
EVAL_CTA_PATH = "/ارزیابی-مهاجرت/"
YEAR = "۲۰۲۶"

COUNTRY_PROFILES: dict[str, dict] = {
    "کانادا": {
        "en": "Canada",
        "visa": "Study Permit",
        "currency": "دلار کانادا (CAD)",
        "cities": "تورنتو، ونکوور، مونترال، اتاوا، کلگری",
        "unis": "University of Toronto، UBC، McGill، Waterloo",
        "tuition": "حدود ۱۵,۰۰۰ تا ۳۵,۰۰۰ دلار در سال (بسته به مقطع و استان)",
        "living": "حدود ۱,۲۰۰ تا ۲,۲۰۰ دلار در ماه برای اجاره و زندگی در شهرهای بزرگ",
        "work": "کار پاره‌وقت تا ۲۰ ساعت در هفته در دوران کلاس",
        "post_study": "PGWP و مسیر PNP / Express Entry",
        "lang": "آیلتس آکادمیک (معمولاً ۶.۵整体 یا ۶ در هر مهارت)",
    },
    "آلمان": {
        "en": "Germany",
        "visa": "ویزای ملی نوع D (دانشجویی)",
        "currency": "یورو (€)",
        "cities": "برلین، مونیخ، هامبورگ، فرانکفورت، کلن",
        "unis": "TU Munich، LMU، Heidelberg، RWTH Aachen",
        "tuition": "اغلب شهریه پایین در دانشگاه‌های دولتی (هزینه ترم ناچند صد یورو)",
        "living": "Blocked Account حدود ۱,۰۳۷ یورو در ماه (۲۰۲۶)",
        "work": "۱۲۰ روز کامل یا ۲۴۰ نیمه‌روز در سال",
        "post_study": "۱۸ ماه اقامت جستجوی کار پس از تحصیل",
        "lang": "آلمانی B2/C1 یا برنامه‌های انگلیسی‌زبان",
    },
    "اسپانیا": {
        "en": "Spain",
        "visa": "ویزای Type D دانشجویی",
        "currency": "یورو (€)",
        "cities": "مادرید، بارسلونا، والنسیا، سویا، بیلبائو",
        "unis": "Complutense، Barcelona، Autónoma de Madrid",
        "tuition": "شهریه دولتی معمولاً پایین‌تر از شمال اروپا",
        "living": "حدود ۹۰۰ تا ۱,۴۰۰ یورو در ماه بسته به شهر",
        "work": "کار پاره‌وقت با مجوز (معمولاً تا ۳۰ ساعت در هفته در دوره‌های مشخص)",
        "post_study": "مجوز اقامت برای جستجوی کار یا ادامه فعالیت",
        "lang": "اسپانیایی B2 یا برنامه انگلیسی‌زبان",
    },
    "چین": {
        "en": "China",
        "visa": "ویزای X1 / X2",
        "currency": "یوان (CNY)",
        "cities": "پکن، شانگهای، گوانگژو، شنژن، هانگژو",
        "unis": "Tsinghua، Peking، Fudan، Shanghai Jiao Tong",
        "tuition": "اغلب پایین‌تر از غرب؛ بورسیه CSC فرصت مهم",
        "living": "حدود ۳,۰۰۰ تا ۷,۰۰۰ یوان در ماه بسته به شهر",
        "work": "محدودیت‌های مشخص؛ بررسی قوانین دانشگاه و ویزا",
        "post_study": "بسته به employer و شهر؛ برنامه‌ریزی از قبل",
        "lang": "HSK برای چینی‌زبان؛ برخی برنامه‌ها انگلیسی",
    },
    "آمریکا": {
        "en": "USA",
        "visa": "ویزای F-1",
        "currency": "دلار آمریکا (USD)",
        "cities": "نیویورک، بوستون، لس‌آنجلس، سانفرانسیسکو، شیکاگو",
        "unis": "MIT، Stanford، UC Berkeley، NYU",
        "tuition": "شهریه متنوع؛ اغلب بالاتر از اروپای دولتی",
        "living": "۱,۵۰۰ تا ۲,۵۰۰+ دلار در ماه در شهرهای گران",
        "work": "CPT و OPT با قوانین مشخص",
        "post_study": "OPT تا ۱۲ ماه (بیشتر برای STEM)",
        "lang": "TOEFL / IELTS",
    },
    "فرانسه": {
        "en": "France",
        "visa": "ویزای Étudiant",
        "currency": "یورو (€)",
        "cities": "پاریس، لیون، تولوز، مونپلیه",
        "unis": "Sorbonne، Sciences Po، École Polytechnique",
        "tuition": "شهریه دولتی نسبتاً پایین برای بسیاری برنامه‌ها",
        "living": "CAF ممکن است بخشی از اجاره را پوشش دهد",
        "work": "۹۶۴ ساعت کار در سال",
        "post_study": "APS / titre de séjour",
        "lang": "فرانسوی B2 یا برنامه انگلیسی",
    },
    "هلند": {
        "en": "Netherlands",
        "visa": "MVV + residence permit",
        "currency": "یورو (€)",
        "cities": "آمستردام، روتردام، لاهه، اوترخت",
        "unis": "TU Delft، University of Amsterdam، Leiden",
        "tuition": "شهریه برای خارجی‌ها بالاتر از EU",
        "living": "حدود ۱,۰۰۰ تا ۱,۶۰۰ یورو در ماه",
        "work": "کار پاره‌وقت با محدودیت ساعت",
        "post_study": "Orientation Year برای فارغ‌التحصیلان",
        "lang": "IELTS ۶.۰–۶.۵ برای انگلیسی‌زبان",
    },
    "ایتالیا": {
        "en": "Italy",
        "visa": "ویزای Type D",
        "currency": "یورو (€)",
        "cities": "رم، میلان، بولونیا، فلورانس، تورین",
        "unis": "Bologna، Politecnico di Milano، Sapienza",
        "tuition": "شهریه بر اساس ISEE؛ اغلب مقرون‌به‌صرفه",
        "living": "۸۰۰ تا ۱,۳۰۰ یورو در ماه",
        "work": "۲۰ ساعت در هفته",
        "post_study": "转换 permesso di soggiorno برای کار",
        "lang": "ایتالیایی B2 یا انگلیسی",
    },
    "سوئد": {
        "en": "Sweden",
        "visa": "Residence permit for studies",
        "currency": "کرون سوئد (SEK)",
        "cities": "استکهلم، گوتنبرگ، مالمو، اوپسالا",
        "unis": "KTH، Lund، Uppsala، Stockholm University",
        "tuition": "برای خارجی‌ها؛ بورسیه SI",
        "living": "حدود ۹,۰۰۰–۱۲,۰۰۰ SEK در ماه",
        "work": "بدون محدودیت ساعت در دوران تحصیل (با رعایت تحصیل)",
        "post_study": "۶ ماه برای جستجوی کار",
        "lang": "IELTS ۶.۵ یا معافیت دانشگاه",
    },
    "فنلاند": {
        "en": "Finland",
        "visa": "Residence permit for studies",
        "currency": "یورو (€)",
        "cities": "هلسینکی، اسپو، تامپره، اوولو",
        "unis": "University of Helsinki، Aalto، Tampere",
        "tuition": "برای خارجی‌ها؛ بورسیه‌های دانشگاهی",
        "living": "حدود ۷۰۰–۱,۲۰۰ یورو در ماه",
        "work": "کار پاره‌وقت در حد مجاز",
        "post_study": "۱ سال residence permit برای جستجوی کار",
        "lang": "IELTS یا Finnish language course",
    },
    "اروپا": {
        "en": "Europe",
        "visa": "ویزای شنگن Type D / Type C",
        "currency": "یورو در بیشتر کشورها",
        "cities": "شهرهای دانشجویی متنوع",
        "unis": "دانشگاه‌های رتبه‌برتر در آلمان، هلند، فرانسه، سوئد",
        "tuition": "از رایگان/ارزان (آلمان، نروژ محدود) تا متوسط",
        "living": "بسته به کشور ۸۰۰ تا ۲,۰۰۰ یورو",
        "work": "قوانین متفاوت در هر کشور",
        "post_study": "مجوزهای کاری ملی متفاوت",
        "lang": "انگلیسی یا زبان محلی",
    },
}

DEFAULT_PROFILE: dict = {
    "en": "abroad",
    "visa": "ویزای تحصیلی",
    "currency": "ارز مقصد",
    "cities": "شهرهای دانشجویی",
    "unis": "دانشگاه‌های معتبر",
    "tuition": "متغیر",
    "living": "متغیر",
    "work": "طبق قوانین کشور",
    "post_study": "مجوز اقامت پس از تحصیل",
    "lang": "IELTS / زبان محلی",
}

GENERIC_PROFILE: dict = {
    "en": "study abroad",
    "visa": "ویزای تحصیلی",
    "currency": "ارز مقصد",
    "cities": "شهرهای محبوب دانشجویی",
    "unis": "دانشگاه‌های بین‌المللی",
    "tuition": "بسته به کشور و مقطع",
    "living": "بسته به شهر",
    "work": "کار دانشجویی در حد مجاز",
    "post_study": "اقامت پس از تحصیل",
    "lang": "مدرک زبان بین‌المللی",
}


def profile_for(category: str) -> dict:
    if category in COUNTRY_PROFILES:
        return COUNTRY_PROFILES[category]
    for key, val in COUNTRY_PROFILES.items():
        if key in (category or ""):
            return val
    if category in ("آموزشی", "مشکل‌محور", "هزینه", "مقایسه‌ای", "مهاجرت تحصیلی", "خدمات موسسه"):
        return GENERIC_PROFILE
    return DEFAULT_PROFILE
