# به‌روزرسانی خدمات و سوالات متداول مطابق قرارداد

from django.db import migrations


def update_services_and_faq(apps, schema_editor):
    Service = apps.get_model("core", "Service")
    ServiceCategory = apps.get_model("core", "ServiceCategory")
    FAQ = apps.get_model("core", "FAQ")
    FAQCategory = apps.get_model("core", "FAQCategory")

    cat_moshavere, _ = ServiceCategory.objects.get_or_create(
        slug="moshavere-arezaye",
        defaults={"name": "مشاوره و ارزیابی", "icon": "ti-headphone-alt", "order": 1, "is_active": True},
    )
    cat_paziresh, _ = ServiceCategory.objects.get_or_create(
        slug="paziresh-apply",
        defaults={"name": "پذیرش و اپلای", "icon": "ti-book", "order": 2, "is_active": True},
    )
    cat_visa, _ = ServiceCategory.objects.get_or_create(
        slug="visa-madarek",
        defaults={"name": "ویزا و روادید", "icon": "ti-id-badge", "order": 3, "is_active": True},
    )
    cat_est, _ = ServiceCategory.objects.get_or_create(
        slug="estghrar-pasokhbane",
        defaults={"name": "استقرار و پشتیبانی", "icon": "ti-home", "order": 5, "is_active": True},
    )

    contract_services = [
        {
            "title": "مشاوره تخصصی (طبق قرارداد)",
            "slug": "moshavere-gheyradi",
            "category": cat_moshavere,
            "order": 1,
            "featured": True,
            "icon": "ti-headphone-alt",
            "keywords": "مشاوره,قرارداد,جلسه,۵۰۰۰۰,تعرفه,هزینه",
            "short": "هر جلسه ۵۰٬۰۰۰ تومان — اطلاعات جامع کشور، دانشگاه، رشته و روادید (ماده ۳-۱).",
            "description": (
                "مطابق ماده ۱-۱ و ۳-۱ قرارداد استاندارد موسسات اعزام: ارائه مشاوره و اطلاعات جامع "
                "در خصوص کشور مقصد، دانشگاه، رشته، مقطع، هزینه‌ها، روادید و سایر موارد مؤثر در تصمیم‌گیری. "
                "حق‌الزحمه هر جلسه مشاوره ۵۰٬۰۰۰ تومان (۵۰۰٬۰۰۰ ریال) است."
            ),
            "highlights": "مطابق ماده ۱-۱ قرارداد\n۵۰٬۰۰۰ تومان هر جلسه\nحضوری یا آنلاین\nبدون تعهد برای ادامه",
        },
        {
            "title": "اخذ پذیرش دانشگاه",
            "slug": "akhz-paziresh",
            "category": cat_paziresh,
            "order": 2,
            "featured": True,
            "icon": "ti-medall",
            "keywords": "پذیرش,اپلای,۴۰ درصد,مقرری,دانشگاه",
            "short": "حداکثر ۴۰٪ یک‌ماه مقرری بورس مجرد — دانشگاه‌های مورد تأیید وزارت علوم.",
            "description": (
                "ماده ۱-۲: اخذ پذیرش از دانشگاه‌های خارجی مورد تأیید وزارت علوم، تحقیقات و فناوری "
                "یا بهداشت. حق‌الزحمه حداکثر ۴۰٪ از یک‌ماه مقرری دانشجوی بورسیه مجرد در کشور مقصد "
                "با معادل ریالی به نرخ روز (ماده ۳-۲)."
            ),
            "highlights": "دانشگاه‌های مورد تأیید\nحداکثر ۴۰٪ مقرری ماهانه\nمعادل ریالی نرخ روز\nپیگیری تا Offer",
        },
        {
            "title": "اخذ روادید تحصیلی",
            "slug": "akhz-visa",
            "category": cat_visa,
            "order": 3,
            "featured": True,
            "icon": "ti-id-badge",
            "keywords": "ویزا,روادید,۲۰ درصد,سفارت,تحصیلی",
            "short": "حداکثر ۲۰٪ یک‌ماه مقرری — اقدام و پیگیری پرونده ویزا.",
            "description": (
                "ماده ۱-۳: اخذ روادید تحصیلی. حق‌الزحمه حداکثر ۲۰٪ از یک‌ماه مقرری "
                "با احتساب معادل ریالی به نرخ روز (ماده ۳-۳). در صورت عدم موفقیت موسسه "
                "در اخذ ویزا، هزینه‌های ویزا پس از کسر هزینه‌های غیرقابل استرداد سفارت عودت می‌شود (۳-۸)."
            ),
            "highlights": "ماده ۱-۳ قرارداد\nحداکثر ۲۰٪ مقرری\nپیگیری سفارت\nقوانین استرداد ۳-۸",
        },
        {
            "title": "ثبتنام در دانشگاه",
            "slug": "sabtnam-daneshgah",
            "category": cat_paziresh,
            "order": 4,
            "featured": False,
            "icon": "ti-pencil-alt",
            "keywords": "ثبتنام,دانشگاه,۲۰ درصد,مقرری",
            "short": "حداکثر ۲۰٪ یک‌ماه مقرری — ثبتنام نهایی و تکمیل اطلاعات دانشگاه.",
            "description": (
                "ماده ۱-۴: ثبتنام در دانشگاه و ارائه تمامی اطلاعات مورد درخواست. "
                "حق‌الزحمه حداکثر ۲۰٪ یک‌ماه مقرری (ماده ۳-۴)."
            ),
            "highlights": "ثبتنام نهایی\nحداکثر ۲۰٪ مقرری\nهماهنگی با دانشگاه",
        },
        {
            "title": "انتقال، اسکان و راهنمایی",
            "slug": "eskhan-oghdamat",
            "category": cat_est,
            "order": 5,
            "featured": False,
            "icon": "ti-home",
            "keywords": "اسکان,اقامت,انتقال,۲۰ درصد,استقرار",
            "short": "۲۰٪ یک‌ماه مقرری — جابجایی، اسکان و راهنمایی در کشور مقصد.",
            "description": (
                "ماده ۱-۵: جابجایی، اقامت و اسکان مناسب با درخواست متقاضی و خدمات راهنمایی "
                "در کشور محل تحصیل. حق‌الزحمه ۲۰٪ یک‌ماه مقرری (ماده ۳-۵)."
            ),
            "highlights": "ماده ۱-۵\nاسکان اولیه\nراهنمایی در مقصد\n۲۰٪ مقرری",
        },
    ]

    for data in contract_services:
        Service.objects.update_or_create(
            slug=data["slug"],
            defaults={
                "title": data["title"],
                "category": data["category"],
                "short_description": data["short"],
                "description": data["description"],
                "highlights": data["highlights"],
                "icon": data["icon"],
                "search_keywords": data["keywords"],
                "order": data["order"],
                "is_featured": data["featured"],
                "is_active": True,
            },
        )

    faq_cat_tarafe, _ = FAQCategory.objects.get_or_create(
        slug="tarafe-gharardad",
        defaults={
            "name": "تعرفه و قرارداد",
            "icon": "ti-money",
            "description": "سوالات درباره تعرفه خدمات، مقرری بانکی و قرارداد موسسه.",
            "order": 4,
            "is_active": True,
        },
    )
    faq_cat_paziresh, _ = FAQCategory.objects.get_or_create(
        slug="paziresh-visa",
        defaults={"name": "پذیرش، ویزا و مدارک", "icon": "ti-id-badge", "order": 2, "is_active": True},
    )

    faqs = [
        (
            "تعرفه-خدمات-چگونه-محاسبه-میشود",
            "تعرفه خدمات چگونه محاسبه می‌شود؟",
            faq_cat_tarafe,
            True,
            1,
            "تعرفه,قرارداد,مقرری,درصد,محاسبه",
            "تعرفه‌ها منطبق با فهرست مقرری دانشجویان بورسیه مصوب هیئت وزیران است. "
            "مشاوره ۵۰٬۰۰۰ تومان هر جلسه است؛ حق‌الزحمه پذیرش حداکثر ۴۰٪، ویزا و ثبتنام "
            "هر کدام حداکثر ۲۰٪ و استقرار ۲۰٪ از یک‌ماه مقرری کشور مقصد، با معادل ریالی به نرخ روز.",
        ),
        (
            "mablaq-moshavere",
            "مبلغ مشاوره چقدر است؟",
            faq_cat_tarafe,
            True,
            2,
            "مشاوره,۵۰۰۰۰,جلسه,هزینه",
            "طبق ماده ۳-۱ قرارداد: ۵۰٬۰۰۰ تومان (۵۰۰٬۰۰۰ ریال) برای هر جلسه مشاوره.",
        ),
        (
            "moqarari-banki-chist",
            "مقرری بانکی پیشنهادی چیست؟",
            faq_cat_tarafe,
            True,
            3,
            "مقرری,تمکن,بانک,سپرده",
            "مقرری مبلغی است که سفارت یا دانشگاه برای تمکن مالی تحصیل پیشنهاد می‌کند. "
            "جدول ۴۸ کشور در صفحه تعرفه خدمات قابل مشاهده است و جدا از حق‌الزحمه موسسه محاسبه می‌شود.",
        ),
        (
            "zamanbandi-pardakht-gharardad",
            "زمان‌بندی پرداخت قرارداد چگونه است؟",
            faq_cat_tarafe,
            False,
            4,
            "پرداخت,۴۰ درصد,قسط,قرارداد",
            "ماده ۴: ۴۰٪ حق‌الزحمه هنگام امضای قرارداد و تسویه مابقی پس از ایفای کامل تعهدات موسسه.",
        ),
        (
            "esterdad-vajh-visa",
            "اگر ویزا صادر نشود پول برمی‌گردد؟",
            faq_cat_paziresh,
            True,
            5,
            "استرداد,ویزا,عودت,قرارداد",
            "طبق ۳-۸: اگر موسسه متعهد به اخذ ویزا باشد و موفق نشود، هزینه‌های ویزا پس از کسر "
            "هزینه‌های غیرقابل استرداد سفارت به متقاضی عودت می‌شود. در پذیرش+ویزا، بند ۳-۹ نیز حاکم است.",
        ),
        (
            "hazine-ha-ye-motaghazi",
            "چه هزینه‌هایی بر عهده خود دانشجو است؟",
            faq_cat_tarafe,
            False,
            6,
            "ترجمه,بلیط,سفارت,ثبتنام,هزینه",
            "ماده ۶-۳: ترجمه مدارک، تحویل مدارک، هزینه ثبتنام دانشگاه، هزینه سفارت برای صدور ویزا "
            "و بلیط هواپیما بر عهده متقاضی است.",
        ),
        (
            "modat-gharardad",
            "مدت قرارداد چقدر است؟",
            faq_cat_tarafe,
            False,
            7,
            "مدت,قرارداد,۳ ماه,۶ ماه",
            "ماده ۲: حداکثر ۳ ماه برای پذیرش، ۶ ماه برای ویزا و ۶ ماه برای ثبتنام نهایی. "
            "در کشورهایی با فرایند ویزای طولانی‌تر، با اطلاع قبلی قابل تمدید است.",
        ),
        (
            "bourse-haghozahme",
            "حق‌الزحمه در صورت اخذ بورس چقدر است؟",
            faq_cat_tarafe,
            False,
            8,
            "بورس,۷۰ درصد,۵۰ درصد,شهریه",
            "ماده ۳-۷: بورس کامل — ۷۰٪ یک‌ماه مقرری + ۱۰٪ شهریه ترم/سال اول؛ "
            "بورس نیمه دوره — ۵۰٪ مقرری + ۱۰٪ شهریه. مبلغ شهریه با اسناد مثبته تعیین می‌شود.",
        ),
    ]

    for slug, question, category, featured, order, keywords, answer in faqs:
        FAQ.objects.update_or_create(
            slug=slug,
            defaults={
                "question": question,
                "answer": answer,
                "category": category,
                "is_featured": featured,
                "is_active": True,
                "order": order + 20,
                "search_keywords": keywords,
            },
        )


def reverse_update(apps, schema_editor):
    FAQ = apps.get_model("core", "FAQ")
    FAQ.objects.filter(order__gte=20).delete()
    FAQCategory = apps.get_model("core", "FAQCategory")
    FAQCategory.objects.filter(slug="tarafe-gharardad").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0040_contract_pricing"),
    ]

    operations = [
        migrations.RunPython(update_services_and_faq, reverse_update),
    ]
