# Seed تعرفه‌ها و مقرری کشورها

from django.db import migrations


LIVING_ALLOWANCE = [
    (1, "south-africa", "آفریقای جنوبی", 833, "EUR", "آفریقا"),
    (2, "germany-munich", "آلمان (مونیخ)", 1432, "EUR", "اروپا آلمان"),
    (3, "germany-other", "آلمان (سایر شهرها)", 1298, "EUR", "اروپا آلمان"),
    (4, "usa", "آمریکا", 1101, "USD", "آمریکا"),
    (5, "austria", "اتریش", 1155, "EUR", "اروپا"),
    (6, "spain", "اسپانیا", 1109, "EUR", "اروپا"),
    (7, "australia-sydney", "استرالیا (سیدنی)", 2150, "AUD", "اقیانوسیه"),
    (8, "australia-other", "استرالیا (سایر شهرها)", 2057, "AUD", "اقیانوسیه"),
    (9, "uk-group-a", "انگلستان (گروه الف)", 1001, "GBP", "انگلستان"),
    (10, "uk-group-b", "انگلستان (گروه ب)", 987, "GBP", "انگلستان"),
    (11, "uk-group-c", "انگلستان (گروه ج)", 863, "GBP", "انگلستان"),
    (12, "uk-london", "انگلستان (لندن)", 1100, "GBP", "انگلستان"),
    (13, "italy-major", "ایتالیا (رم، میلان، تورینو)", 1228, "EUR", "اروپا"),
    (14, "italy-other", "ایتالیا (سایر شهرها)", 1188, "EUR", "اروپا"),
    (15, "ireland", "ایرلند", 1445, "EUR", "اروپا"),
    (16, "brazil", "برزیل", 759, "EUR", "آمریکای لاتین"),
    (17, "belgium", "بلژیک", 1214, "EUR", "اروپا"),
    (18, "belgium-brussels", "بلژیک (بروکسل)", 1265, "EUR", "اروپا"),
    (19, "portugal", "پرتغال", 792, "EUR", "اروپا"),
    (20, "turkey", "ترکیه", 759, "EUR", "خاورمیانه"),
    (21, "china", "چین", 825, "EUR", "آسیا"),
    (22, "denmark", "دانمارک", 10834, "DKK", "اروپا"),
    (23, "russia-moscow", "روسیه (مسکو)", 1120, "EUR", "اروپا"),
    (24, "russia-other", "روسیه (سایر شهرها)", 900, "EUR", "اروپا"),
    (25, "belarus", "روسیه سفید (بلاروس)", 1017, "EUR", "اروپا"),
    (26, "new-zealand", "زلاندنو (نیوزلند)", 963, "EUR", "اقیانوسیه"),
    (27, "singapore", "سنگاپور", 759, "EUR", "آسیا"),
    (28, "sweden", "سوئد", 13540, "SEK", "اروپا"),
    (29, "switzerland", "سوئیس", 2732, "CHF", "اروپا"),
    (30, "france-paris", "فرانسه (پاریس)", 1340, "EUR", "اروپا"),
    (31, "france-other", "فرانسه (سایر شهرها)", 1095, "EUR", "اروپا"),
    (32, "finland", "فنلاند", 1109, "EUR", "اروپا"),
    (33, "south-korea", "کره جنوبی", 759, "EUR", "آسیا"),
    (34, "lebanon", "لبنان", 759, "EUR", "خاورمیانه"),
    (35, "mexico", "مکزیک", 759, "EUR", "آمریکای لاتین"),
    (36, "norway", "نروژ", 11088, "NOK", "اروپا"),
    (37, "netherlands", "هلند", 1360, "EUR", "اروپا"),
    (38, "india-major", "هند (دهلی و بمبئی)", 647, "EUR", "آسیا"),
    (39, "india-other", "هند (سایر شهرها)", 543, "EUR", "آسیا"),
    (40, "greece", "یونان", 1016, "EUR", "اروپا"),
    (41, "europe-other", "سایر کشورهای اروپایی", 792, "EUR", "اروپا"),
    (42, "non-europe-other", "سایر کشورهای غیراروپایی", 759, "EUR", "سایر"),
    (43, "japan", "ژاپن", 200000, "JPY", "آسیا"),
    (44, "syria", "سوریه", 690, "EUR", "خاورمیانه"),
    (45, "canada-group-a", "کانادا (گروه الف)", 1650, "CAD", "آمریکای شمالی"),
    (46, "canada-group-b", "کانادا (گروه ب)", 1485, "CAD", "آمریکای شمالی"),
    (47, "gcc", "کشورهای حاشیه خلیج فارس", 690, "EUR", "خاورمیانه"),
    (48, "malaysia", "مالزی", 600, "EUR", "آسیا"),
]


def seed_pricing(apps, schema_editor):
    PricingCategory = apps.get_model("core", "PricingCategory")
    PricingTariff = apps.get_model("core", "PricingTariff")
    LivingAllowanceCountry = apps.get_model("core", "LivingAllowanceCountry")

    categories = [
        ("consult", "مشاوره و ارزیابی", "مشاوره تخصصی و بررسی اولیه پرونده", "ti-comments-smiley", 1),
        ("documents", "مدارک و ترجمه", "آماده‌سازی، ترجمه و تنظیم مدارک", "ti-files", 2),
        ("apply", "اپلای و پذیرش", "انتخاب دانشگاه و ارسال درخواست پذیرش", "ti-book", 3),
        ("visa", "ویزا و سفارت", "اقدام ویزا، وقت سفارت و آمادگی مصاحبه", "ti-id-badge", 4),
        ("financial", "مقرری و تمکن", "گواهی مقرری و مشاوره تمکن مالی", "ti-money", 5),
    ]
    cat_map = {}
    for slug, name, desc, icon, order in categories:
        cat_map[slug] = PricingCategory.objects.create(
            slug=slug, name=name, description=desc, icon=icon, order=order, is_active=True
        )

    tariffs = [
        (
            "initial-consultation",
            "مشاوره اولیه تخصصی",
            "initial_consultation",
            "consult",
            "جلسه مشاوره ۳۰ دقیقه‌ای با کارشناس برای بررسی اهداف، مقطع تحصیلی و مسیرهای ممکن.",
            "در این جلسه وضعیت تحصیلی، زبان، بودجه و کشورهای هدف شما بررسی می‌شود و نقشه راه اولیه ارائه می‌گردد. مشاوره می‌تواند حضوری یا آنلاین باشد.",
            500_000,
            "fixed",
            "ti-headphone-alt",
            True,
            False,
            "study,language,visa_only,docs_only",
            "",
            1,
        ),
        (
            "profile-evaluation",
            "ارزیابی جامع پرونده",
            "profile_evaluation",
            "consult",
            "تحلیل دقیق مدارک، سن، زبان و شانس پذیرش با گزارش کتبی.",
            "کارشناسان موسسه پرونده شما را با معیارهای دانشگاه‌ها و سفارت مقایسه می‌کنند و نقاط قوت و ضعف را اعلام می‌کنند. خروجی: لیست کشورها و دانشگاه‌های پیشنهادی.",
            2_000_000,
            "fixed",
            "ti-clipboard",
            True,
            True,
            "study,language",
            "",
            2,
        ),
        (
            "document-preparation",
            "آماده‌سازی و تنظیم مدارک",
            "document_preparation",
            "documents",
            "تنظیم رزومه، انگیزه‌نامه، توصیه‌نامه و چک‌لیست مدارک.",
            "تمام مدارک تحصیلی و هویتی شما مطابق استاندارد دانشگاه و سفارت مقصد بازبینی، ویرایش و آماده ارسال می‌شود. از اشتباهات رایج که باعث رد پرونده می‌شود جلوگیری می‌کنیم.",
            3_500_000,
            "fixed",
            "ti-pencil-alt",
            True,
            True,
            "study,language,docs_only",
            "",
            3,
        ),
        (
            "university-application",
            "اپلای دانشگاه (تا ۳ مورد)",
            "university_application",
            "apply",
            "انتخاب دانشگاه، تکمیل فرم‌ها و ارسال درخواست پذیرش.",
            "تا سه دانشگاه یا برنامه تحصیلی: انتخاب استراتژیک، تکمیل پورتال اپلای، آپلود مدارک و پیگیری تا دریافت پاسخ. در صورت نیاز به دانشگاه بیشتر، تعرفه جداگانه محاسبه می‌شود.",
            8_000_000,
            "from",
            "ti-medall",
            True,
            True,
            "study,language",
            "",
            4,
        ),
        (
            "visa-application",
            "اقدام ویزای تحصیلی",
            "visa_application",
            "visa",
            "تکمیل فرم ویزا، آپلود مدارک و پیگیری پرونده سفارت.",
            "راهنمایی کامل برای فرم‌های آنلاین سفارت، رزرو وقت، آماده‌سازی مدارک ویزا و پیگیری وضعیت تا صدور ویزا. شامل یک بار بازبینی نهایی قبل از مصاحبه.",
            12_000_000,
            "fixed",
            "ti-id-badge",
            True,
            True,
            "study,language,visa_only",
            "",
            5,
        ),
        (
            "living-allowance",
            "گواهی مقرری و تمکن مالی",
            "living_allowance",
            "financial",
            "مشاوره و تنظیم گواهی مقرری مطابق کشور مقصد.",
            "بر اساس کشور مقصد، میزان مقرری پیشنهادی بانکی به شما اعلام و مدارک تمکن و گردش حساب راهنمایی می‌شود. مبلغ سپرده بانکی جدا از حق‌الزحمه موسسه است.",
            4_500_000,
            "fixed",
            "ti-wallet",
            True,
            False,
            "study,visa_only,docs_only",
            "",
            6,
        ),
        (
            "official-translation",
            "ترجمه رسمی مدارک",
            "official_translation",
            "documents",
            "ترجمه رسمی مدارک تحصیلی و هویتی برای سفارت و دانشگاه.",
            "هماهنگی با مترجم رسمی دارای مهر دادگستری برای مدارک مورد نیاز. هزینه بر اساس تعداد صفحات ممکن است افزایش یابد.",
            2_500_000,
            "from",
            "ti-world",
            True,
            False,
            "study,language,visa_only,docs_only",
            "",
            7,
        ),
        (
            "embassy-appointment",
            "وقت‌گیری و هماهنگی سفارت",
            "embassy_appointment",
            "visa",
            "رزرو نوبت سفارت و چک نهایی مدارک قبل از مراجعه.",
            "دریافت وقت سفارت در سیستم‌های مختلف کشورها، یادآوری زمان مراجعه و چک‌لیست روز مصاحبه.",
            3_000_000,
            "fixed",
            "ti-calendar",
            True,
            False,
            "study,visa_only",
            "visa_application",
            8,
        ),
        (
            "interview-prep",
            "آمادگی مصاحبه ویزا",
            "interview_prep",
            "visa",
            "جلسه شبیه‌سازی مصاحبه و پاسخ به سوالات متداول.",
            "یک جلسه تخصصی برای تمرین سوالات رایج سفارت، نحوه پاسخ‌گویی و مدیریت استرس. مناسب ویزای کانادا، انگلستان، آلمان و …",
            2_000_000,
            "fixed",
            "ti-microphone",
            True,
            False,
            "study,visa_only",
            "visa_application",
            9,
        ),
        (
            "courier-followup",
            "ارسال مدارک و پیگیری پرونده",
            "courier_followup",
            "documents",
            "ارسال فیزیکی مدارک و پیگیری وضعیت پرونده تا نتیجه نهایی.",
            "هماهنگی ارسال پستی یا پیک به دانشگاه و سفارت، و پیگیری منظم تا دریافت پاسخ نهایی.",
            1_500_000,
            "fixed",
            "ti-truck",
            True,
            False,
            "study,visa_only",
            "",
            10,
        ),
        (
            "full-package",
            "پکیج کامل همراهی پرونده",
            "full_package",
            "apply",
            "همراهی از مشاوره تا ویزا با تخفیف نسبت به خدمات تکی.",
            "شامل مشاوره، ارزیابی، آماده‌سازی مدارک، اپلای تا ۳ دانشگاه، اقدام ویزا و یک جلسه آمادگی مصاحبه. مناسب کسانی که تازه مسیر مهاجرت تحصیلی را شروع می‌کنند.",
            24_000_000,
            "from",
            "ti-package",
            True,
            False,
            "study",
            "",
            11,
        ),
    ]

    for row in tariffs:
        slug, title, key, cat_slug, short, desc, price, ptype, icon, calc_opt, is_core, goals, deps, order = row
        PricingTariff.objects.create(
            category=cat_map[cat_slug],
            slug=slug,
            title=title,
            calculator_key=key,
            short_description=short,
            description=desc,
            price_toman=price,
            price_type=ptype,
            icon=icon,
            is_calculator_option=calc_opt,
            is_core=is_core,
            auto_for_goals=goals,
            depends_on_keys=deps,
            order=order,
            is_active=True,
        )

    for order, slug, name, amount, currency, region in LIVING_ALLOWANCE:
        keywords = name.replace("(", "").replace(")", "").replace("،", " ")
        LivingAllowanceCountry.objects.create(
            slug=slug,
            name=name,
            amount=amount,
            currency=currency,
            search_keywords=keywords,
            region_group=region,
            order=order,
            is_active=True,
        )


def reverse_seed(apps, schema_editor):
    apps.get_model("core", "PricingTariff").objects.all().delete()
    apps.get_model("core", "PricingCategory").objects.all().delete()
    apps.get_model("core", "LivingAllowanceCountry").objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0035_pricing_and_living_allowance"),
    ]

    operations = [
        migrations.RunPython(seed_pricing, reverse_seed),
    ]
