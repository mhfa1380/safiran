"""سئو صفحه ارزیابی رایگان مهاجرت تحصیلی — متا، canonical و داده ساختاریافته."""

from __future__ import annotations

import json
from typing import Any

from django.urls import reverse


EVALUATION_FAQS: tuple[tuple[str, str], ...] = (
    (
        "آیا ارزیابی مهاجرت تحصیلی رایگان است؟",
        "بله. تکمیل فرم ارزیابی آنلاین، دریافت گزارش تحلیل هوشمند و مشاهده پیشنهاد کشور، "
        "رشته، بورسیه و برآورد هزینه برای شما کاملاً رایگان است و هزینه اولیه ندارد.",
    ),
    (
        "تحلیل هوشمند پرونده چه چیزهایی را بررسی می‌کند؟",
        "سیستم بر اساس معدل، مدرک فعلی، رشته، وضعیت زبان (آیلتس، تافل، دولینگو، PTE و …)، "
        "کشورهای مقصد، تمکن مالی، دستاوردهای علمی و هدف مقطع، تطابق شما با دانشگاه‌ها، "
        "مسیر بورسیه و فاند، مطالب وبلاگ و تعرفه تقریبی خدمات را در یک گزارش "
        "شخصی‌سازی‌شده جمع‌بندی می‌کند.",
    ),
    (
        "بعد از ثبت فرم ارزیابی چه اتفاقی می‌افتد؟",
        "بلافاصله پس از ثبت، گزارش اولیه آنلاین نمایش داده می‌شود و لینک نتیجه "
        "برای مدت محدود در اختیار شماست. در صورت تمایل، کارشناسان موسسه برای "
        "مشاوره تخصصی و برنامه‌ریزی اپلای تماس می‌گیرند.",
    ),
    (
        "ارزیابی آنلاین برای چه مقاطعی مناسب است؟",
        "برای برنامه‌ریزی کارشناسی، کارشناسی ارشد، دکتری، فوق‌لیسانس و بورسیه تحصیلی "
        "طراحی شده است. با انتخاب مقصد و رشته هدف، پیشنهادها متناسب با همان مقطع "
        "اولویت‌بندی می‌شوند.",
    ),
    (
        "چه کشورهایی در فرم ارزیابی مهاجرت پوشش داده می‌شود؟",
        "می‌توانید چند کشور مقصد انتخاب کنید: کانادا، آلمان، ایتالیا، اسپانیا، هلند، "
        "چین، ترکیه، امارات، انگلستان و گزینه اروپا/سایر — تا تحلیل متناسب با "
        "اولویت شما انجام شود.",
    ),
    (
        "تفاوت ارزیابی رایگان آنلاین با رزرو مشاوره چیست؟",
        "ارزیابی آنلاین در چند دقیقه تصویر اولیه از وضعیت پرونده، شانس پذیرش و "
        "مسیرهای محتمل می‌دهد. رزرو مشاوره برای صحبت عمیق با کارشناس، زمان‌بندی "
        "اپلای و تصمیم نهایی ویزای تحصیلی است.",
    ),
    (
        "آیا گزارش ارزیابی جایگزین مشاوره تخصصی مهاجرت است؟",
        "خیر. گزارش هوشمند نقطه شروع تصمیم‌گیری است؛ شرایط واقعی پذیرش به زمان اپلای، "
        "رقابت رشته و جزئیات مدارک بستگی دارد. برای اقدام نهایی، مشاوره با کارشناس "
        "توصیه می‌شود.",
    ),
    (
        "چقدر طول می‌کشد گزارش تحلیل هوشمند آماده شود؟",
        "پس از تکمیل چهار مرحله فرم، تحلیل معمولاً در همان جلسه — از چند ثانیه تا "
        "چند دقیقه — نمایش داده می‌شود و نیازی به انتظار روزهای کاری نیست.",
    ),
    (
        "آیا برای ویزای تحصیلی و پذیرش دانشگاه خارج کافی است؟",
        "گزارش ارزیابی به شما کمک می‌کند مسیرهای منطقی را بشناسید؛ اما اخذ پذیرش "
        "دانشگاه، تمکن مالی، مدارک و مصاحبه ویزا مراحل جداگانه‌ای هستند که در "
        "مشاوره تخصصی پوشش داده می‌شوند.",
    ),
    (
        "چه کسانی باید از ارزیابی رایگان مهاجرت تحصیلی استفاده کنند؟",
        "دانشجویان و فارغ‌التحصیلانی که قصد اپلای، بورسیه یا مهاجرت تحصیلی دارند "
        "و می‌خواهند قبل از پرداخت هزینه مشاوره، وضعیت تقریبی پرونده خود را "
        "بدانند.",
    ),
)

EVALUATION_BENEFITS: tuple[tuple[str, str], ...] = (
    ("رایگان و آنلاین", "بدون هزینه اولیه؛ هر زمان از موبایل یا دسکتاپ فرم را تکمیل کنید."),
    ("تحلیل فوری پرونده", "گزارش شخصی‌سازی‌شده بلافاصله پس از ثبت، قبل از تماس مشاور."),
    ("پوشش چندکشوری", "مقایسه مسیر کانادا، آلمان، اروپا، چین و سایر مقاصد بر اساس شرایط شما."),
    ("بورسیه و هزینه", "اشاره به بورسیه‌های مرتبط و برآورد اولیه تعرفه خدمات موسسه."),
)

EVALUATION_HOWTO_STEPS: tuple[str, ...] = (
    "نام، شماره تماس و برنامه مهاجرت تحصیلی را وارد کنید.",
    "آخرین مدرک، رشته تحصیلی و معدل را ثبت کنید.",
    "وضعیت آزمون زبان و دستاوردهای علمی را مشخص کنید (اختیاری).",
    "کشور مقصد و رشته هدف را انتخاب کنید و فرم را برای دریافت گزارش رایگان ارسال کنید.",
)

EVALUATION_SEO_INTRO: str = (
    "ارزیابی رایگان مهاجرت تحصیلی ابزاری آنلاین برای دانشجویان و فارغ‌التحصیلان ایرانی است "
    "که می‌خواهند قبل از شروع اپلای، شانس تقریبی پذیرش دانشگاه خارج، مسیر بورسیه، "
    "ویزای تحصیلی و هزینه‌های اولیه را بدانند. با پر کردن فرم چهارمرحله‌ای، "
    "سیستم تحلیل هوشمند بر اساس معدل، زبان، رشته و کشور مقصد شما گزارشی شخصی‌سازی‌شده "
    "ارائه می‌دهد — بدون پرداخت هزینه و بدون انتظار برای تماس اولیه."
)


def build_evaluation_page_seo(
    *,
    institute_name: str,
    site_url: str,
) -> dict[str, Any]:
    path = reverse("evaluation")
    base = site_url.rstrip("/")
    page_url = f"{base}{path}"

    meta_title = "ارزیابی رایگان آنلاین مهاجرت تحصیلی | تحلیل هوشمند پرونده"
    meta_description = (
        f"فرم ارزیابی رایگان مهاجرت تحصیلی در {institute_name} — تحلیل هوشمند آنلاین "
        "معدل، زبان، کشور مقصد (کانادا، آلمان، ایتالیا، اروپا، چین)، بورسیه، "
        "پذیرش دانشگاه و برآورد هزینه. گزارش شخصی فوری پس از ثبت، بدون هزینه."
    )
    meta_keywords = (
        "ارزیابی رایگان مهاجرت تحصیلی, فرم ارزیابی آنلاین, تحلیل هوشمند پرونده, "
        "مشاوره مهاجرت تحصیلی رایگان, اعزام دانشجو, پذیرش دانشگاه خارج, "
        "ویزای تحصیلی, بورسیه تحصیلی, فاند تحصیلی, اپلای دانشگاه, "
        "ارزیابی شرایط مهاجرت, کانادا, آلمان, ایتالیا, اروپا, چین"
    )
    og_title = f"{meta_title} | {institute_name}"
    hero_lead = (
        "فرم ارزیابی رایگان و آنلاین مهاجرت تحصیلی — در چند دقیقه شرایط خود را ثبت کنید "
        "و گزارش تحلیل هوشمند کشور، رشته، بورسیه، دانشگاه و هزینه را همان لحظه ببینید."
    )

    faq_entities = [
        {
            "@type": "Question",
            "name": q,
            "acceptedAnswer": {"@type": "Answer", "text": a},
        }
        for q, a in EVALUATION_FAQS
    ]

    graph: list[dict[str, Any]] = [
        {
            "@type": "WebPage",
            "@id": f"{page_url}#webpage",
            "url": page_url,
            "name": meta_title,
            "description": meta_description,
            "inLanguage": "fa-IR",
            "keywords": meta_keywords,
            "about": [
                {"@type": "Thing", "name": "مهاجرت تحصیلی"},
                {"@type": "Thing", "name": "اعزام دانشجو"},
                {"@type": "Thing", "name": "ویزای تحصیلی"},
                {"@type": "Thing", "name": "بورسیه تحصیلی"},
            ],
            "isPartOf": {
                "@type": "WebSite",
                "@id": f"{base}/#website",
                "name": institute_name,
                "url": f"{base}/",
            },
            "primaryImageOfPage": {
                "@type": "ImageObject",
                "url": f"{base}/static/img/logo.png",
            },
        },
        {
            "@type": "BreadcrumbList",
            "@id": f"{page_url}#breadcrumb",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "صفحه اصلی", "item": f"{base}/"},
                {"@type": "ListItem", "position": 2, "name": "ارزیابی رایگان مهاجرت تحصیلی", "item": page_url},
            ],
        },
        {
            "@type": "Service",
            "@id": f"{page_url}#evaluation-service",
            "name": "ارزیابی رایگان مهاجرت تحصیلی آنلاین",
            "alternateName": "فرم ارزیابی هوشمند مهاجرت",
            "description": meta_description,
            "url": page_url,
            "serviceType": "ارزیابی و مشاوره مهاجرت تحصیلی",
            "areaServed": {"@type": "Country", "name": "Iran"},
            "availableChannel": {
                "@type": "ServiceChannel",
                "serviceUrl": page_url,
                "serviceType": "فرم آنلاین",
                "availableLanguage": "fa",
            },
            "provider": {
                "@type": "EducationalOrganization",
                "name": institute_name,
                "url": f"{base}/",
            },
            "offers": {
                "@type": "Offer",
                "price": "0",
                "priceCurrency": "IRR",
                "description": "ارزیابی و گزارش تحلیل هوشمند اولیه — رایگان",
                "url": page_url,
                "availability": "https://schema.org/InStock",
            },
        },
        {
            "@type": "WebApplication",
            "@id": f"{page_url}#eval-app",
            "name": "ارزیابی هوشمند مهاجرت تحصیلی",
            "applicationCategory": "EducationalApplication",
            "operatingSystem": "Web",
            "browserRequirements": "Requires JavaScript",
            "url": page_url,
            "inLanguage": "fa-IR",
            "description": (
                "ابزار آنلاین رایگان تحلیل شرایط مهاجرت تحصیلی بر اساس سوابق تحصیلی، "
                "آزمون زبان و کشور مقصد"
            ),
            "offers": {"@type": "Offer", "price": "0", "priceCurrency": "IRR"},
            "featureList": [title for title, _ in EVALUATION_BENEFITS],
        },
        {
            "@type": "ItemList",
            "@id": f"{page_url}#benefits",
            "name": "مزایای ارزیابی رایگان",
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": i + 1,
                    "name": title,
                    "description": desc,
                }
                for i, (title, desc) in enumerate(EVALUATION_BENEFITS)
            ],
        },
        {
            "@type": "HowTo",
            "@id": f"{page_url}#howto",
            "name": "نحوه دریافت گزارش ارزیابی رایگان مهاجرت تحصیلی",
            "description": "چهار مرحله ساده برای تحلیل هوشمند پرونده مهاجرت تحصیلی",
            "totalTime": "PT5M",
            "inLanguage": "fa-IR",
            "step": [
                {
                    "@type": "HowToStep",
                    "position": i + 1,
                    "name": text.split("،")[0].split(".")[0],
                    "text": text,
                    "url": page_url,
                }
                for i, text in enumerate(EVALUATION_HOWTO_STEPS)
            ],
        },
        {
            "@type": "FAQPage",
            "@id": f"{page_url}#faq",
            "url": page_url,
            "inLanguage": "fa-IR",
            "mainEntity": faq_entities,
        },
    ]

    schema = {"@context": "https://schema.org", "@graph": graph}

    from .google_ai_seo import augment_evaluation_schema, build_eval_answer_summary
    from .site_navigation import build_evaluation_related_links

    related_links = list(build_evaluation_related_links(site_url=site_url))

    def _pick(key: str) -> dict[str, str] | None:
        return next((lnk for lnk in related_links if lnk.get("key") == key), None)

    return {
        "eval_meta_title": meta_title,
        "eval_meta_description": meta_description,
        "eval_meta_keywords": meta_keywords,
        "eval_page_url": page_url,
        "eval_hero_lead": hero_lead,
        "eval_answer_summary": build_eval_answer_summary(),
        "eval_og_title": og_title,
        "eval_schema_json": augment_evaluation_schema(schema, site_url=site_url),
        "eval_faqs": EVALUATION_FAQS,
        "eval_benefits": EVALUATION_BENEFITS,
        "eval_howto_steps": EVALUATION_HOWTO_STEPS,
        "eval_seo_intro": EVALUATION_SEO_INTRO,
        "eval_related_links": related_links,
        "eval_blog_guide_link": _pick("blog_evaluation_guide"),
        "eval_appointment_link": _pick("appointment"),
        "eval_pricing_link": _pick("pricing"),
    }
