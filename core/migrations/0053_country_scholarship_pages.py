# Country scholarship guide pages + Canada bachelor seed

from decimal import Decimal

from django.db import migrations, models
import django.db.models.deletion


def seed_canada_bachelor_scholarships(apps, schema_editor):
    StudyCountry = apps.get_model("core", "StudyCountry")
    Guide = apps.get_model("core", "CountryScholarshipGuide")
    Scholarship = apps.get_model("core", "CountryScholarship")

    country = StudyCountry.objects.filter(code="canada").first()
    if not country:
        return

    country.scholarship_info = (
        "<p>کانادا برای دانشجویان بین‌المللی بورسیه‌های ورودی (Entrance)، "
        "برنامه‌های مبتنی بر شایستگی و چند بورسیه تمام‌هزینه در دانشگاه‌های برتر دارد. "
        "بسیاری از جوایز <strong>خودکار</strong> بر اساس معدل پذیرش ارزیابی می‌شوند؛ "
        "برخی دیگر نیاز به نامزدی مدرسه یا درخواست جداگانه دارند.</p>"
        "<p><a href=\"/کشور/canada/بورسیه/?target_degree=bachelor\">"
        "مشاهده راهنمای کامل بورسیه کارشناسی کانادا</a> — شامل مبالغ، مهلت‌ها و لینک رسمی هر برنامه.</p>"
    )
    country.save(update_fields=["scholarship_info"])

    guide, _ = Guide.objects.update_or_create(
        country=country,
        target_degree="bachelor",
        defaults={
            "headline": "بورسیه کارشناسی کانادا برای دانشجویان بین‌المللی",
            "intro": (
                "برنامه‌های بورسیه کارشناسی کانادا از جوایز خودکار چندهزار دلاری تا "
                "بورسیه‌های تمام‌هزینه چهارساله در دانشگاه تورنتو و UBC متغیرند. "
                "در این صفحه مهم‌ترین برنامه‌های معتبر ۲۰۲۵–۲۰۲۶ با مبالغ تقریبی، "
                "شرایط و مهلت‌های رسمی جمع‌آوری شده است."
            ),
            "overview": (
                "<h3>انواع بورسیه کارشناسی در کانادا</h3>"
                "<ul>"
                "<li><strong>Entrance / Merit:</strong> بر اساس معدل دبیرستان؛ اغلب بدون درخواست جدا "
                "(مثل کارلتون، واترلو، آلبرتا).</li>"
                "<li><strong>بورسیه‌های تمام‌هزینه:</strong> شهریه، اقامت و هزینه‌های جانبی — "
                "بسیار رقابتی؛ معمولاً نیاز به نامزدی مدرسه (Pearson) یا پرونده مالی قوی (UBC International Scholars).</li>"
                "<li><strong>بورسیه مبتنی بر رهبری و نیاز مالی:</strong> York Global Leader of Tomorrow، "
                "برنامه بین‌المللی UBC.</li>"
                "</ul>"
                "<h3>زمان‌بندی کلی اپلای ۲۰۲۶</h3>"
                "<p>برای شروع تحصیل <strong>سپتامبر ۲۰۲۶</strong>، پذیرش دانشگاه را معمولاً "
                "از <strong>اکتبر تا ژانویه</strong> ارسال کنید. بورسیه‌های نیازمند نامزدی مدرسه "
                "(مثل Pearson) مهلت‌های زودتری در <strong>اکتبر–نوامبر ۲۰۲۵</strong> دارند. "
                "همیشه صفحه رسمی هر دانشگاه را قبل از ارسال مدارک بررسی کنید.</p>"
                "<p><em>مبالغ به دلار کانادا (CAD) است مگر خلاف آن ذکر شود.</em></p>"
            ),
            "application_guide": (
                "<h3>مراحل پیشنهادی</h3>"
                "<ol>"
                "<li>لیست ۵–۸ دانشگاه DLI متناسب با معدل و بودجه تهیه کنید.</li>"
                "<li>برای هر دانشگاه جدول بورسیه‌ها را بخوانید: خودکار است یا فرم جدا دارد؟</li>"
                "<li>اگر Pearson یا برنامه مشابه مدنظر است، از مشاور مدرسه برای <strong>نامزدی</strong> "
                "حداقل ۲ ماه زودتر اقدام کنید.</li>"
                "<li>مدارک مالی (در صورت نیاز) و رزومه فعالیت‌های داوطلبانه را آماده کنید.</li>"
                "<li>پس از پذیرش، برای Study Permit و اثبات تمکن مالی برنامه‌ریزی کنید — "
                "بورسیه جایگزین تمکن ویزا نیست مگر نامه رسمی پوشش کامل داشته باشید.</li>"
                "</ol>"
                "<h3>اشتباهات رایج</h3>"
                "<ul>"
                "<li>فرض کردن همه بورسیه‌ها خودکار هستند.</li>"
                "<li>از دست دادن مهلت نامزدی مدرسه برای Pearson.</li>"
                "<li>اعتماد به واسطه‌های غیررسمی (دانشگاه تورنتو درباره Pearson هشدار تقلب داده است).</li>"
                "</ul>"
            ),
            "search_keywords": (
                "بورسیه کانادا, بورسیه کارشناسی کانادا, Pearson, UBC International Scholars, "
                "entrance scholarship canada, بورسیه دانشجویان بین‌المللی کانادا"
            ),
            "meta_title": "بورسیه کارشناسی کانادا ۲۰۲۶ | راهنمای کامل دانشجویان بین‌المللی",
            "meta_description": (
                "راهنمای بورسیه کارشناسی کانادا: Pearson، UBC International Scholars، "
                "Carleton، Waterloo، York و مهلت‌های ۲۰۲۵–۲۰۲۶ با لینک رسمی."
            ),
            "meta_keywords": (
                "بورسیه کانادا, بورسیه کارشناسی کانادا, Lester B Pearson, "
                "بورسیه دانشگاه تورنتو, UBC scholarship, entrance scholarship"
            ),
            "is_active": True,
        },
    )

    programs = [
        {
            "slug": "lester-b-pearson",
            "program_key": "ca-pearson",
            "name": "بورسیه Lester B. Pearson (دانشگاه تورنتو)",
            "provider": "University of Toronto",
            "coverage": "شهریه، کتاب، هزینه‌های جانبی و اقامت کامل — ۴ سال",
            "eligibility": (
                "<p>دانشجوی بین‌المللی (غیرکانادایی با نیاز به Study Permit)؛ "
                "در سال آخر دبیرستان ۲۰۲۵/۲۰۲۶ یا فارغ‌التحصیل از ژوئن ۲۰۲۵ به بعد؛ "
                "شروع تحصیل در U of T از <strong>سپتامبر ۲۰۲۶</strong>. "
                "دانشجویان قبلاً مشغول به تحصیلات دانشگاهی واجد شرایط نیستند.</p>"
                "<p>هر مدرسه فقط <strong>یک</strong> دانشجو در سال می‌تواند نامزد کند. "
                "حدود ۳۷ بورسیه‌دار در سال.</p>"
            ),
            "deadlines": (
                "نامزدی مدرسه: ۱۰ اکتبر ۲۰۲۵ | اپلای پذیرش U of T: ۱۷ اکتبر ۲۰۲۵ | "
                "فرم Pearson: ۷ نوامبر ۲۰۲۵ (ورود ۲۰۲۶)"
            ),
            "official_url": "https://future.utoronto.ca/pearson-scholarships",
            "min_gpa": Decimal("17.50"),
            "lang_requirement": "IELTS 7+ یا معادل (بسته به برنامه)",
            "highlights": "یکی از بزرگ‌ترین بورسیه‌های بین‌المللی کانادا\n"
            "پوشش کامل ۴ ساله در دانشگاه تورنتو\n"
            "نیاز به نامزدی رسمی مدرسه دبیرستان",
            "tags": "تمام‌هزینه, کارشناسی, رقابتی, تورنتو",
            "is_featured": True,
            "order": 1,
        },
        {
            "slug": "ubc-international-scholars",
            "program_key": "ca-ubc-isp",
            "name": "برنامه International Scholars (UBC)",
            "provider": "University of British Columbia",
            "coverage": "شهریه، اقامت و هزینه‌های تحصیلی — بر اساس نیاز مالی",
            "eligibility": (
                "<p>دانشجوی بین‌المللی با معدل تقریباً تمام A، "
                "<strong>نیاز مالی قابل اثبات</strong> و سابقه رهبری/خدمت اجتماعی. "
                "ورود مستقیم از دبیرستان معتبر؛ اولین مدرک کارشناسی.</p>"
                "<p>چهار دسته: Karen McKellin، Donald Wehrung، International Impact، "
                "Vantage One Excellence. با اپلای این برنامه، جوایز merit جداگانه UBC بررسی نمی‌شود.</p>"
            ),
            "deadlines": "اپلای ۲۰۲۶ بسته شد؛ اطلاعات ورود ۲۰۲۷ از تابستان ۲۰۲۶ در سایت UBC",
            "official_url": "https://you.ubc.ca/financial-planning/scholarships-awards-international-students/international-scholars/",
            "min_gpa": Decimal("17.00"),
            "lang_requirement": "استاندارد زبان UBC یا مسیر Vantage College",
            "highlights": "پوشش معنادار برای دانشجویان نیازمند\n"
            "مشاوره و کارگاه‌های اختصاصی Scholars\n"
            "بیش از ۵۶۰ Scholar از ۲۰۰۱",
            "tags": "تمام‌هزینه, نیاز مالی, رهبری, ونکوور",
            "is_featured": True,
            "order": 2,
        },
        {
            "slug": "york-global-leader",
            "program_key": "ca-york-glot",
            "name": "Global Leader of Tomorrow (York University)",
            "provider": "York University",
            "coverage": "۲۰٬۰۰۰ دلار کانادا در سال — حداکثر ۸۰٬۰۰۰ در ۴ سال",
            "eligibility": (
                "<p>دانشجوی بین‌المللی سال اول؛ فارغ‌التحصیل دبیرستان در ۲ سال اخیر؛ "
                "معدل حداقل A (حدود ۸۰٪)؛ فعالیت در خدمت اجتماعی، هنر یا ورزش. "
                "برنامه‌های واجد شرایط در فاکولته‌های مشخص York.</p>"
            ),
            "deadlines": "معمولاً میانه فوریه (برای ورود بعدی؛ سال تحصیلی را در سایت York بررسی کنید)",
            "official_url": "https://futurestudents.yorku.ca/financing-your-degree/international-scholarships",
            "min_gpa": Decimal("16.00"),
            "lang_requirement": "شرط زبان پذیرش York",
            "highlights": "تمدید سالانه با عملکرد تحصیلی مناسب\n"
            "ترجیح با نیاز مالی\n"
            "حدود ۲–۴ جایزه در سال",
            "tags": "رهبری, تمدیدشونده, تورنتو",
            "is_featured": True,
            "order": 3,
        },
        {
            "slug": "carleton-presidents-welcome",
            "program_key": "ca-carleton-pwa",
            "name": "President's Welcome Award (Carleton)",
            "provider": "Carleton University",
            "coverage": "۲٬۰۰۰ تا ۵٬۰۰۰ دلار کانادا — یک‌باره (ورود ۲۰۲۶)",
            "eligibility": (
                "<p>دانشجوی بین‌المللی ورود مستقیم از دبیرستان به کارشناسی؛ "
                "بر اساس معدل پذیرش — <strong>بدون درخواست جدا</strong>.</p>"
            ),
            "deadlines": "خودکار با پذیرش سپتامبر ۲۰۲۶",
            "official_url": "https://admissions.carleton.ca/presidents-welcome-award-for-international-students/",
            "min_gpa": Decimal("15.00"),
            "lang_requirement": "IELTS 6.5+ یا معادل",
            "highlights": "ارزیابی خودکار\n"
            "مناسب پرونده‌های با معدل خوب",
            "tags": "خودکار, بین‌المللی, اتاوا",
            "is_featured": False,
            "order": 4,
        },
        {
            "slug": "carleton-entrance-renewable",
            "program_key": "ca-carleton-entrance",
            "name": "بورسیه ورودی تمدیدشونده Carleton",
            "provider": "Carleton University",
            "coverage": (
                "بر اساس معدل پذیرش: ۹۵–۱۰۰٪ → ۴٬۰۰۰/سال (تا ۱۶٬۰۰۰) | "
                "۹۰–۹۴.۹ → ۳٬۰۰۰/سال | ۸۵–۸۹.۹ → ۲٬۰۰۰ | ۸۰–۸۴.۹ → ۱٬۰۰۰"
            ),
            "eligibility": (
                "<p>ورود مستقیم کارشناسی؛ تمدید با GPA سالانه ۱۰.۰ (معادل A-).</p>"
            ),
            "deadlines": "خودکار با پذیرش",
            "official_url": "https://carleton.ca/awards/awards/scholarships/entrance-scholarships/",
            "min_gpa": Decimal("16.00"),
            "lang_requirement": "شرط زبان پذیرش Carleton",
            "highlights": "ساختار شفاف بر اساس درصد معدل\n"
            "قابل تمدید تا ۴ سال",
            "tags": "خودکار, مبتنی بر معدل",
            "is_featured": False,
            "order": 5,
        },
        {
            "slug": "waterloo-international-entrance",
            "program_key": "ca-waterloo-intl",
            "name": "International Student Entrance Scholarship (Waterloo)",
            "provider": "University of Waterloo",
            "coverage": "۱۰٬۰۰۰ دلار کانادا — یک‌باره (ورود از سپتامبر ۲۰۲۶)",
            "eligibility": (
                "<p>دانشجوی بین‌المللی کارشناسی تمام‌وقت؛ "
                "قابل ترکیب با سایر بورسیه‌های ورودی. ارزیابی خودکار.</p>"
            ),
            "deadlines": "خودکار — پذیرش به‌موقع برای سپتامبر ۲۰۲۶",
            "official_url": "https://uwaterloo.ca/future-students/node/706",
            "min_gpa": Decimal("16.50"),
            "lang_requirement": "شرط زبان Waterloo",
            "highlights": "۱۰٬۰۰۰ دلار اختصاصی بین‌المللی‌ها\n"
            "بدون فرم جدا",
            "tags": "خودکار, بین‌المللی",
            "is_featured": False,
            "order": 6,
        },
        {
            "slug": "waterloo-presidents-distinction",
            "program_key": "ca-waterloo-psd",
            "name": "President's Scholarship of Distinction (Waterloo)",
            "provider": "University of Waterloo",
            "coverage": "۲٬۰۰۰ دلار ورودی + فرصت جوایز تجربه/پژوهش ۱٬۵۰۰ دلاری",
            "eligibility": (
                "<p>میانگین پذیرش اوایل مه ≥ ۹۵٪؛ اولین ورود به دانشگاه. خودکار.</p>"
            ),
            "deadlines": "خودکار",
            "official_url": "https://uwaterloo.ca/undergraduate-entrance-awards/awards/university-waterloo-presidents-scholarship-distinction",
            "min_gpa": Decimal("17.50"),
            "lang_requirement": "شرط زبان Waterloo",
            "highlights": "برای معدل‌های بسیار بالا\n"
            "امکان جوایز تکمیلی پس از سال اول",
            "tags": "خودکار, شایستگی",
            "is_featured": False,
            "order": 7,
        },
        {
            "slug": "alberta-entrance",
            "program_key": "ca-alberta-entrance",
            "name": "بورسیه‌های ورودی University of Alberta",
            "provider": "University of Alberta",
            "coverage": "متنوع — از جوایز مبتنی بر پذیرش تا درخواست جدا (بسته به برنامه)",
            "eligibility": (
                "<p>بسیاری از جوایز ورودی <strong>خودکار</strong> با پذیرش بررسی می‌شوند؛ "
                "برخی نیاز به اپلیکیشن جدا در پورتال بورسیه دارند.</p>"
            ),
            "deadlines": "اپلیکیشن بورسیه: ۱ اکتبر ۲۰۲۵ – ۱۰ ژانویه ۲۰۲۶ (ورود ۲۰۲۶)",
            "official_url": "https://www.ualberta.ca/en/undergraduate-admissions/tuition-and-scholarships/entrance-scholarships/index.html",
            "min_gpa": Decimal("15.50"),
            "lang_requirement": "IELTS 6.5+ یا معادل",
            "highlights": "ترکیب خودکار و درخواستی\n"
            "مناسب پرونده‌های متوسط تا قوی",
            "tags": "خودکار, درخواست جدا",
            "is_featured": False,
            "order": 8,
        },
        {
            "slug": "mcgill-entrance",
            "program_key": "ca-mcgill-entrance",
            "name": "بورسیه‌های ورودی McGill",
            "provider": "McGill University",
            "coverage": "جوایز merit ورودی — مبلغ بسته به دانشکده و معدل",
            "eligibility": (
                "<p>دانشجوی بین‌المللی سال اول؛ ارزیابی بر اساس مدارک تحصیلی و "
                "در برخی موارد درخواست جدا. جزئیات در صفحه Student Aid McGill.</p>"
            ),
            "deadlines": "هم‌زمان با مهلت پذیرش — برنامه‌های محدود ممکن است زودتر بسته شوند",
            "official_url": "https://www.mcgill.ca/studentaid/scholarships-aid/future-undergrads/entrance-scholarships",
            "min_gpa": Decimal("16.00"),
            "lang_requirement": "IELTS 6.5+ یا معادل",
            "highlights": "دانشگاه برتر مونترال\n"
            "تنوع جوایز دانشکده‌ای",
            "tags": "شایستگی, مونترال",
            "is_featured": False,
            "order": 9,
        },
        {
            "slug": "entrance-general",
            "program_key": "ca-entrance",
            "name": "بورسیه‌های ورودی سایر دانشگاه‌ها (Entrance Scholarships)",
            "provider": "دانشگاه‌های کانادا",
            "coverage": "معمولاً ۱٬۰۰۰ تا ۲۰٬۰۰۰ دلار در سال اول یا تمدیدشونده",
            "eligibility": (
                "<p>اکثر دانشگاه‌های DLI جوایز merit ورودی دارند که با معدل، "
                "فعالیت‌های فوق‌برنامه یا مقاله انگیزشی ارزیابی می‌شود. "
                "حتماً صفحه Financial Aid هر دانشگاه را بخوید.</p>"
            ),
            "deadlines": "متفاوت — معمولاً هم‌زمان یا کمی بعد از مهلت پذیرش",
            "official_url": "https://www.educanada.ca/scholarships-bourses/non_can/index.aspx?lang=eng",
            "min_gpa": Decimal("15.00"),
            "lang_requirement": "IELTS 6.0+ بسته به دانشگاه",
            "highlights": "گسترده‌ترین دسته بورسیه\n"
            "بسیاری خودکار هستند",
            "tags": "کارشناسی, مبتنی بر معدل",
            "is_featured": False,
            "order": 10,
        },
    ]

    for item in programs:
        Scholarship.objects.update_or_create(
            guide=guide,
            slug=item["slug"],
            defaults={**item, "is_active": True},
        )


def unseed_canada_bachelor(apps, schema_editor):
    StudyCountry = apps.get_model("core", "StudyCountry")
    Guide = apps.get_model("core", "CountryScholarshipGuide")
    country = StudyCountry.objects.filter(code="canada").first()
    if country:
        Guide.objects.filter(country=country, target_degree="bachelor").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0052_blog_author_model"),
    ]

    operations = [
        migrations.CreateModel(
            name="CountryScholarshipGuide",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "target_degree",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("", "همه مقاطع"),
                            ("bachelor", "کارشناسی"),
                            ("master", "کارشناسی ارشد"),
                            ("phd", "دکتری"),
                        ],
                        default="",
                        help_text="خالی = همه مقاطع؛ برای صفحه کارشناسی «bachelor» انتخاب کنید.",
                        max_length=20,
                        verbose_name="مقطع",
                    ),
                ),
                ("headline", models.CharField(max_length=300, verbose_name="تیتر صفحه")),
                ("intro", models.TextField(verbose_name="مقدمه")),
                (
                    "overview",
                    models.TextField(
                        blank=True,
                        help_text="متن غنی درباره انواع بورسیه، زمان‌بندی کلی و نکات مهم.",
                        verbose_name="راهنمای کلی بورسیه",
                    ),
                ),
                (
                    "application_guide",
                    models.TextField(
                        blank=True,
                        help_text="مراحل پیشنهادی، مدارک و اشتباهات رایج.",
                        verbose_name="راهنمای اپلای بورسیه",
                    ),
                ),
                ("search_keywords", models.TextField(blank=True, verbose_name="کلمات کلیدی جستجو")),
                ("meta_title", models.CharField(blank=True, max_length=200, verbose_name="عنوان SEO")),
                ("meta_description", models.TextField(blank=True, verbose_name="توضیح متا SEO")),
                ("meta_keywords", models.CharField(blank=True, max_length=300, verbose_name="کلمات کلیدی SEO")),
                ("is_active", models.BooleanField(default=True, verbose_name="فعال")),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "country",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="scholarship_guides",
                        to="core.studycountry",
                        verbose_name="کشور",
                    ),
                ),
            ],
            options={
                "verbose_name": "راهنمای بورسیه کشور",
                "verbose_name_plural": "راهنماهای بورسیه کشورها",
                "db_table": "core_countryscholarshipguide",
                "ordering": ["country__order", "country_id", "target_degree"],
            },
        ),
        migrations.CreateModel(
            name="CountryScholarship",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("slug", models.SlugField(max_length=120, verbose_name="شناسه")),
                (
                    "program_key",
                    models.SlugField(
                        blank=True,
                        help_text="اختیاری؛ برای همگام‌سازی با پیشنهاد ارزیابی (مثلاً ca-pearson).",
                        max_length=80,
                        verbose_name="کلید کاتالوگ",
                    ),
                ),
                ("name", models.CharField(max_length=250, verbose_name="نام بورسیه")),
                ("provider", models.CharField(max_length=200, verbose_name="ارائه‌دهنده")),
                ("coverage", models.CharField(max_length=300, verbose_name="پوشش مالی (خلاصه)")),
                ("eligibility", models.TextField(blank=True, verbose_name="شرایط واجد شرایط بودن")),
                ("deadlines", models.CharField(blank=True, max_length=400, verbose_name="مهلت‌ها")),
                ("official_url", models.URLField(blank=True, max_length=500, verbose_name="لینک رسمی")),
                (
                    "min_gpa",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        max_digits=4,
                        null=True,
                        verbose_name="حداقل معدل (ایرانی ۲۰)",
                    ),
                ),
                ("lang_requirement", models.CharField(blank=True, max_length=200, verbose_name="شرط زبان")),
                (
                    "highlights",
                    models.TextField(
                        blank=True,
                        help_text="هر خط یک مورد.",
                        verbose_name="نکات برجسته",
                    ),
                ),
                (
                    "tags",
                    models.CharField(
                        blank=True,
                        help_text="با کاما جدا کنید.",
                        max_length=300,
                        verbose_name="برچسب‌ها",
                    ),
                ),
                ("is_featured", models.BooleanField(default=False, verbose_name="ویژه (بالای لیست)")),
                ("order", models.PositiveSmallIntegerField(default=0, verbose_name="ترتیب")),
                ("is_active", models.BooleanField(default=True, verbose_name="فعال")),
                (
                    "guide",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="scholarships",
                        to="core.countryscholarshipguide",
                        verbose_name="راهنمای کشور",
                    ),
                ),
            ],
            options={
                "verbose_name": "برنامه بورسیه",
                "verbose_name_plural": "برنامه‌های بورسیه",
                "db_table": "core_countryscholarship",
                "ordering": ["-is_featured", "order", "id"],
            },
        ),
        migrations.AddConstraint(
            model_name="countryscholarshipguide",
            constraint=models.UniqueConstraint(
                fields=("country", "target_degree"),
                name="core_scholarshipguide_country_degree_uniq",
            ),
        ),
        migrations.AddConstraint(
            model_name="countryscholarship",
            constraint=models.UniqueConstraint(
                fields=("guide", "slug"),
                name="core_countryscholarship_guide_slug_uniq",
            ),
        ),
        migrations.RunPython(seed_canada_bachelor_scholarships, unseed_canada_bachelor),
    ]
