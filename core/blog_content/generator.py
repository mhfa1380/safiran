"""
تولید HTML مقاله وبلاگ (۱۵۰۰+ کلمه) از متادیتای plan_200.
"""
from __future__ import annotations

import hashlib
import re
from html import escape

from .context import EVAL_CTA_PATH, INSTITUTE, YEAR, profile_for

_WORD_RE = re.compile(r"[\w\u0600-\u06FF]+", re.UNICODE)


def word_count(text: str) -> int:
    plain = re.sub(r"<[^>]+>", " ", text)
    return len(_WORD_RE.findall(plain))


def _h(s: str) -> str:
    return escape(s, quote=True)


def _pick(slug: str, key: str, options: list[str]) -> str:
    if not options:
        return ""
    h = int(hashlib.md5(f"{slug}:{key}".encode()).hexdigest(), 16)
    return options[h % len(options)]


def _p(*parts: str) -> str:
    return "".join(f"<p>{part}</p>\n" for part in parts if part)


def _cta_block() -> str:
    return f"""
<div style="background:linear-gradient(135deg,#ecfdf5 0%,#e0f2fe 100%);border:1px solid #99f6e4;border-radius:14px;padding:1.35rem 1.5rem;margin:1.75rem 0;text-align:right;direction:rtl">
<p style="margin:0 0 0.5rem;font-size:1.05rem;color:#0f766e"><strong>ارزیابی رایگان مهاجرت تحصیلی {YEAR}</strong></p>
<p style="margin:0 0 1rem;color:#334155;line-height:1.8">با فرم ارزیابی هوشمند {INSTITUTE}، کشور، مقطع، بورسیه و هزینه را بر اساس پرونده واقعی خود ببینید.</p>
<p style="margin:0"><a href="{EVAL_CTA_PATH}" style="display:inline-block;background:#0d9488;color:#fff!important;padding:0.7rem 1.4rem;border-radius:10px;text-decoration:none;font-weight:700">شروع ارزیابی رایگان</a></p>
</div>
"""


def _intro(article: dict, prof: dict) -> str:
    title = article["title"]
    cat = article.get("category", "")
    kw = article.get("keywords", "")
    slug = article["slug"]
    hook = _pick(
        slug,
        "hook",
        [
            f"اگر «{title}» برایتان سوال است، این راهنمای {YEAR} دقیقاً برای متقاضیان ایرانی نوشته شده است.",
            f"در سال {YEAR} رقابت برای پذیرش و ویزا سخت‌تر شده؛ اما با برنامه‌ریزی درست هنوز مسیر روشن است.",
            f"بسیاری از پرونده‌ها نه به‌خاطر ضعف علمی، بلکه به‌خاطر جزئیات مدارک و ویزا متوقف می‌شوند.",
            f"این مقاله خلاصه تجربه مشاوره‌ای {INSTITUTE} در موضوع {cat or 'مهاجرت تحصیلی'} است.",
        ],
    )
    return _p(
        f"<strong>{_h(title)}</strong> — {hook} "
        f"در ادامه شرایط به‌روز {YEAR}، مزایا و معایب، مراحل عملی، "
        f"هزینه‌های واقع‌بینانه، اشتباهات پرهزینه و پاسخ سوالات متداول را می‌خوانید.",
        f"کلمات کلیدی این صفحه: <em>{_h(kw)}</em>. "
        f"مقصد اصلی بحث ما <strong>{_h(prof['en'])}</strong> و نظام <strong>{_h(prof['visa'])}</strong> است.",
        "قبل از هر اقدامی، پرونده خود را با مدارک واقعی (معدل، زبان، بودجه، گپ تحصیلی) "
        "مرور کنید؛ تصمیم‌گیری احساسی یا کپی‌کردن تجربه دیگران اغلب منجر به ریجکت می‌شود.",
    )


def _section_conditions(article: dict, prof: dict) -> str:
    slug = article["slug"]
    cat = article.get("category", "")
    return f"""
<h2>شرایط و قوانین {YEAR} (به‌روز و کاربردی)</h2>
{_p(
    f"در {YEAR} نهادهای پذیرش و مهاجرت در {_h(prof['en'])} به شفافیت مالی، "
    f"انطباق برنامه تحصیلی با سابقه قبلی و اصالت مدارک حساس‌تر شده‌اند.",
    f"برای ایرانیان، مدارک تحصیلی رسمی، ترجمه قضایی، {_h(prof['lang'])} "
    f"و گاهی گواهی‌های تکمیلی (مانند نظام وظیفه یا تمکن) جزو چک‌لیست اصلی است.",
    _pick(slug, "cond", [
        f"اگر {cat} مقصد شماست، از همان ابتدا DLI/دانشگاه معتبر و مسیر ویزای {_h(prof['visa'])} را تأیید کنید.",
        "تغییرات سالانه را فقط از وب‌سایت رسمی دانشگاه و اداره مهاجرت بخوانید، نه از شبکه‌های اجتماعی.",
        "ددلاین پاییز ۲۰۲۶ معمولاً شلوغ‌ترین بازه است؛ ۶ تا ۹ ماه زودتر شروع کنید.",
    ]),
)}
<h3>چک‌لیست مدارک پایه</h3>
<ul>
<li>پاسپورت معتبر (ترجیحاً حداقل ۱۸ ماه اعتبار)</li>
<li>ریزنمرات و گواهی‌ها با ترجمه رسمی</li>
<li>مدرک زبان یا پذیرش مشروط زبان با برنامه روشن</li>
<li>نامه پذیرش (LOA / i20 / CAS بسته به کشور)</li>
<li>تمکن مالی یا بورسیه مستند</li>
<li>SOP/CV/توصیه‌نامه برای مقاطع بالاتر</li>
</ul>
"""


def _section_pros_cons(prof: dict, slug: str) -> str:
    return f"""
<h2>مزایا و معایب (نمای واقع‌بینانه)</h2>
<h3>مزایا</h3>
<ul>
<li>کیفیت آموزشی و اعتبار بین‌المللی دانشگاه‌های {_h(prof['en'])}</li>
<li>امکان {_h(prof['work'])} و تجربه کاری</li>
<li>مسیر {_h(prof['post_study'])} برای آینده شغلی</li>
<li>شبکه جهانی و بازار کار بین‌المللی</li>
<li>تنوع رشته و شهر برای سلیقه‌های مختلف</li>
</ul>
<h3>معایب و چالش‌ها</h3>
<ul>
<li>هزینه {_h(prof['tuition'])} و {_h(prof['living'])}</li>
<li>فشار روانی دوران اپلای و انتظار ویزا</li>
<li>تفاوت فرهنگی و زبان در ماه‌های اول</li>
<li>ریسک ریجکت در صورت پرونده ضعیف یا ناهماهنگ</li>
<li>فاصله از خانواده و نیاز به برنامه مالی دقیق</li>
</ul>
<p>{_pick(slug, 'pc', ['جمع‌بندی: اگر بودجه و هدف شغلی شفاف باشد، معمولاً مزایا غالب است.', 'برای بسیاری از ایرانیان، آمادگی زبان مهم‌ترین گلوگاه است.'])}</p>
"""


def _section_steps(article: dict, prof: dict) -> str:
    return f"""
<h2>مراحل اقدام گام‌به‌گام</h2>
<ol>
<li><strong>ارزیابی اولیه:</strong> تعیین کشور، مقطع، بودجه و افق شغلی</li>
<li><strong>آماده‌سازی زبان:</strong> {_h(prof['lang'])}</li>
<li><strong>انتخاب دانشگاه:</strong> {_h(prof['unis'])} و شهرهایی مانند {_h(prof['cities'])}</li>
<li><strong>اپلای و پذیرش:</strong> ارسال مدارک، پیگیری Conditional Offer</li>
<li><strong>تمکن و بورسیه:</strong> {_h(prof['currency'])}</li>
<li><strong>ویزا:</strong> {_h(prof['visa'])} — تکمیل فرم، بیومتریک، مصاحبه در صورت نیاز</li>
<li><strong>ورود و استقرار:</strong> بیمه، اسکان، ثبت محلی</li>
</ol>
<p>تیم {INSTITUTE} در هر مرحله چک‌لیست اختصاصی می‌دهد تا پرونده یکپارچه بماند.</p>
"""


def _section_costs(prof: dict, slug: str) -> str:
    return f"""
<h2>هزینه‌ها در {YEAR} (برآورد)</h2>
<p>اعداد تقریبی و قبل از اپلای باید با دانشگاه و نرخ ارز به‌روز شوند.</p>
<table style="width:100%;border-collapse:collapse;margin:1rem 0">
<thead>
<tr style="background:#f1f5f9"><th style="padding:0.5rem;border:1px solid #e2e8f0">ردیف</th>
<th style="padding:0.5rem;border:1px solid #e2e8f0">شرح</th>
<th style="padding:0.5rem;border:1px solid #e2e8f0">محدوده</th></tr>
</thead>
<tbody>
<tr><td style="padding:0.5rem;border:1px solid #e2e8f0">۱</td><td style="padding:0.5rem;border:1px solid #e2e8f0">شهریه سالانه</td>
<td style="padding:0.5rem;border:1px solid #e2e8f0">{_h(prof['tuition'])}</td></tr>
<tr><td style="padding:0.5rem;border:1px solid #e2e8f0">۲</td><td style="padding:0.5rem;border:1px solid #e2e8f0">زندگی ماهانه</td>
<td style="padding:0.5rem;border:1px solid #e2e8f0">{_h(prof['living'])}</td></tr>
<tr><td style="padding:0.5rem;border:1px solid #e2e8f0">۳</td><td style="padding:0.5rem;border:1px solid #e2e8f0">ویزا و مدارک</td>
<td style="padding:0.5rem;border:1px solid #e2e8f0">متغیر</td></tr>
<tr><td style="padding:0.5rem;border:1px solid #e2e8f0">۴</td><td style="padding:0.5rem;border:1px solid #e2e8f0">بیمه و سفر</td>
<td style="padding:0.5rem;border:1px solid #e2e8f0">متغیر</td></tr>
</tbody>
</table>
<p>{_pick(slug, 'cost', ['صرفه‌جویی: اپلای هدفمند به ۴–۶ دانشگاه کافی است؛ پراکندگی بی‌هدف هزینه را چند برابر می‌کند.', 'بورسیه جزئی یا دستیار آموزشی می‌تواند بخشی از هزینه را پوشش دهد.'])}</p>
"""


def _section_mistakes(slug: str) -> str:
    return f"""
<h2>اشتباهات رایج متقاضیان ایرانی</h2>
<ul>
<li>ارائه تمکن مالی ناگهانی یا غیرقابل توضیح</li>
<li>SOP کپی‌شده یا نامرتبط با رشته</li>
<li>مخفی کردن ریجکتی قبلی ویزا</li>
<li>ترجمه غیررسمی یا مغایرت نام در مدارک</li>
<li>انتخاب دانشگاه غیرمعتبر یا برنامه نامرتبط بدون توجیه</li>
<li>شروع دیر هنگام در فصل پیک (پاییز)</li>
<li>اتکا به اطلاعات قدیمی قبل از {YEAR}</li>
</ul>
<p>{_pick(slug, 'mist', ['یک اشتباه کوچک در فرم ویزا می‌تواند ماه‌ها تأخیر ایجاد کند.', 'هماهنگی SOP ویزا با SOP دانشگاه و CV حیاتی است.'])}</p>
"""


def _section_deep_dive(article: dict, prof: dict) -> str:
    """بخش اختصاصی بر اساس کلاستر."""
    cluster = article.get("cluster", "")
    title = article["title"]
    slug = article["slug"]
    parts: list[str] = [f"<h2>توضیح تخصصی: {_h(title)}</h2>"]

    if cluster == "کشورمحور":
        parts.append(
            _p(
                f"برای تحصیل در {_h(prof['en'])} باید هم‌راستایی بین رشته قبلی، زبان، بودجه و "
                f"افق اقامت بعد از تحصیل دیده شود.",
                f"شهرهای پرتقاضا مانند {_h(prof['cities'])} فرصت شغلی بیشتری دارند اما اجاره بالاتر است.",
                _pick(
                    slug,
                    "country",
                    [
                        "استان یا ایالت مناسب را بر اساس شهریه، آب‌وهوا و PNP انتخاب کنید.",
                        "دانشگاه را فقط از رتبه انتخاب نکنید؛ برنامه Co-op و شبکه صنعتی مهم است.",
                    ],
                ),
            )
        )
    elif cluster == "آموزشی":
        parts.append(
            _p(
                "مدارک اپلای باید یک داستان منسجم بسازند: هدف تحصیلی، تجربه قبلی، "
                "و برنامه شغلی پس از فارغ‌التحصیلی.",
                "هر نامه (SOP، LoR، Cover Letter) نقش متفاوتی دارد؛ تکرار محتوا بین آن‌ها اشتباه است.",
                "فایل PDF باکیفیت، نام‌گذاری استاندارد و آرشیو نسخه‌ها برای پیگیری ضروری است.",
            )
        )
    elif cluster == "مشکل‌محور":
        parts.append(
            _p(
                "اگر قبلاً ریجکت شده‌اید، تحلیل دقیق نامه ریجکت (در صورت وجود) اولویت اول است.",
                "اصلاح پرونده باید مستند باشد: تمکن واقعی، انگیزه بازگشت یا مسیر شغلی شفاف.",
                "درخواست مجدد بدون تغییر معنادار معمولاً به همان نتیجه می‌رسد.",
            )
        )
    elif cluster == "هزینه":
        parts.append(
            _p(
                "بودجه‌بندی ۱۲ ماهه را قبل از اپلای بنویسید: شهریه، اجاره، غذا، بیمه، حمل‌ونقل، تمکن.",
                "درآمد کار دانشجویی را خوش‌بینانه لحاظ نکنید؛ آن را پشتوانه اضافی بدانید.",
                "نرخ ارز را در سناریوی بدتر (۲۰٪ افزایش) هم تست کنید.",
            )
        )
    elif cluster == "مقایسه‌ای":
        parts.append(
            _p(
                "در مقایسه کشورها، معیارهای وزن‌دار تعریف کنید: هزینه، زبان، اقامت، بازار کار رشته شما.",
                "کشور ارزان‌تر همیشه بهترین انتخاب نیست اگر محدودیت کار یا زبان مانع شود.",
                "برای برخی رشته‌ها یک کشور به‌وضوح برتر است — ارزیابی تخصصی کمک می‌کند.",
            )
        )
    else:
        parts.append(
            _p(
                f"موضوع این مقاله در چارچوب مهاجرت تحصیلی {YEAR} بررسی می‌شود.",
                "ترکیب مشاوره تخصصی و آماده‌سازی شخصی بهترین نتیجه را می‌دهد.",
            )
        )

    parts.append(
        f"""
<h3>نکات ویژه {YEAR}</h3>
<ul>
<li>زمان پردازش ویزا در فصل پیک طولانی‌تر است</li>
<li>برخی کشورها سقف پذیرش یا الزامات جدید دارند</li>
<li>هوش مصنوعی در نوشتن SOP بدون ویرایس انسانی خطرناک است</li>
<li>گواهی‌های جعلی منجر به ممنوعیت چندساله می‌شود</li>
</ul>
"""
    )
    return "\n".join(parts)


def _faq_items(article: dict, prof: dict) -> list[tuple[str, str]]:
    title = article["title"]
    cat = article.get("category", "مهاجرت تحصیلی")
    slug = article["slug"]
    return [
        (
            f"آیا {title} برای ایرانیان در {YEAR} امکان‌پذیر است؟",
            _pick(
                slug,
                "faq1",
                [
                    f"بله، مشروط بر پرونده کامل و واقع‌بینانه. قوانین {_h(prof['en'])} را دقیق بررسی کنید.",
                    "بسیاری از متقاضیان موفق با برنامه‌ریزی ۹–۱۲ ماهه به نتیجه رسیده‌اند.",
                ],
            ),
        ),
        (
            f"حداقل مدرک زبان چیست؟",
            f"معمولاً {_h(prof['lang'])}. برخی مسیرهای Pathway یا پذیرش مشروط وجود دارد. "
            f"اگر نمره زبان نزدیک حد نصاب است، بازنویسی SOP و انتخاب دانشگاه مناسب‌تر "
            f"گاهی جبران می‌کند؛ اما ادعای نمره غیرواقعی خطرناک است.",
        ),
        (
            "تمکن مالی چقدر باید باشد؟",
            "به کشور، شهر و همراه بستگی دارد. جدول هزینه همین مقاله نقطه شروع است؛ "
            "برای پرونده شخصی ارزیابی بگیرید. تمکن باید منطقی با شغل خانواده، سپرده‌ها "
            "و تاریخچه حساب هم‌خوان باشد؛ واریزهای ناگهانی بدون توضیح پرچم قرمز است.",
        ),
        (
            f"ریجکتی ویزا در {cat} چه اقدامی نیاز دارد؟",
            "تحلیل دلیل، اصلاح مستندات، تقویت انگیزه و در صورت نیاز تغییر مقصد یا مقطع. "
            "درخواست مجدد بدون تغییر معنا‌دار توصیه نمی‌شود.",
        ),
        (
            "آیا می‌توان همزمان به چند کشور اپلای کرد؟",
            "بله، اما SOP و استراتژی هر کشور باید اختصاصی باشد؛ کپی یکسان ریسک دارد.",
        ),
        (
            f"کار دانشجویی در {_h(prof['en'])} چگونه است؟",
            f"{_h(prof['work'])}. قوانین را از منابع رسمی بخوانید.",
        ),
        (
            "چقدر طول می‌کشد کل فرآیند؟",
            _pick(
                slug,
                "faq7",
                [
                    "معمولاً ۶ تا ۱۸ ماه از آماده‌سازی تا ورود، بسته به کشور و فصل.",
                    "فصل پاییز بیشترین تقاضا را دارد؛ زودتر شروع کنید.",
                ],
            ),
        ),
        (
            f"چرا {INSTITUTE}؟",
            f"{INSTITUTE} در مسیر انتخاب مقصد، تکمیل مدارک، اپلای و آماده‌سازی ویزا "
            f"همراه متقاضی است. ارزیابی اولیه رایگان از طریق سایت انجام می‌شود.",
        ),
    ]


def _section_faq(article: dict, prof: dict) -> str:
    items = _faq_items(article, prof)
    html = [f"<h2>سوالات متداول (FAQ)</h2>"]
    for q, a in items:
        html.append(f"<h3>{_h(q)}</h3>\n<p>{a}</p>")
    return "\n".join(html)


def _conclusion(article: dict) -> str:
    title = article["title"]
    return f"""
<h2>جمع‌بندی</h2>
{_p(
    f"«{_h(title)}» در {YEAR} همچنان یکی از جستجوهای مهم متقاضیان ایرانی است. "
    f"اگر پرونده شفاف، مدارک اصیل و برنامه زمانی واقع‌بینانه باشد، مسیر قابل مدیریت است.",
    f"قبل از پرداخت هزینه‌های سنگین اپلای، از ارزیابی رایگان {INSTITUTE} استفاده کنید "
    f"تا گزینه‌های منطقی را ببینید.",
)}
{_cta_block()}
<p><em>یادآوری:</em> قوانین مهاجرتی تغییر می‌کنند؛ همیشه منابع رسمی را هم‌زمان با این راهنما بخوانید.</p>
"""


def _extra_paragraphs(slug: str, prof: dict, n: int) -> str:
    """پاراگراف‌های تکمیلی برای رساندن به حداقل کلمه."""
    pool = [
        f"شهر {_h(prof['cities'])} برای برخی رشته‌ها فرصت‌های شغلی ویژه دارد.",
        "ارتباط با فارغ‌التحصیلان همان رشته قبل از اپلای بسیار مفید است.",
        "بیمه دانشجویی را از روز اول جدی بگیرید.",
        "اسکان موقت برای هفته‌های اول ورود برنامه‌ریزی کنید.",
        "حساب بانکی بین‌المللی و کارت مناسب سفر را زودتر آماده کنید.",
        "با دفتر بین‌الملل دانشگاه از همان هفته اول در ارتباط باشید.",
        "شرکت در انجمن‌های دانشجویی ایرانی و بین‌المللی سرعت سازگاری را بالا می‌برد.",
        "برای ویزای همراه، تمکن جداگانه و مدارک ازدواج/فرزند لازم است.",
        "گپ تحصیلی را با کار، دوره یا توضیح شفاف پوشش دهید.",
        "رتبه دانشگاه تنها معیار نیست؛ Co-op و ارتباط با صنعت را بسنجید.",
    ]
    out: list[str] = []
    h = int(hashlib.md5(slug.encode()).hexdigest(), 16)
    for i in range(n):
        out.append(pool[(h + i) % len(pool)])
    return _p(*out)


def generate_blog_article(article: dict) -> dict:
    """
    برمی‌گرداند: content, excerpt, meta_title, meta_description, meta_keywords
    """
    prof = profile_for(article.get("category", ""))
    slug = article["slug"]
    title = article["title"]

    sections = [
        _intro(article, prof),
        _section_conditions(article, prof),
        _section_deep_dive(article, prof),
        _section_pros_cons(prof, slug),
        _section_steps(article, prof),
        _section_costs(prof, slug),
        _section_mistakes(slug),
        _section_faq(article, prof),
        _conclusion(article),
    ]
    content = "\n".join(sections)

    # حداقل ~۱۵۰۰ کلمه
    wc = word_count(content)
    extra_round = 0
    while wc < 1520 and extra_round < 12:
        content += _extra_paragraphs(slug, prof, 6)
        content += f"<h3>نکته تکمیلی {extra_round + 1} برای متقاضیان {YEAR}</h3>\n" + _p(
            _pick(
                slug,
                f"ex{extra_round}",
                [
                    "برنامه‌ریزی مالی خانواده را شفاف کنید تا تمکن قابل دفاع باشد؛ "
                    "منبع درآمد و تاریخ واریز باید با سوابق بانکی هم‌خوان باشد.",
                    "برای مصاحبه ویزا پاسخ‌های کوتاه و مستند آماده کنید؛ "
                    "از پاسخ‌های کلی و کپی‌شده پرهیز کنید.",
                    "لیست دانشگاه‌های هدف را به سه دسته dream, match, safe تقسیم کنید "
                    "تا ریسک بدون پذیرش کاهش یابد.",
                    "با Alumni یا دانشجویان فعلی همان رشته در مقصد تماس بگیرید؛ "
                    "اطلاعات واقعی از زندگی روزانه ارزشمند است.",
                ],
            ),
            _pick(
                slug,
                f"exb{extra_round}",
                [
                    "اگر در حال کار هستید، نامه اشتغال و توجیه گپ را همزمان آماده کنید.",
                    "برای همراه خانواده، از ابتدا بودجه جدا و مدارک ازدواج/تولد را نظم دهید.",
                ],
            ),
        )
        wc = word_count(content)
        extra_round += 1

    excerpt = article.get("meta_description") or (
        f"راهنمای {YEAR} درباره {title} — شرایط، هزینه، ویزا و FAQ برای متقاضیان ایرانی."
    )
    if len(excerpt) > 400:
        excerpt = excerpt[:397] + "…"

    meta_title = (article.get("meta_title") or title)[:200]
    meta_desc = (article.get("meta_description") or excerpt)[:500]
    meta_kw = article.get("keywords", "")[:300]

    return {
        "content": content.strip(),
        "excerpt": excerpt.strip(),
        "meta_title": meta_title,
        "meta_description": meta_desc.strip(),
        "meta_keywords": meta_kw,
        "word_count": wc,
    }
