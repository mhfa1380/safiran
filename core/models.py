from django.db import models


class Institute(models.Model):
    """اطلاعات موسسه اعزام دانشجو؛ تنها یک رکورد. از پنل ادمین قابل ویرایش است."""

    name = models.CharField("نام موسسه", max_length=150)
    province = models.CharField("استان", max_length=100)
    city = models.CharField("شهر", max_length=100)
    type_title = models.CharField("عنوان نوع مجوز", max_length=200)
    phone = models.CharField("تلفن", max_length=20)
    email = models.EmailField("ایمیل")
    address = models.TextField("آدرس")
    website = models.CharField("وب‌سایت", max_length=200, blank=True)
    license_issue_date = models.CharField("تاریخ صدور مجوز", max_length=20)
    license_expiry_date = models.CharField("تاریخ انقضای مجوز", max_length=20, blank=True)
    students_sent = models.PositiveIntegerField("تعداد دانشجویان اعزام‌شده", default=0)
    countries_count = models.PositiveIntegerField("کشور مقصد", default=0)

    class Meta:
        app_label = "core"
        db_table = "core_institute"
        verbose_name = "اطلاعات موسسه"
        verbose_name_plural = "اطلاعات موسسه"

    def __str__(self):
        return self.name

    @property
    def phone_formatted(self):
        """شماره تلفن با فرمت نمایشی (مثلاً 011-32350320)."""
        if not self.phone:
            return ""
        if len(self.phone) == 11 and self.phone.startswith("0"):
            return f"{self.phone[:3]}-{self.phone[3:]}"
        return self.phone

    @property
    def website_url(self):
        """آدرس وب‌سایت با پروتکل برای استفاده در لینک."""
        if not self.website:
            return ""
        url = self.website.strip()
        if url and not url.startswith(("http://", "https://")):
            return f"https://{url}"
        return url


class ConsultationRequest(models.Model):
    """ثبت درخواست رزرو وقت مشاوره برای موسسه سفیران آینده روشن."""

    IN_PERSON = "in_person"
    ONLINE = "online"
    CONSULTATION_TYPE_CHOICES = [
        (IN_PERSON, "حضوری (۳۰ دقیقه)"),
        (ONLINE, "غیرحضوری / آنلاین (۳۰ دقیقه)"),
    ]

    COUNTRY_CHINA = "china"
    COUNTRY_CANADA = "canada"
    COUNTRY_SPAIN = "spain"
    COUNTRY_OTHER = "other"
    COUNTRY_CHOICES = [
        (COUNTRY_CHINA, "چین"),
        (COUNTRY_CANADA, "کانادا"),
        (COUNTRY_SPAIN, "اسپانیا"),
        (COUNTRY_OTHER, "سایر کشورها"),
    ]

    STATUS_NEW = "new"
    STATUS_CONTACTED = "contacted"
    STATUS_DONE = "done"
    STATUS_CHOICES = [
        (STATUS_NEW, "ثبت شده"),
        (STATUS_CONTACTED, "تماس گرفته شده"),
        (STATUS_DONE, "انجام شده"),
    ]

    full_name = models.CharField("نام و نام خانوادگی", max_length=150)
    phone = models.CharField("شماره تماس", max_length=20)
    email = models.EmailField("ایمیل", blank=True)
    consultation_type = models.CharField(
        "نوع مشاوره",
        max_length=20,
        choices=CONSULTATION_TYPE_CHOICES,
        default=ONLINE,
    )
    country = models.CharField(
        "کشور مقصد", max_length=20, choices=COUNTRY_CHOICES, default=COUNTRY_CANADA
    )
    slot = models.ForeignKey(
        "core.ConsultationSlot",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="consultation_requests",
        verbose_name="زمان رزرو",
    )
    interest_university = models.ForeignKey(
        "core.University",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="consultation_requests",
        verbose_name="دانشگاه مورد علاقه",
    )
    description = models.TextField(
        "توضیحات و سوالات شما",
        blank=True,
        help_text="به صورت خلاصه شرایط و سوالات خود را بنویسید.",
    )

    status = models.CharField(
        "وضعیت درخواست",
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_NEW,
    )
    admin_seen_at = models.DateTimeField(
        "مشاهده توسط ادمین",
        null=True,
        blank=True,
        help_text="زمانی که ادمین لیست را مشاهده کرده (برای badge پیام جدید)",
    )
    created_at = models.DateTimeField("تاریخ ثبت", auto_now_add=True)
    updated_at = models.DateTimeField("آخرین به‌روزرسانی", auto_now=True)

    class Meta:
        app_label = "core"
        db_table = "core_consultationrequest"
        verbose_name = "درخواست مشاوره"
        verbose_name_plural = "درخواست‌های مشاوره"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["consultation_type"], name="consult_type_idx"),
            models.Index(fields=["country"], name="consult_country_idx"),
            models.Index(fields=["status"], name="consult_status_idx"),
            models.Index(fields=["created_at"], name="consult_created_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.full_name} - {self.get_consultation_type_display()}"


class ConsultationSlot(models.Model):
    """زمان‌های از پیش تعیین‌شده برای رزرو مشاوره."""

    date = models.DateField("تاریخ")
    time_label = models.CharField("بازه زمانی", max_length=50)  # مثلاً "۱۰:۰۰ - ۱۰:۳۰"
    is_booked = models.BooleanField("رزرو شده", default=False)
    admin_seen_at = models.DateTimeField(
        "مشاهده توسط ادمین",
        null=True,
        blank=True,
        help_text="برای badge تایم‌های رزرو شده جدید",
    )
    order = models.PositiveSmallIntegerField("ترتیب", default=0)

    class Meta:
        app_label = "core"
        db_table = "core_consultationslot"
        verbose_name = "زمان مشاوره"
        verbose_name_plural = "زمان‌های مشاوره"
        ordering = ["date", "order", "id"]
        unique_together = [["date", "time_label"]]
        indexes = [
            models.Index(fields=["date", "is_booked"], name="slot_date_booked_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.date} — {self.time_label}"


class EvaluationRequest(models.Model):
    """فرم ارزیابی اولیه برای بررسی شرایط متقاضی."""

    DEGREE_DIPLOMA = "diploma"
    DEGREE_BACHELOR = "bachelor"
    DEGREE_MASTER = "master"
    DEGREE_PHD = "phd"
    DEGREE_CHOICES = [
        (DEGREE_DIPLOMA, "دیپلم"),
        (DEGREE_BACHELOR, "کارشناسی"),
        (DEGREE_MASTER, "کارشناسی ارشد"),
        (DEGREE_PHD, "دکتری"),
    ]

    TARGET_CHOICES = ConsultationRequest.COUNTRY_CHOICES

    # اطلاعات شخصی
    full_name = models.CharField("نام و نام خانوادگی", max_length=150)
    phone = models.CharField("شماره تماس", max_length=20)
    email = models.EmailField("ایمیل", blank=True)
    birth_year = models.PositiveSmallIntegerField("سال تولد", blank=True, null=True)

    MARITAL_SINGLE = "single"
    MARITAL_MARRIED = "married"
    MARITAL_CHOICES = [
        (MARITAL_SINGLE, "مجرد"),
        (MARITAL_MARRIED, "متاهل"),
    ]
    marital_status = models.CharField(
        "وضعیت تاهل", max_length=10, choices=MARITAL_CHOICES, blank=True
    )

    APPLY_SOON = "<1"
    APPLY_MID = "1-2"
    APPLY_LATE = ">2"
    APPLY_CHOICES = [
        (APPLY_SOON, "کمتر از ۱ سال"),
        (APPLY_MID, "بین ۱ تا ۲ سال"),
        (APPLY_LATE, "بیشتر از ۲ سال"),
    ]
    apply_timeline = models.CharField(
        "کی قصد اپلای دارید؟", max_length=10, choices=APPLY_CHOICES, blank=True
    )

    has_financial_capacity = models.BooleanField(
        "تمکن مالی بالای یک میلیارد تومان دارم", default=False
    )

    # سوابق تحصیلی
    current_degree = models.CharField(
        "آخرین مدرک تحصیلی", max_length=20, choices=DEGREE_CHOICES
    )
    field_of_study = models.CharField("رشته تحصیلی فعلی / قبلی", max_length=150)
    average_grade = models.CharField(
        "معدل (تقریبی)", max_length=20, help_text="مثلاً ۱۸.۵"
    )
    graduation_year = models.CharField(
        "سال فارغ التحصیلی", max_length=10, blank=True
    )

    # کشور مقصد اصلی (برای دسته‌بندی سریع)
    target_country = models.CharField(
        "کشور مقصد", max_length=20, choices=TARGET_CHOICES, default=ConsultationRequest.COUNTRY_CANADA
    )

    # آزمون زبان
    TEST_NONE = "none"
    TEST_IELTS = "ielts"
    TEST_TOEFL = "toefl"
    TEST_DUOLINGO = "duolingo"
    TEST_PTE = "pte"
    TEST_DELF = "delf"
    TEST_TESTDAF = "testdaf"
    TEST_SAT = "sat"
    TEST_YOS = "yos"
    LANGUAGE_TEST_CHOICES = [
        (TEST_NONE, "ندارم"),
        (TEST_IELTS, "IELTS"),
        (TEST_TOEFL, "TOEFL"),
        (TEST_DUOLINGO, "Duolingo"),
        (TEST_PTE, "PTE"),
        (TEST_DELF, "DELF/DALF"),
        (TEST_TESTDAF, "TestDaF"),
        (TEST_SAT, "SAT"),
        (TEST_YOS, "YOS"),
    ]
    language_test_type = models.CharField(
        "نوع آزمون زبان",
        max_length=20,
        choices=LANGUAGE_TEST_CHOICES,
        default=TEST_NONE,
    )
    has_ielts = models.BooleanField(
        "مدرک زبان (آیلتس/تافل) دارم", default=False, help_text="در صورت داشتن هر نوع مدرک زبان این گزینه را فعال کنید."
    )
    language_score = models.CharField(
        "نمره زبان (در صورت وجود)", max_length=50, blank=True
    )

    # دستاوردها
    has_journal_article = models.BooleanField("مقاله ژورنالی", default=False)
    has_conference_article = models.BooleanField("مقاله کنفرانسی", default=False)
    has_book = models.BooleanField("چاپ یا ترجمه کتاب", default=False)
    has_international_tests = models.BooleanField(
        "آزمون‌های بین‌الملل (SAT, GRE, GMAT ...)", default=False
    )

    # اولویت‌ها
    desired_countries = models.CharField(
        "کشورهای مورد نظر",
        max_length=200,
        blank=True,
        help_text="مثلاً چین، کانادا، اسپانیا یا سایر کشورها",
    )
    desired_major = models.CharField(
        "رشته مورد نظر (اختیاری)", max_length=150, blank=True
    )

    SERVICE_FULL = "full"
    SERVICE_PARTIAL = "partial"
    SERVICE_CONSULT = "consulting"
    SERVICE_CHOICES = [
        (SERVICE_FULL, "تمام فرآیند پذیرش و ویزا"),
        (SERVICE_PARTIAL, "بخشی از فرآیند پذیرش و ویزا"),
        (SERVICE_CONSULT, "تنها مشاوره دقیق و فنی می‌خواهم"),
    ]
    service_scope = models.CharField(
        "تمایل دارید چه بخشی از کار به موسسه سپرده شود؟",
        max_length=30,
        choices=SERVICE_CHOICES,
        blank=True,
    )

    # سایر
    preferred_intake = models.CharField(
        "ترم / سال مورد نظر برای شروع",
        max_length=50,
        blank=True,
    )
    notes = models.TextField(
        "توضیحات تکمیلی",
        blank=True,
        help_text="اولویت‌ها، بودجه تقریبی، کشور یا دانشگاه‌های مورد علاقه و ...",
    )

    admin_seen_at = models.DateTimeField(
        "مشاهده توسط ادمین",
        null=True,
        blank=True,
        help_text="برای badge درخواست‌های جدید",
    )
    created_at = models.DateTimeField("تاریخ ثبت", auto_now_add=True)

    class Meta:
        app_label = "core"
        db_table = "core_evaluationrequest"
        verbose_name = "درخواست ارزیابی"
        verbose_name_plural = "درخواست‌های ارزیابی"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.full_name} - {self.get_target_country_display()}"


class ContactMessage(models.Model):
    """پیام‌های دریافتی از فرم تماس با ما."""

    STATUS_UNREAD = "unread"
    STATUS_READ = "read"
    STATUS_REPLIED = "replied"
    STATUS_CHOICES = [
        (STATUS_UNREAD, "خوانده نشده"),
        (STATUS_READ, "خوانده شده"),
        (STATUS_REPLIED, "پاسخ داده شده"),
    ]

    full_name = models.CharField("نام و نام خانوادگی", max_length=150)
    email = models.EmailField("ایمیل")
    subject = models.CharField("موضوع", max_length=200)
    message = models.TextField("متن پیام")

    status = models.CharField(
        "وضعیت",
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_UNREAD,
    )
    admin_seen_at = models.DateTimeField(
        "مشاهده توسط ادمین",
        null=True,
        blank=True,
        help_text="برای badge پیام‌های جدید",
    )
    created_at = models.DateTimeField("تاریخ ثبت", auto_now_add=True)

    class Meta:
        app_label = "core"
        db_table = "core_contactmessage"
        verbose_name = "پیام تماس"
        verbose_name_plural = "پیام‌های تماس"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.full_name} - {self.subject}"


class BlogPost(models.Model):
    """پست وبلاگ برای اخبار و مطالب موسسه."""

    title = models.CharField("عنوان", max_length=250)
    slug = models.SlugField(
        "شناسه آدرس",
        max_length=250,
        unique=True,
        help_text="برای آدرس صفحه، فقط حروف انگلیسی و خط تیره.",
    )
    excerpt = models.TextField("خلاصه مطلب", blank=True)
    content = models.TextField("متن کامل")

    image = models.URLField(
        "آدرس تصویر شاخص",
        blank=True,
        help_text="آدرس تصویر؛ در صورت خالی بودن از تصویر پیش‌فرض استفاده می‌شود.",
    )

    country_tag = models.CharField(
        "برچسب کشور / دسته",
        max_length=100,
        blank=True,
        help_text="مثلاً چین، کانادا، اسپانیا، خبری، خدمات موسسه",
    )

    is_published = models.BooleanField("منتشر شده", default=True)
    created_at = models.DateTimeField("تاریخ انتشار", auto_now_add=True)
    updated_at = models.DateTimeField("آخرین به‌روزرسانی", auto_now=True)

    class Meta:
        app_label = "core"
        db_table = "core_blogpost"
        verbose_name = "پست وبلاگ"
        verbose_name_plural = "پست‌های وبلاگ"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["is_published", "created_at"],
                name="blog_published_created_idx",
            ),
            models.Index(fields=["country_tag"], name="blog_country_tag_idx"),
        ]

    def __str__(self) -> str:
        return self.title


class Service(models.Model):
    """خدمات موسسه برای نمایش در صفحه خدمات."""

    title = models.CharField("عنوان", max_length=150)
    short_description = models.TextField(
        "توضیح کوتاه (صفحه اول)",
        blank=True,
        help_text="خلاصه برای نمایش در صفحه اصلی؛ در صورت خالی بودن از توضیحات کامل استفاده می‌شود.",
    )
    description = models.TextField(
        "توضیحات کامل (صفحه خدمات)",
        help_text="متن کامل برای صفحه خدمات موسسه.",
    )
    icon = models.CharField(
        "کلاس آیکون",
        max_length=80,
        blank=True,
        help_text="مثلاً ti-comments-smiley یا ti-email",
    )
    order = models.PositiveSmallIntegerField("ترتیب نمایش", default=0)
    is_active = models.BooleanField("فعال", default=True)

    class Meta:
        app_label = "core"
        db_table = "core_service"
        verbose_name = "خدمت"
        verbose_name_plural = "خدمات موسسه"
        ordering = ["order", "id"]

    def __str__(self) -> str:
        return self.title


class Major(models.Model):
    """رشته‌های تحصیلی برای نمایش در صفحه رشته‌ها و جزئیات رشته."""

    COUNTRY_CHOICES = ConsultationRequest.COUNTRY_CHOICES

    title = models.CharField("عنوان رشته", max_length=200)
    slug = models.SlugField(
        "شناسه آدرس",
        max_length=250,
        unique=True,
        blank=True,
        help_text="برای آدرس صفحه؛ خالی = از عنوان ساخته می‌شود.",
    )
    short_description = models.TextField("خلاصه (لیست)", blank=True)
    description = models.TextField("توضیحات کامل", blank=True)
    image = models.URLField("آدرس تصویر", blank=True)
    country = models.CharField(
        "کشور مرتبط",
        max_length=20,
        choices=COUNTRY_CHOICES,
        blank=True,
    )
    order = models.PositiveSmallIntegerField("ترتیب نمایش", default=0)
    is_active = models.BooleanField("فعال", default=True)

    class Meta:
        app_label = "core"
        db_table = "core_major"
        verbose_name = "رشته تحصیلی"
        verbose_name_plural = "رشته‌های تحصیلی"
        ordering = ["order", "id"]

    def __str__(self) -> str:
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug and self.title:
            from django.utils.text import slugify
            import uuid
            base = slugify(self.title, allow_unicode=False)
            self.slug = base if base else f"major-{uuid.uuid4().hex[:8]}"
        super().save(*args, **kwargs)


class Course(models.Model):
    """دوره‌ها و برنامه‌های تحصیلی برای نمایش در صفحه جزئیات دوره."""

    COUNTRY_CHOICES = ConsultationRequest.COUNTRY_CHOICES

    DELIVERY_IN_PERSON = "in_person"
    DELIVERY_ONLINE = "online"
    DELIVERY_BOTH = "both"
    DELIVERY_CHOICES = [
        (DELIVERY_IN_PERSON, "حضوری"),
        (DELIVERY_ONLINE, "آنلاین"),
        (DELIVERY_BOTH, "حضوری و آنلاین"),
    ]

    title = models.CharField("عنوان دوره", max_length=250)
    slug = models.SlugField(
        "شناسه آدرس",
        max_length=250,
        unique=True,
        help_text="برای آدرس صفحه، فقط حروف انگلیسی و خط تیره.",
    )
    short_description = models.TextField("خلاصه", blank=True)
    description = models.TextField("توضیحات کامل دوره", blank=True)
    objectives = models.TextField("اهداف دوره", blank=True)
    conditions = models.TextField("شرایط و پیش‌نیازها", blank=True)
    features = models.TextField(
        "ویژگی‌های دوره",
        blank=True,
        help_text="هر خط یک ویژگی؛ مثلاً: پشتیبانی آنلاین، گواهینامه معتبر",
    )
    duration_hours = models.PositiveIntegerField("مدت دوره (ساعت)", default=0, blank=True)
    price = models.CharField("قیمت", max_length=150, blank=True, help_text="مثلاً: تماس بگیرید، رایگان، یا مبلغ")
    delivery_mode = models.CharField(
        "نحوه برگزاری",
        max_length=20,
        choices=DELIVERY_CHOICES,
        default=DELIVERY_BOTH,
        blank=True,
    )
    sample_video = models.URLField("لینک ویدیو نمونه تدریس", blank=True)
    image = models.URLField("آدرس تصویر", blank=True)
    country = models.CharField(
        "کشور مرتبط",
        max_length=20,
        choices=COUNTRY_CHOICES,
        blank=True,
    )
    order = models.PositiveSmallIntegerField("ترتیب نمایش", default=0)
    is_active = models.BooleanField("فعال", default=True)

    class Meta:
        app_label = "core"
        db_table = "core_course"
        verbose_name = "دوره"
        verbose_name_plural = "دوره‌ها"
        ordering = ["order", "id"]

    def __str__(self) -> str:
        return self.title

    def get_features_list(self):
        """لیست ویژگی‌ها (هر خط یک مورد)."""
        if not self.features:
            return []
        return [line.strip() for line in self.features.strip().splitlines() if line.strip()]

    def get_sample_video_embed_url(self):
        """آدرس embed ویدیو برای نمایش در iframe (یوتیوب و آپارات)."""
        if not self.sample_video:
            return ""
        url = self.sample_video.strip()
        if "youtube.com/watch?v=" in url:
            vid = url.split("v=")[-1].split("&")[0]
            return f"https://www.youtube.com/embed/{vid}"
        if "youtu.be/" in url:
            vid = url.split("youtu.be/")[-1].split("?")[0]
            return f"https://www.youtube.com/embed/{vid}"
        if "aparat.com/v/" in url:
            vid = url.rstrip("/").split("/")[-1]
            return f"https://www.aparat.com/video/video/embed/videohash/{vid}/fa/video_id/{vid}"
        return url


class CourseFAQ(models.Model):
    """سوالات متداول اختصاصی هر دوره برای نمایش در صفحه جزئیات دوره."""

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="faqs",
        verbose_name="دوره",
    )
    question = models.CharField("سوال", max_length=350)
    answer = models.TextField("پاسخ")
    order = models.PositiveSmallIntegerField("ترتیب نمایش", default=0)
    is_active = models.BooleanField("فعال", default=True)

    class Meta:
        app_label = "core"
        db_table = "core_course_faq"
        verbose_name = "سوال متداول دوره"
        verbose_name_plural = "سوالات متداول دوره"
        ordering = ["order", "id"]

    def __str__(self) -> str:
        return self.question[:60] + ("..." if len(self.question) > 60 else "")


class MajorFAQ(models.Model):
    """سوالات متداول اختصاصی هر رشته برای نمایش در صفحه جزئیات رشته."""

    major = models.ForeignKey(
        Major,
        on_delete=models.CASCADE,
        related_name="faqs",
        verbose_name="رشته",
    )
    question = models.CharField("سوال", max_length=350)
    answer = models.TextField("پاسخ")
    order = models.PositiveSmallIntegerField("ترتیب نمایش", default=0)
    is_active = models.BooleanField("فعال", default=True)

    class Meta:
        app_label = "core"
        db_table = "core_major_faq"
        verbose_name = "سوال متداول رشته"
        verbose_name_plural = "سوالات متداول رشته"
        ordering = ["order", "id"]

    def __str__(self) -> str:
        return self.question[:60] + ("..." if len(self.question) > 60 else "")


class CourseSyllabus(models.Model):
    """سرفصل‌های دوره با عنوان و توضیحات."""

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="syllabus_items",
        verbose_name="دوره",
    )
    title = models.CharField("عنوان سرفصل", max_length=250)
    description = models.TextField("توضیحات", blank=True)
    order = models.PositiveSmallIntegerField("ترتیب", default=0)

    class Meta:
        app_label = "core"
        db_table = "core_course_syllabus"
        verbose_name = "سرفصل دوره"
        verbose_name_plural = "سرفصل‌های دوره"
        ordering = ["order", "id"]

    def __str__(self) -> str:
        return self.title


class FAQ(models.Model):
    """سوالات متداول برای نمایش در صفحه FAQ."""

    question = models.CharField("سوال", max_length=350)
    answer = models.TextField("پاسخ")
    order = models.PositiveSmallIntegerField("ترتیب نمایش", default=0)
    is_active = models.BooleanField("فعال", default=True)

    class Meta:
        app_label = "core"
        db_table = "core_faq"
        verbose_name = "سوال متداول"
        verbose_name_plural = "سوالات متداول"
        ordering = ["order", "id"]

    def __str__(self) -> str:
        return self.question[:60] + ("..." if len(self.question) > 60 else "")


class University(models.Model):
    """دانشگاه‌ها و موسسات مناسب پذیرش تحصیلی (مجاز برای سفیران)."""

    COUNTRY_CHOICES = ConsultationRequest.COUNTRY_CHOICES

    TYPE_UNIVERSITY = "university"
    TYPE_COLLEGE = "college"
    TYPE_SCHOOL = "school"
    TYPE_INSTITUTE = "institute"
    TYPE_CHOICES = [
        (TYPE_UNIVERSITY, "دانشگاه"),
        (TYPE_COLLEGE, "کالج"),
        (TYPE_SCHOOL, "مدرسه"),
        (TYPE_INSTITUTE, "موسسه"),
    ]

    slug = models.SlugField(
        "شناسه آدرس (انگلیسی)", max_length=150, unique=True, help_text="برای آدرس صفحه، فقط حروف انگلیسی و خط تیره."
    )
    name_fa = models.CharField("نام فارسی", max_length=200)
    name_en = models.CharField("نام انگلیسی", max_length=200)

    image = models.FileField(
        "تصویر دانشگاه",
        upload_to="universities/",
        blank=True,
        null=True,
        help_text="تصویر را اینجا آپلود کنید.",
    )

    country = models.CharField("کشور", max_length=20, choices=COUNTRY_CHOICES)
    city = models.CharField("شهر", max_length=100)
    type = models.CharField("نوع موسسه", max_length=20, choices=TYPE_CHOICES, default=TYPE_UNIVERSITY)

    world_rank = models.CharField(
        "رتبه جهانی", max_length=50, blank=True, help_text="مثلاً 2 یا 101-150"
    )

    is_approved_by_mo_science = models.BooleanField(
        "مورد تایید وزارت علوم", default=True
    )
    is_approved_by_mo_health = models.BooleanField(
        "مورد تایید وزارت بهداشت", default=False
    )

    website = models.URLField("وب‌سایت دانشگاه", blank=True)
    short_description = models.TextField("توضیح کوتاه", blank=True)
    description = models.TextField("توضیحات کامل", blank=True)

    meta_title = models.CharField(
        "عنوان SEO",
        max_length=200,
        blank=True,
        help_text="برای موتورهای جستجو؛ در صورت خالی بودن از نام دانشگاه استفاده می‌شود.",
    )
    meta_description = models.TextField(
        "توضیح SEO",
        blank=True,
        help_text="خلاصه صفحه برای موتورهای جستجو (۱۵۰–۱۶۰ کاراکتر توصیه می‌شود).",
    )

    created_at = models.DateTimeField("تاریخ ایجاد", auto_now_add=True)

    class Meta:
        app_label = "core"
        db_table = "core_university"
        verbose_name = "دانشگاه / موسسه"
        verbose_name_plural = "دانشگاه‌ها و موسسات"
        ordering = ["country", "city", "name_fa"]
        indexes = [
            models.Index(fields=["country", "city"], name="uni_country_city_idx"),
            models.Index(fields=["type"], name="uni_type_idx"),
            models.Index(fields=["name_fa"], name="uni_name_fa_idx"),
            models.Index(fields=["name_en"], name="uni_name_en_idx"),
        ]

    def __str__(self) -> str:
        return self.name_fa


class TeamMember(models.Model):
    """اعضای تیم موسسه برای نمایش در صفحه درباره ما."""

    name = models.CharField("نام و نام خانوادگی", max_length=150)
    position = models.CharField("سمت", max_length=150)
    image = models.FileField(
        "عکس",
        upload_to="team/",
        help_text="عکس عضو تیم (الزامی)",
    )
    title = models.CharField(
        "عنوان / مدرک",
        max_length=200,
        blank=True,
        help_text="مثلاً مشاور ارشد، کارشناس پذیرش",
    )
    phone = models.CharField("شماره تماس", max_length=20, blank=True)
    email = models.EmailField("ایمیل", blank=True)
    description = models.TextField(
        "توضیحات",
        blank=True,
        help_text="معرفی کوتاه یا طولانی عضو تیم",
    )
    telegram = models.URLField("تلگرام", blank=True)
    whatsapp = models.CharField("واتساپ", max_length=20, blank=True, help_text="شماره با کد کشور، مثلاً 989123456789")
    instagram = models.URLField("اینستاگرام", blank=True)
    linkedin = models.URLField("لینکدین", blank=True)
    website = models.URLField("وب‌سایت شخصی", blank=True)

    order = models.PositiveSmallIntegerField("ترتیب نمایش", default=0)
    is_active = models.BooleanField("فعال", default=True)

    class Meta:
        app_label = "core"
        db_table = "core_teammember"
        verbose_name = "عضو تیم"
        verbose_name_plural = "اعضای تیم"
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.name} — {self.position}"


class UniversityGalleryImage(models.Model):
    """تصاویر گالری دانشگاه."""

    university = models.ForeignKey(
        "core.University",
        on_delete=models.CASCADE,
        related_name="gallery_images",
        verbose_name="دانشگاه",
    )
    image = models.FileField("تصویر", upload_to="universities/gallery/")
    caption = models.CharField("عنوان / توضیح تصویر", max_length=200, blank=True)
    order = models.PositiveSmallIntegerField("ترتیب نمایش", default=0)

    class Meta:
        app_label = "core"
        db_table = "core_universitygalleryimage"
        verbose_name = "تصویر گالری"
        verbose_name_plural = "تصاویر گالری"
        ordering = ["order", "id"]

    def __str__(self) -> str:
        return self.caption or f"تصویر {self.order}"


class UniversityFAQ(models.Model):
    """سوالات متداول اختصاصی هر دانشگاه برای نمایش در صفحه جزئیات دانشگاه."""

    university = models.ForeignKey(
        University,
        on_delete=models.CASCADE,
        related_name="faqs",
        verbose_name="دانشگاه",
    )
    question = models.CharField("سوال", max_length=350)
    answer = models.TextField("پاسخ")
    order = models.PositiveSmallIntegerField("ترتیب نمایش", default=0)
    is_active = models.BooleanField("فعال", default=True)

    class Meta:
        app_label = "core"
        db_table = "core_university_faq"
        verbose_name = "سوال متداول دانشگاه"
        verbose_name_plural = "سوالات متداول دانشگاه"
        ordering = ["order", "id"]

    def __str__(self) -> str:
        return self.question[:60] + ("..." if len(self.question) > 60 else "")

