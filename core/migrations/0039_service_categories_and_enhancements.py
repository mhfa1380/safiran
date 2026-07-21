# Generated for service categories, smart search, and rich seed data

from django.db import migrations, models
import django.db.models.deletion
from django.utils.text import slugify


def _unique_slug(model, base, exclude_pk=None):
    slug = base[:180] or "service"
    n = 1
    qs = model.objects.all()
    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)
    unique = slug
    while qs.filter(slug=unique).exists():
        unique = f"{slug}-{n}"
        n += 1
    return unique


def seed_service_categories_and_data(apps, schema_editor):
    Service = apps.get_model("core", "Service")
    ServiceCategory = apps.get_model("core", "ServiceCategory")

    categories = [
        (1, "moshavere-arezaye", "مشاوره و ارزیابی", "ti-headphone-alt",
         "مشاوره تخصصی، ارزیابی اولیه پرونده و انتخاب مسیر تحصیلی مناسب."),
        (2, "paziresh-apply", "پذیرش و اپلای دانشگاه", "ti-book",
         "مکاتبه با دانشگاه‌ها، نگارش مدارک و پیگیری پذیرش تا دریافت Offer."),
        (3, "visa-madarek", "ویزا و تکمیل مدارک", "ti-id-badge",
         "ترجمه رسمی، تکمیل پرونده، آمادگی مصاحبه و اخذ ویزای تحصیلی."),
        (4, "bourse-mali", "بورسیه و امور مالی", "ti-wallet",
         "برنامه‌ریزی مالی تحصیل، پیگیری بورسیه و مشاوره هزینه‌های زندگی."),
        (5, "estghrar-pasokhbane", "استقرار و پشتیبانی مقصد", "ti-world",
         "اسکان اولیه، پشتیبانی پس از ورود و همراهی در کشور مقصد."),
    ]
    cat_by_slug = {}
    for order, slug, name, icon, desc in categories:
        cat, _ = ServiceCategory.objects.get_or_create(
            slug=slug,
            defaults={
                "name": name,
                "icon": icon,
                "description": desc,
                "order": order,
                "is_active": True,
            },
        )
        cat_by_slug[slug] = cat

    services_data = [
        {
            "title": "مشاوره رایگان اولیه",
            "icon": "ti-comments-smiley",
            "category": "moshavere-arezaye",
            "order": 1,
            "featured": True,
            "keywords": "مشاوره,رایگان,جلسه,شروع,مهاجرت تحصیلی,اولیه",
            "short": "جلسه آشنایی رایگان برای بررسی شرایط، اهداف تحصیلی و معرفی مسیرهای قابل‌اتکا.",
            "description": (
                "در جلسه مشاوره رایگان اولیه، وضعیت تحصیلی، زبان، بودجه و اهداف شما بررسی می‌شود "
                "تا بتوانید با دید روشن‌تر تصمیم بگیرید. این جلسه تعهدآور نیست و فقط برای "
                "شناخت مسیر و اولویت‌بندی گام‌های بعدی طراحی شده است."
            ),
            "highlights": "بررسی رزومه و سوابق تحصیلی\nمعرفی کشورها و مسیرهای متناسب\nپاسخ به سوالات حقوقی و اجرایی\nتعیین گام بعدی بدون فشار فروش",
        },
        {
            "title": "ارزیابی تخصصی پرونده",
            "icon": "ti-clipboard",
            "category": "moshavere-arezaye",
            "order": 2,
            "featured": True,
            "keywords": "ارزیابی,فرم,امتیاز,شانس پذیرش,پرونده",
            "short": "تحلیل دقیق شانس پذیرش، نقاط قوت و ضعف پرونده با چک‌لیست اختصاصی موسسه.",
            "description": (
                "ارزیابی تخصصی شامل بررسی معدل، زبان، سابقه کاری، بودجه و رشته هدف است. "
                "خروجی این مرحله، نقشه راه شخصی‌سازی‌شده با اولویت کشورها و دانشگاه‌هاست."
            ),
            "highlights": "گزارش شفاف شانس پذیرش\nپیشنهاد کشور و رشته متناسب\nبرآورد زمان‌بندی اقدام\nهم‌راستا با فرم ارزیابی آنلاین",
        },
        {
            "title": "انتخاب کشور و مسیر تحصیلی",
            "icon": "ti-map-alt",
            "category": "moshavere-arezaye",
            "order": 3,
            "featured": False,
            "keywords": "کشور,کانادا,آلمان,چین,اسپانیا,مسیر,رشته",
            "short": "مقایسه کشورهای مقصد از نظر هزینه، بورسیه، زبان و فرصت اقامت پس از تحصیل.",
            "description": (
                "با توجه به بودجه، رشته و برنامه شغلی شما، گزینه‌های واقع‌بینانه معرفی می‌شود "
                "و مزایا و محدودیت هر مسیر (از اپلای مستقیم تا pathway) توضیح داده می‌شود."
            ),
            "highlights": "مقایسه هزینه و بورسیه\nبررسی زبان و بازار کار\nهم‌راستایی با اهداف بلندمدت\nجلوگیری از انتخاب مسیر اشتباه",
        },
        {
            "title": "مشاوره آنلاین و پیگیری پرونده",
            "icon": "ti-video-camera",
            "category": "moshavere-arezaye",
            "order": 4,
            "featured": False,
            "keywords": "آنلاین,ویدیو,پیگیری,پرونده,وضعیت",
            "short": "جلسات آنلاین منظم و گزارش پیشرفت پرونده در تمام مراحل مهاجرت تحصیلی.",
            "description": (
                "برای متقاضیان خارج از شهر یا کشور، جلسات آنلاین و کانال ارتباطی اختصاصی "
                "برقرار می‌شود تا هیچ مرحله‌ای بدون اطلاع‌رسانی باقی نماند."
            ),
            "highlights": "جلسات ویدیویی منظم\nگزارش وضعیت مرحله‌به‌مرحله\nپاسخ‌گویی در بازه کاری\nهماهنگی با تیم اجرایی",
        },
        {
            "title": "مکاتبه با دانشگاه‌ها و اساتید",
            "icon": "ti-email",
            "category": "paziresh-apply",
            "order": 5,
            "featured": True,
            "keywords": "دانشگاه,استاد,ایمیل,مکاتبه,پذیرش",
            "short": "ارتباط حرفه‌ای با دانشگاه‌ها و اساتید برای افزایش شانس پذیرش و بورسیه.",
            "description": (
                "تیم ما بر اساس رشته و پروفایل شما، لیست دانشگاه‌ها و اساتید مناسب را آماده "
                "و مکاتبات رسمی را با رعایت استانداردهای بین‌المللی انجام می‌دهد."
            ),
            "highlights": "انتخاب دانشگاه هدفمند\nنگارش ایمیل حرفه‌ای\nپیگیری پاسخ‌ها\nهماهنگی با استراتژی بورسیه",
        },
        {
            "title": "نگارش انگیزه‌نامه و رزومه تحصیلی",
            "icon": "ti-pencil-alt",
            "category": "paziresh-apply",
            "order": 6,
            "featured": False,
            "keywords": "SOP,انگیزه نامه,رزومه,CV,نگارش",
            "short": "تدوین Statement of Purpose و رزومه استاندارد مطابق الزامات دانشگاه مقصد.",
            "description": (
                "متن‌های شما با ساختار پذیرفته‌شده دانشگاه‌ها بازنویسی می‌شود تا نقاط قوت "
                "و انگیزه تحصیلی به‌صورت حرفه‌ای منتقل شود."
            ),
            "highlights": "بازبینی چندمرحله‌ای\nهماهنگ با رشته هدف\nرعایت فرمت دانشگاه\nافزایش کیفیت اپلای",
        },
        {
            "title": "ثبت اپلای و پیگیری پذیرش",
            "icon": "ti-upload",
            "category": "paziresh-apply",
            "order": 7,
            "featured": True,
            "keywords": "اپلای,ثبت نام,پورتال,پذیرش,offer",
            "short": "ثبت درخواست در پورتال‌های دانشگاهی و پیگیری تا صدور نامه پذیرش.",
            "description": (
                "از تکمیل فرم‌های آنلاین تا بارگذاری مدارک و پرداخت هزینه‌های درخواست، "
                "تمام مراحل اپلای با نظارت کارشناس انجام و پیگیری می‌شود."
            ),
            "highlights": "ثبت دقیق در پورتال‌ها\nکنترل ددلاین‌ها\nپیگیری وضعیت درخواست\nدریافت Offer Letter",
        },
        {
            "title": "تایید و تکمیل مدارک",
            "icon": "ti-files",
            "category": "visa-madarek",
            "order": 8,
            "featured": False,
            "keywords": "مدارک,ترجمه,تایید,فرم,چک لیست",
            "short": "چک‌لیست کامل مدارک تحصیلی و شخصی مطابق استاندارد سفارت و دانشگاه.",
            "description": (
                "پرونده شما قبل از ارسال نهایی، از نظر کامل بودن، ترتیب و انطباق با "
                "الزامات سفارت/دانشگاه بازبینی می‌شود تا ریسک رد یا تأخیر کاهش یابد."
            ),
            "highlights": "چک‌لیست اختصاصی\nکنترل نسخ اصل و کپی\nهماهنگی با ترجمه رسمی\nکاهش خطای پرونده",
        },
        {
            "title": "ترجمه رسمی و تایید مدارک",
            "icon": "ti-agenda",
            "category": "visa-madarek",
            "order": 9,
            "featured": False,
            "keywords": "ترجمه رسمی,تایید وزارت,سفارت,مدرک",
            "short": "هماهنگی ترجمه رسمی و احراز مدارک برای ویزا و پذیرش دانشگاه.",
            "description": (
                "مسیر ترجمه و تأیید مدارک بسته به کشور مقصد متفاوت است؛ ما فرآیند را "
                "هماهنگ می‌کنیم تا مدارک در زمان مناسب آماده شوند."
            ),
            "highlights": "هماهنگی با مترجم رسمی\nپیگیری تأییدات لازم\nآماده‌سازی بسته ویزا\nصرفه‌جویی در زمان",
        },
        {
            "title": "اخذ ویزای دانشجویی",
            "icon": "ti-id-badge",
            "category": "visa-madarek",
            "order": 10,
            "featured": True,
            "keywords": "ویزا,سفارت,تحصیلی,مصاحبه,وقت",
            "short": "تعیین وقت سفارت، آمادگی مصاحبه و پیگیری تا صدور ویزای تحصیلی.",
            "description": (
                "از تکمیل فرم‌های سفارت تا آماده‌سازی برای مصاحبه و پیگیری وضعیت ویزا، "
                "در تمام مراحل همراه شما هستیم تا با اطمینان سفر کنید."
            ),
            "highlights": "رزرو وقت سفارت\nآمادگی مصاحبه\nبررسی مدارک مالی\nپیگیری تا صدور ویزا",
        },
        {
            "title": "آمادگی مصاحبه سفارت",
            "icon": "ti-microphone",
            "category": "visa-madarek",
            "order": 11,
            "featured": False,
            "keywords": "مصاحبه,سفارت,سوالات,آمادگی,ویزا",
            "short": "شبیه‌سازی مصاحبه و آموزش پاسخ‌گویی شفاف مطابق الگوی سفارت.",
            "description": (
                "جلسات آمادگی مصاحبه شامل مرور سوالات رایج، تمرین پاسخ و بررسی "
                "مدارک مالی و تحصیلی ارائه‌شده در مصاحبه است."
            ),
            "highlights": "تمرین سوالات پرتکرار\nبازبینی مدارک مصاحبه\nافزایش اعتمادبه‌نفس\nکاهش ریسک رد ویزا",
        },
        {
            "title": "اخذ بورسیه تحصیلی",
            "icon": "ti-crown",
            "category": "bourse-mali",
            "order": 12,
            "featured": True,
            "keywords": "بورسیه,اسکالرشیپ,fund,کمک هزینه",
            "short": "شناسایی فرصت‌های بورسیه و پیگیری درخواست‌های مالی دانشگاهی.",
            "description": (
                "بورسیه‌ها بر اساس رشته، معدل و پروفایل پژوهشی متفاوت است. ما مناسب‌ترین "
                "گزینه‌ها را معرفی و در نگارش درخواست‌ها همراهی می‌کنیم."
            ),
            "highlights": "لیست بورسیه‌های متناسب\nنگارش درخواست مالی\nپیگیری نتیجه\nترکیب با پذیرش",
        },
        {
            "title": "برنامه‌ریزی مالی تحصیل",
            "icon": "ti-bar-chart",
            "category": "bourse-mali",
            "order": 13,
            "featured": False,
            "keywords": "هزینه,شهریه,زندگی,بودجه,مالی",
            "short": "برآورد هزینه تحصیل، اقامت و سپرده مالی موردنیاز سفارت/دانشگاه.",
            "description": (
                "قبل از شروع پرونده، تصویر شفافی از هزینه‌های واقعی ارائه می‌شود تا "
                "برنامه‌ریزی مالی خانواده دقیق‌تر انجام شود."
            ),
            "highlights": "برآورد شهریه و زندگی\nمحاسبه سپرده بانکی\nهم‌راستا با تعرفه خدمات\nجلوگیری از کمبود بودجه",
        },
        {
            "title": "استقرار و اسکان اولیه",
            "icon": "ti-home",
            "category": "estghrar-pasokhbane",
            "order": 14,
            "featured": True,
            "keywords": "اسکان,اقامت,خوابگاه,فرودگاه,ورود",
            "short": "هماهنگی اسکان اولیه، خوابگاه و استقبال در کشور مقصد.",
            "description": (
                "با شبکه همکاران در مقصد، برای روزهای اول ورود برنامه‌ریزی می‌شود تا "
                "فرآیند سکونت و ثبت‌نام دانشگاه روان‌تر پیش برود."
            ),
            "highlights": "رزرو اقامت موقت\nراهنمای محله و حمل‌ونقل\nهماهنگی با دانشگاه\nآرامش خانواده",
        },
        {
            "title": "پشتیبانی پس از ورود",
            "icon": "ti-support",
            "category": "estghrar-pasokhbane",
            "order": 15,
            "featured": False,
            "keywords": "پشتیبانی,بعد ورود,ثبت نام,بانک,سیم کارت",
            "short": "راهنمایی برای ثبت‌نام دانشگاه، افتتاح حساب، بیمه و امور روزمره.",
            "description": (
                "پس از ورود، سوالات عملی زیادی پیش می‌آید؛ تیم پشتیبانی برای مسائل اولیه "
                "زندگی دانشجویی در دسترس است."
            ),
            "highlights": "راهنمای ثبت‌نام دانشگاه\nافتتاح حساب و بیمه\nمعرفی منابع محلی\nکاهش استرس اولیه",
        },
        {
            "title": "ویزای همراه و خانواده",
            "icon": "ti-user",
            "category": "estghrar-pasokhbane",
            "order": 16,
            "featured": False,
            "keywords": "همراه,همسر,فرزند,ویزای تابعه,خانواده",
            "short": "مشاوره و پیگیری ویزای همراه برای همسر و فرزندان در صورت امکان.",
            "description": (
                "قوانین ویزای همراه بسته به کشور متفاوت است. شرایط شما بررسی و در صورت "
                "امکان، مسیر قانونی همراهی خانواده پیشنهاد می‌شود."
            ),
            "highlights": "بررسی قوانین کشور مقصد\nآماده‌سازی مدارک همراه\nهماهنگی با ویزای اصلی\nشفافیت در محدودیت‌ها",
        },
    ]

    for item in services_data:
        defaults = {
            "icon": item["icon"],
            "description": item["description"],
            "short_description": item["short"],
            "highlights": item["highlights"],
            "search_keywords": item["keywords"],
            "order": item["order"],
            "is_active": True,
            "is_featured": item["featured"],
            "category": cat_by_slug[item["category"]],
        }
        service, created = Service.objects.get_or_create(
            title=item["title"],
            defaults=defaults,
        )
        if not created:
            for key, val in defaults.items():
                setattr(service, key, val)
        if not service.slug:
            service.slug = _unique_slug(
                Service,
                slugify(item["title"], allow_unicode=True),
                exclude_pk=service.pk,
            )
        service.save()

    legacy_titles = [
        "مشاوره رایگان",
        "مکاتبه با دانشگاه‌ها و اساتید",
        "تایید و تکمیل مدارک",
        "اخذ ویزای دانشجویی و همراهی",
        "اخذ بورسیه",
        "استقرار در مقصد",
    ]
    Service.objects.filter(title__in=legacy_titles, category__isnull=True).update(is_active=False)


def populate_service_slugs(apps, schema_editor):
    Service = apps.get_model("core", "Service")
    for service in Service.objects.all():
        if service.slug:
            continue
        base = slugify(service.title, allow_unicode=True)[:180] or f"service-{service.pk}"
        slug = _unique_slug(Service, base, exclude_pk=service.pk)
        service.slug = slug
        service.save(update_fields=["slug"])


def reverse_seed(apps, schema_editor):
    Service = apps.get_model("core", "Service")
    Service.objects.update(category_id=None, slug="", search_keywords="", highlights="", is_featured=False, view_count=0)
    ServiceCategory = apps.get_model("core", "ServiceCategory")
    ServiceCategory.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0038_achievement_detail_seo"),
    ]

    operations = [
        migrations.CreateModel(
            name="ServiceCategory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120, verbose_name="نام دسته")),
                ("slug", models.SlugField(help_text="برای آدرس صفحه دسته", max_length=150, unique=True, verbose_name="شناسه آدرس")),
                ("description", models.TextField(blank=True, help_text="نمایش زیر عنوان دسته در صفحه خدمات", verbose_name="توضیح کوتاه")),
                ("icon", models.CharField(blank=True, help_text="کلاس آیکون Themify", max_length=60, verbose_name="آیکون")),
                ("meta_title", models.CharField(blank=True, max_length=70, verbose_name="عنوان سئو")),
                ("meta_description", models.CharField(blank=True, max_length=160, verbose_name="توضیح متا (سئو)")),
                ("order", models.PositiveSmallIntegerField(default=0, verbose_name="ترتیب نمایش")),
                ("is_active", models.BooleanField(default=True, verbose_name="فعال")),
            ],
            options={
                "verbose_name": "دسته خدمات",
                "verbose_name_plural": "دسته‌های خدمات",
                "db_table": "core_service_category",
                "ordering": ["order", "id"],
            },
        ),
        migrations.AddField(
            model_name="service",
            name="slug",
            field=models.SlugField(blank=True, help_text="برای لینک مستقیم به خدمت", max_length=200),
        ),
        migrations.AddField(
            model_name="service",
            name="highlights",
            field=models.TextField(blank=True, help_text="هر خط یک مورد", verbose_name="نکات کلیدی"),
        ),
        migrations.AddField(
            model_name="service",
            name="search_keywords",
            field=models.TextField(blank=True, help_text="کلمات مرتبط با کاما", verbose_name="کلمات کلیدی جستجو"),
        ),
        migrations.AddField(
            model_name="service",
            name="is_featured",
            field=models.BooleanField(default=False, help_text="در بخش پرطرفدار نمایش داده می‌شود", verbose_name="خدمات پرطرفدار"),
        ),
        migrations.AddField(
            model_name="service",
            name="view_count",
            field=models.PositiveIntegerField(default=0, editable=False, verbose_name="تعداد بازدید"),
        ),
        migrations.AddField(
            model_name="service",
            name="category",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="services", to="core.servicecategory", verbose_name="دسته"),
        ),
        migrations.RunPython(seed_service_categories_and_data, reverse_seed),
        migrations.RunPython(populate_service_slugs, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="service",
            name="slug",
            field=models.SlugField(blank=True, help_text="برای لینک مستقیم به خدمت", max_length=200, unique=True),
        ),
    ]
