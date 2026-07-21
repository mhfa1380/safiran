# Generated manually for course instructors and English course seed.

from django.db import migrations, models
import django.db.models.deletion
import core.models


def seed_english_course(apps, schema_editor):
    CourseInstructor = apps.get_model("core", "CourseInstructor")
    CourseInstructorResumeEntry = apps.get_model("core", "CourseInstructorResumeEntry")
    Course = apps.get_model("core", "Course")
    CourseSyllabus = apps.get_model("core", "CourseSyllabus")
    CourseFAQ = apps.get_model("core", "CourseFAQ")

    instructor, _ = CourseInstructor.objects.update_or_create(
        slug="rasoul-montazeri",
        defaults={
            "name": "رسول منتظری",
            "position": "مدرس زبان انگلیسی و آمادگی آیلتس",
            "title": "کارشناسی ارشد آموزش زبان انگلیسی (TEFL)",
            "short_bio": (
                "مدرس زبان انگلیسی با تمرکز بر مکالمه، گرامر کاربردی و آمادگی آیلتس؛ "
                "همراهی گام‌به‌گام برای ارتقای مهارت واقعی زبان."
            ),
            "bio": (
                "<p><strong>رسول منتظری</strong> مدرس زبان انگلیسی در موسسه سفیران آینده روشن است "
                "و در طراحی مسیر آموزشی، تمرکز اصلی او بر یادگیری عملی و قابل‌استفاده در زندگی روزمره "
                "و آزمون‌های بین‌المللی است.</p>"
                "<p>رویکرد تدریس او ترکیبی از تمرین مکالمه هدفمند، تقویت دایره واژگان، "
                "مرور گرامر در قالب مثال‌های واقعی و بازخورد مستمر روی تلفظ و روان صحبت کردن است. "
                "شرکت‌کنندگان دوره با برنامه هفتگی منظم و تمرین‌های تکلیفی، پیشرفت خود را "
                "در مهارت‌های Listening، Speaking، Reading و Writing دنبال می‌کنند.</p>"
                "<p>اگر هدف شما مهاجرت تحصیلی، اپلای دانشگاه یا ارتقای زبان عمومی است، "
                "این دوره می‌تواند پایه محکمی برای مسیر بعدی شما باشد.</p>"
            ),
            "specialties": (
                "مکالمه روزمره و آکادمیک\n"
                "گرامر کاربردی (سطح متوسط به پیشرفته)\n"
                "آمادگی آیلتس (IELTS)\n"
                "تلفظ و لهجه استاندارد\n"
                "Writing آکادمیک\n"
                "واژگان تخصصی مهاجرت تحصیلی"
            ),
            "highlights": (
                "بیش از ۸ سال تجربه تدریس زبان انگلیسی\n"
                "کلاس‌های تعاملی با تمرکز بر Speaking\n"
                "برنامه آموزشی شخصی‌سازی‌شده\n"
                "پشتیبانی بین جلسات\n"
                "مناسب دانشجویان و متقاضیان مهاجرت تحصیلی"
            ),
            "meta_title": "رسول منتظری | مدرس زبان انگلیسی و آیلتس",
            "meta_description": (
                "معرفی رسول منتظری، مدرس زبان انگلیسی و آیلتس در موسسه سفیران؛ "
                "رزومه، تخصص‌ها و دوره‌های ارائه‌شده."
            ),
            "search_keywords": "رسول منتظری, مدرس انگلیسی, آیلتس, IELTS, کلاس زبان انگلیسی, بابل",
            "order": 0,
            "is_active": True,
        },
    )

    CourseInstructorResumeEntry.objects.filter(instructor=instructor).delete()
    resume_rows = [
        (
            "۱۴۰۲ – اکنون",
            "مدرس زبان انگلیسی",
            "موسسه سفیران آینده روشن",
            "طراحی و اجرای دوره‌های عمومی انگلیسی، آمادگی آیلتس و کلاس‌های مکالمه برای دانشجویان و متقاضیان مهاجرت تحصیلی.",
            1,
        ),
        (
            "۱۳۹۶ – ۱۴۰۱",
            "مدرس زبان انگلیسی و آیلتس",
            "آموزشگاه‌های زبان خصوصی",
            "تدریس General English، IELTS Preparation و برگزاری آزمون‌های تعیین سطح.",
            2,
        ),
        (
            "۱۳۹۰ – ۱۳۹۶",
            "مدرس زبان انگلیسی",
            "مدارس و موسسات آموزشی",
            "تدریس پایه تا پیشرفته، تقویت مهارت شنیداری و گفتاری برای نوجوانان و بزرگسالان.",
            3,
        ),
    ]
    for period, role, org, desc, order in resume_rows:
        CourseInstructorResumeEntry.objects.create(
            instructor=instructor,
            period=period,
            role_title=role,
            organization=org,
            description=desc,
            order=order,
        )

    course, created = Course.objects.update_or_create(
        slug="english-language-course",
        defaults={
            "title": "دوره جامع زبان انگلیسی",
            "short_description": (
                "دوره زبان انگلیسی با تدریس رسول منتظری؛ مکالمه، گرامر، واژگان و آمادگی آیلتس "
                "با برنامه منظم و پشتیبانی بین جلسات."
            ),
            "description": (
                "<p>این دوره برای علاقه‌مندانی طراحی شده که می‌خواهند زبان انگلیسی را "
                "<strong>واقعاً</strong> یاد بگیرند — نه فقط حفظ قاعده. از مکالمه روزمره "
                "تا مهارت‌های موردنیاز اپلای و آیلتس، با تمرین مستمر و بازخورد مدرس پیش می‌روید.</p>"
                "<p>کلاس‌ها به‌صورت ترکیبی (حضوری و آنلاین) برگزار می‌شود و برای هر سطح "
                "(از متوسط به بالا) برنامه اختصاصی در نظر گرفته می‌شود.</p>"
            ),
            "objectives": (
                "<ul>"
                "<li>تقویت مکالمه روان و اعتمادبه‌نفس در موقعیت‌های واقعی</li>"
                "<li>مرور و تثبیت گرامر کاربردی در گفتار و نوشتار</li>"
                "<li>گسترش دایره واژگان عمومی و آکادمیک</li>"
                "<li>آشنایی با تکنیک‌های آیلتس و تمرین آزمون‌محور</li>"
                "<li>بهبود تلفظ و مهارت Listening</li>"
                "</ul>"
            ),
            "conditions": (
                "<p>آشنایی پایه با الفبا و ساختارهای ساده انگلیسی توصیه می‌شود. "
                "قبل از شروع، یک جلسه تعیین سطح (رایگان) برای انتخاب گروه مناسب برگزار می‌شود.</p>"
            ),
            "features": (
                "تدریس توسط رسول منتظری\n"
                "کلاس‌های کوچک و تعاملی\n"
                "تمرین و تکلیف هفتگی\n"
                "پشتیبانی بین جلسات\n"
                "گواهی پایان دوره از موسسه\n"
                "امکان برگزاری حضوری و آنلاین"
            ),
            "duration_hours": 48,
            "price": "تماس بگیرید",
            "delivery_mode": "both",
            "image": "",
            "country": "",
            "instructor": instructor,
            "meta_title": "دوره زبان انگلیسی | تدریس رسول منتظری",
            "meta_description": (
                "ثبت‌نام دوره جامع زبان انگلیسی با رسول منتظری؛ مکالمه، گرامر، آیلتس "
                "و مهارت‌های چهارگانه. حضوری و آنلاین در موسسه سفیران."
            ),
            "order": 0,
            "is_active": True,
        },
    )

    if created or not course.syllabus_items.exists():
        CourseSyllabus.objects.filter(course=course).delete()
        syllabus = [
            ("گرامر و ساختار جمله", "مرور زمان‌ها، حروف اضافه، جملات مرکب و تمرین در مکالمه.", 1),
            ("مکالمه و تلفظ", "موقعیت‌های روزمره، Role-play و اصلاح تلفظ.", 2),
            ("Listening و درک مطلب", "فایل‌های صوتی، نکته‌برداری و پاسخ به سوال.", 3),
            ("Reading و واژگان", "متون کوتاه، تکنیک اسکیم و اسکن، واژگان موضوعی.", 4),
            ("Writing آکادمیک", "پاراگراف، Task 1 و Task 2 آیلتس (مقدماتی).", 5),
            ("آمادگی آیلتس", "آشنایی با فرمت آزمون، تمرین زمان‌دار و بازخورد.", 6),
        ]
        for title, desc, order in syllabus:
            CourseSyllabus.objects.create(course=course, title=title, description=desc, order=order)

    if created or not course.faqs.filter(is_active=True).exists():
        CourseFAQ.objects.filter(course=course).delete()
        faqs = [
            (
                "این دوره برای چه سطحی مناسب است؟",
                "برای سطح متوسط به بالا طراحی شده؛ با تعیین سطح رایگان، گروه مناسب شما مشخص می‌شود.",
            ),
            (
                "کلاس‌ها حضوری است یا آنلاین؟",
                "هر دو حالت امکان‌پذیر است؛ هنگام ثبت‌نام می‌توانید ترجیح خود را اعلام کنید.",
            ),
            (
                "مدت دوره چقدر است؟",
                "برنامه ۴۸ ساعته (معمولاً ۱۲ تا ۱۶ هفته بسته به تعداد جلسات هفتگی) قابل تنظیم است.",
            ),
            (
                "آیا برای آیلتس هم آماده می‌شوم؟",
                "بله؛ بخشی از سرفصل اختصاص به آشنایی با فرمت آیلتس و تمرین‌های آزمون‌محور دارد.",
            ),
        ]
        for idx, (q, a) in enumerate(faqs, start=1):
            CourseFAQ.objects.create(
                course=course, question=q, answer=a, order=idx, is_active=True
            )


def unseed_english_course(apps, schema_editor):
    Course = apps.get_model("core", "Course")
    CourseInstructor = apps.get_model("core", "CourseInstructor")
    Course.objects.filter(slug="english-language-course").delete()
    CourseInstructor.objects.filter(slug="rasoul-montazeri").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0058_consultation_slot_booked_index"),
    ]

    operations = [
        migrations.CreateModel(
            name="CourseInstructor",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=150, verbose_name="نام و نام خانوادگی")),
                ("slug", models.SlugField(help_text="فقط حروف انگلیسی و خط تیره؛ مثلاً rasoul-montazeri", max_length=150, unique=True, verbose_name="شناسه آدرس")),
                ("position", models.CharField(help_text="مثلاً مدرس زبان انگلیسی", max_length=200, verbose_name="سمت")),
                ("title", models.CharField(blank=True, help_text="مثلاً کارشناسی ارشد آموزش زبان انگلیسی", max_length=200, verbose_name="عنوان / مدرک")),
                ("short_bio", models.TextField(blank=True, help_text="۱–۲ جمله برای کارت دوره و متا", verbose_name="معرفی کوتاه")),
                ("bio", models.TextField(blank=True, help_text="متن کامل معرفی و سوابق", verbose_name="بیوگرافی و رزومه")),
                ("specialties", models.TextField(blank=True, help_text="هر خط یک مورد؛ مثلاً IELTS، مکالمه، گرامر", verbose_name="تخصص‌ها")),
                ("highlights", models.TextField(blank=True, help_text="هر خط یک مورد؛ برای نمایش در کارت پروفایل", verbose_name="نکات برجسته")),
                ("image", models.ImageField(blank=True, null=True, upload_to=core.models.course_instructor_image_upload_to, verbose_name="عکس")),
                ("phone", models.CharField(blank=True, max_length=20, verbose_name="شماره تماس")),
                ("email", models.EmailField(blank=True, max_length=254, verbose_name="ایمیل")),
                ("telegram", models.URLField(blank=True, verbose_name="تلگرام")),
                ("whatsapp", models.CharField(blank=True, max_length=20, verbose_name="واتساپ")),
                ("instagram", models.URLField(blank=True, verbose_name="اینستاگرام")),
                ("linkedin", models.URLField(blank=True, verbose_name="لینکدین")),
                ("website", models.URLField(blank=True, verbose_name="وب‌سایت")),
                ("meta_title", models.CharField(blank=True, max_length=200, verbose_name="عنوان SEO")),
                ("meta_description", models.CharField(blank=True, max_length=160, verbose_name="توضیح متا (سئو)")),
                ("search_keywords", models.TextField(blank=True, verbose_name="کلمات کلیدی جستجو")),
                ("order", models.PositiveSmallIntegerField(default=0, verbose_name="ترتیب نمایش")),
                ("is_active", models.BooleanField(default=True, verbose_name="فعال")),
            ],
            options={
                "verbose_name": "مدرس دوره",
                "verbose_name_plural": "مدرسان دوره",
                "db_table": "core_courseinstructor",
                "ordering": ["order", "id"],
            },
        ),
        migrations.CreateModel(
            name="CourseInstructorResumeEntry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("period", models.CharField(help_text="مثلاً ۱۴۰۰ – اکنون", max_length=80, verbose_name="بازه زمانی")),
                ("role_title", models.CharField(max_length=200, verbose_name="عنوان شغلی / نقش")),
                ("organization", models.CharField(blank=True, max_length=200, verbose_name="موسسه / محل فعالیت")),
                ("description", models.TextField(blank=True, verbose_name="توضیحات")),
                ("order", models.PositiveSmallIntegerField(default=0, verbose_name="ترتیب")),
                (
                    "instructor",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="resume_entries",
                        to="core.courseinstructor",
                        verbose_name="مدرس",
                    ),
                ),
            ],
            options={
                "verbose_name": "سابقه مدرس",
                "verbose_name_plural": "سوابق مدرس",
                "db_table": "core_courseinstructor_resume",
                "ordering": ["order", "id"],
            },
        ),
        migrations.AddField(
            model_name="course",
            name="instructor",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="courses",
                to="core.courseinstructor",
                verbose_name="مدرس دوره",
            ),
        ),
        migrations.AddField(
            model_name="course",
            name="meta_title",
            field=models.CharField(blank=True, max_length=200, verbose_name="عنوان SEO"),
        ),
        migrations.AddField(
            model_name="course",
            name="meta_description",
            field=models.CharField(blank=True, max_length=160, verbose_name="توضیح متا (سئو)"),
        ),
        migrations.RunPython(seed_english_course, unseed_english_course),
    ]
