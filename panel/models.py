"""
مدل‌های پرونده مشتری برای پنل کال‌سنتر / پیگیری.
"""
from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone


class Customer(models.Model):
    """شخص یکتا بر اساس موبایل نرمال‌شده."""

    full_name = models.CharField("نام و نام خانوادگی", max_length=150)
    phone_normalized = models.CharField(
        "موبایل نرمال", max_length=20, unique=True, db_index=True
    )
    phone_display = models.CharField("موبایل نمایشی", max_length=30, blank=True)
    email = models.EmailField("ایمیل", blank=True)
    created_at = models.DateTimeField("ایجاد", auto_now_add=True)
    updated_at = models.DateTimeField("به‌روزرسانی", auto_now=True)

    class Meta:
        verbose_name = "مشتری"
        verbose_name_plural = "مشتریان"
        ordering = ["-updated_at"]

    def __str__(self) -> str:
        return f"{self.full_name} ({self.phone_display or self.phone_normalized})"


class CustomerCase(models.Model):
    """پرونده پیگیری از جذب تا اعزام."""

    STAGE_ATTRACTION = "attraction"
    STAGE_INITIAL = "initial_consult"
    STAGE_FOLLOW_UP = "follow_up"
    STAGE_SPECIALIZED = "specialized_consult"
    STAGE_FILE_OPEN = "file_open"
    STAGE_ADMISSION = "admission"
    STAGE_VISA = "visa"
    STAGE_DISPATCH = "dispatch"
    STAGE_WON = "won"
    STAGE_LOST = "lost"
    STAGE_CHOICES = [
        (STAGE_ATTRACTION, "جذب"),
        (STAGE_INITIAL, "مشاوره اولیه"),
        (STAGE_FOLLOW_UP, "پیگیری"),
        (STAGE_SPECIALIZED, "مشاوره تخصصی"),
        (STAGE_FILE_OPEN, "تشکیل پرونده"),
        (STAGE_ADMISSION, "پذیرش"),
        (STAGE_VISA, "ویزا"),
        (STAGE_DISPATCH, "اعزام"),
        (STAGE_WON, "موفق"),
        (STAGE_LOST, "مختومه"),
    ]

    STAGE_PROGRESS = {
        STAGE_ATTRACTION: 10,
        STAGE_INITIAL: 25,
        STAGE_FOLLOW_UP: 40,
        STAGE_SPECIALIZED: 55,
        STAGE_FILE_OPEN: 70,
        STAGE_ADMISSION: 80,
        STAGE_VISA: 90,
        STAGE_DISPATCH: 95,
        STAGE_WON: 100,
        STAGE_LOST: 0,
    }

    STATUS_OPEN = "open"
    STATUS_WAITING = "waiting"
    STATUS_CLOSED_WON = "closed_won"
    STATUS_CLOSED_LOST = "closed_lost"
    STATUS_CHOICES = [
        (STATUS_OPEN, "باز"),
        (STATUS_WAITING, "منتظر مشتری"),
        (STATUS_CLOSED_WON, "موفق / بسته"),
        (STATUS_CLOSED_LOST, "مختومه"),
    ]

    PRIORITY_LOW = "low"
    PRIORITY_NORMAL = "normal"
    PRIORITY_HIGH = "high"
    PRIORITY_URGENT = "urgent"
    PRIORITY_CHOICES = [
        (PRIORITY_LOW, "کم"),
        (PRIORITY_NORMAL, "معمولی"),
        (PRIORITY_HIGH, "بالا"),
        (PRIORITY_URGENT, "فوری"),
    ]

    SOURCE_EVALUATION = "evaluation"
    SOURCE_CONSULTATION = "consultation"
    SOURCE_CONTACT = "contact"
    SOURCE_MANUAL = "manual"
    SOURCE_CHOICES = [
        (SOURCE_EVALUATION, "ارزیابی"),
        (SOURCE_CONSULTATION, "رزرو مشاوره"),
        (SOURCE_CONTACT, "تماس با ما"),
        (SOURCE_MANUAL, "ورود دستی"),
    ]

    LOSS_NOT_INTERESTED = "not_interested"
    LOSS_BUDGET = "budget"
    LOSS_OTHER_AGENCY = "other_agency"
    LOSS_NO_ANSWER = "no_answer"
    LOSS_VISA_REJECT = "visa_reject"
    LOSS_CANCELLED = "cancelled"
    LOSS_OTHER = "other"
    LOSS_REASON_CHOICES = [
        (LOSS_NOT_INTERESTED, "عدم علاقه‌مندی"),
        (LOSS_BUDGET, "بودجه"),
        (LOSS_OTHER_AGENCY, "مؤسسه دیگر"),
        (LOSS_NO_ANSWER, "عدم پاسخ طولانی"),
        (LOSS_VISA_REJECT, "رد ویزا"),
        (LOSS_CANCELLED, "انصراف"),
        (LOSS_OTHER, "سایر"),
    ]

    case_code = models.CharField("کد پرونده", max_length=20, unique=True, db_index=True)
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="cases",
        verbose_name="مشتری",
    )
    stage = models.CharField(
        "مرحله", max_length=32, choices=STAGE_CHOICES, default=STAGE_ATTRACTION, db_index=True
    )
    status = models.CharField(
        "وضعیت", max_length=20, choices=STATUS_CHOICES, default=STATUS_OPEN, db_index=True
    )
    progress = models.PositiveSmallIntegerField("پیشرفت ٪", default=10)
    priority = models.CharField(
        "اولویت", max_length=10, choices=PRIORITY_CHOICES, default=PRIORITY_NORMAL, db_index=True
    )
    source_type = models.CharField(
        "منبع", max_length=20, choices=SOURCE_CHOICES, default=SOURCE_MANUAL, db_index=True
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="panel_assigned_cases",
        verbose_name="مسئول",
    )
    next_follow_up_at = models.DateTimeField(
        "پیگیری بعدی", null=True, blank=True, db_index=True
    )
    last_contact_result = models.CharField("آخرین نتیجه تماس", max_length=32, blank=True)
    loss_reason = models.CharField(
        "دلیل مختومه", max_length=32, blank=True, choices=LOSS_REASON_CHOICES
    )
    loss_note = models.CharField("توضیح مختومه", max_length=300, blank=True)
    internal_notes = models.TextField("یادداشت داخلی", blank=True)
    target_country = models.CharField("کشور مقصد", max_length=50, blank=True)
    target_degree = models.CharField("مقطع", max_length=50, blank=True)
    checklist = models.JSONField(
        "چک‌لیست اعزام",
        default=dict,
        blank=True,
        help_text="کلید آیتم → True/False",
    )
    ai_payload = models.JSONField(
        "خروجی هوش مصنوعی",
        default=dict,
        blank=True,
        help_text="خلاصه تحلیل + اسکریپت شخصی‌سازی‌شده",
    )
    ai_context_hash = models.CharField(
        "هش زمینه AI", max_length=64, blank=True, default=""
    )
    ai_generated_at = models.DateTimeField(
        "زمان تولید AI", null=True, blank=True
    )

    evaluation = models.ForeignKey(
        "core.EvaluationRequest",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="panel_cases",
        verbose_name="ارزیابی مرتبط",
    )
    consultation = models.ForeignKey(
        "core.ConsultationRequest",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="panel_cases",
        verbose_name="مشاوره مرتبط",
    )
    contact_message = models.ForeignKey(
        "core.ContactMessage",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="panel_cases",
        verbose_name="پیام تماس مرتبط",
    )

    created_at = models.DateTimeField("ایجاد", auto_now_add=True)
    updated_at = models.DateTimeField("به‌روزرسانی", auto_now=True)
    closed_at = models.DateTimeField("زمان بستن", null=True, blank=True)

    class Meta:
        verbose_name = "پرونده پیگیری"
        verbose_name_plural = "پرونده‌های پیگیری"
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["status", "next_follow_up_at"], name="panel_case_st_fu_idx"),
            models.Index(fields=["assigned_to", "status"], name="panel_case_asg_st_idx"),
            models.Index(fields=["stage", "status"], name="panel_case_stage_st_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.case_code} — {self.customer.full_name}"

    def apply_stage_progress(self) -> None:
        self.progress = self.STAGE_PROGRESS.get(self.stage, self.progress)

    @property
    def is_overdue(self) -> bool:
        if self.status in (self.STATUS_CLOSED_WON, self.STATUS_CLOSED_LOST):
            return False
        if not self.next_follow_up_at:
            return False
        return self.next_follow_up_at <= timezone.now()

    @property
    def is_due_today(self) -> bool:
        if self.status in (self.STATUS_CLOSED_WON, self.STATUS_CLOSED_LOST):
            return False
        if not self.next_follow_up_at:
            return False
        now = timezone.localtime(timezone.now())
        due = timezone.localtime(self.next_follow_up_at)
        return due.date() == now.date() and self.next_follow_up_at > timezone.now()

    @property
    def follow_up_badge(self) -> str:
        if self.status in (self.STATUS_CLOSED_WON, self.STATUS_CLOSED_LOST):
            return "closed"
        if self.is_overdue:
            return "overdue"
        if self.is_due_today:
            return "today"
        if not self.next_follow_up_at and self.status == self.STATUS_OPEN:
            return "new"
        return "ok"


class CaseEvent(models.Model):
    """رویداد تایم‌لاین پرونده."""

    TYPE_NOTE = "note"
    TYPE_CALL = "call"
    TYPE_STAGE = "stage_change"
    TYPE_ASSIGN = "assign"
    TYPE_CLOSE = "close"
    TYPE_REOPEN = "reopen"
    TYPE_SYSTEM = "system"
    TYPE_CHOICES = [
        (TYPE_NOTE, "یادداشت"),
        (TYPE_CALL, "تماس"),
        (TYPE_STAGE, "تغییر مرحله"),
        (TYPE_ASSIGN, "تخصیص"),
        (TYPE_CLOSE, "مختومه/بستن"),
        (TYPE_REOPEN, "بازگشایی"),
        (TYPE_SYSTEM, "سیستم"),
    ]

    CONTACT_ANSWERED = "answered"
    CONTACT_NO_ANSWER = "no_answer"
    CONTACT_BUSY = "busy"
    CONTACT_CALLBACK = "callback"
    CONTACT_WHATSAPP = "whatsapp"
    CONTACT_NOT_INTERESTED = "not_interested"
    CONTACT_CONVERTED = "converted"
    CONTACT_RESULT_CHOICES = [
        (CONTACT_ANSWERED, "پاسخ داد"),
        (CONTACT_NO_ANSWER, "عدم پاسخ"),
        (CONTACT_BUSY, "مشغول"),
        (CONTACT_CALLBACK, "تماس مجدد"),
        (CONTACT_WHATSAPP, "واتساپ"),
        (CONTACT_NOT_INTERESTED, "عدم علاقه"),
        (CONTACT_CONVERTED, "تبدیل / قرارداد"),
    ]

    case = models.ForeignKey(
        CustomerCase,
        on_delete=models.CASCADE,
        related_name="events",
        verbose_name="پرونده",
    )
    event_type = models.CharField("نوع", max_length=20, choices=TYPE_CHOICES, db_index=True)
    contact_result = models.CharField(
        "نتیجه تماس", max_length=32, blank=True, choices=CONTACT_RESULT_CHOICES
    )
    notes = models.TextField("توضیحات", blank=True)
    next_follow_up_at = models.DateTimeField("پیگیری بعدی", null=True, blank=True)
    meta = models.JSONField("متادیتا", default=dict, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="panel_case_events",
        verbose_name="ثبت‌کننده",
    )
    created_at = models.DateTimeField("زمان", auto_now_add=True)

    class Meta:
        verbose_name = "رویداد پرونده"
        verbose_name_plural = "رویدادهای پرونده"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["case", "created_at"], name="panel_evt_case_cr_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.case.case_code} · {self.get_event_type_display()}"


class CaseAppointment(models.Model):
    """جلسه مشاوره روی تقویم (فاز ۳ تکمیل UI)."""

    KIND_INITIAL = "initial"
    KIND_SPECIALIZED = "specialized"
    KIND_OTHER = "other"
    KIND_CHOICES = [
        (KIND_INITIAL, "مشاوره اولیه"),
        (KIND_SPECIALIZED, "مشاوره تخصصی"),
        (KIND_OTHER, "سایر"),
    ]

    MODE_ONLINE = "online"
    MODE_IN_PERSON = "in_person"
    MODE_CHOICES = [
        (MODE_ONLINE, "آنلاین"),
        (MODE_IN_PERSON, "حضوری"),
    ]

    case = models.ForeignKey(
        CustomerCase,
        on_delete=models.CASCADE,
        related_name="appointments",
        verbose_name="پرونده",
    )
    title = models.CharField("عنوان", max_length=200, blank=True)
    kind = models.CharField("نوع", max_length=20, choices=KIND_CHOICES, default=KIND_INITIAL)
    mode = models.CharField("حالت", max_length=20, choices=MODE_CHOICES, default=MODE_ONLINE)
    starts_at = models.DateTimeField("شروع", db_index=True)
    ends_at = models.DateTimeField("پایان", null=True, blank=True)
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="panel_appointments",
        verbose_name="مشاور",
    )
    consultation = models.ForeignKey(
        "core.ConsultationRequest",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="panel_appointments",
    )
    notes = models.TextField("یادداشت", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "جلسه پرونده"
        verbose_name_plural = "جلسات پرونده"
        ordering = ["starts_at"]

    def __str__(self) -> str:
        return f"{self.case.case_code} @ {self.starts_at}"


def case_document_upload_to(instance, filename: str) -> str:
    return f"panel/cases/{instance.case_id}/{filename}"


class CaseDocument(models.Model):
    """مدرک آپلودشده روی پرونده."""

    case = models.ForeignKey(
        CustomerCase,
        on_delete=models.CASCADE,
        related_name="documents",
        verbose_name="پرونده",
    )
    title = models.CharField("عنوان", max_length=150, blank=True)
    file = models.FileField("فایل", upload_to=case_document_upload_to)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="panel_case_documents",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "مدرک پرونده"
        verbose_name_plural = "مدارک پرونده"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.title or self.file.name


class PanelSettings(models.Model):
    """تنظیمات سراسری پنل (تک‌ردیفی)."""

    MODE_ROUND_ROBIN = "round_robin"
    MODE_LEAST_LOAD = "least_load"
    MODE_FIXED = "fixed"
    MODE_CHOICES = [
        (MODE_ROUND_ROBIN, "نوبتی (گردشی)"),
        (MODE_LEAST_LOAD, "کم‌بارترین مسئول"),
        (MODE_FIXED, "همیشه یک نفر ثابت"),
    ]

    SCOPE_UNASSIGNED = "unassigned"
    SCOPE_FOLLOWUP = "followup_queue"
    SCOPE_CHOICES = [
        (SCOPE_UNASSIGNED, "فقط پرونده‌های بدون مسئول"),
        (SCOPE_FOLLOWUP, "بدون مسئول + موعد امروز/عقب‌افتاده"),
    ]

    auto_assign_enabled = models.BooleanField(
        "تخصیص خودکار پروندهٔ جدید",
        default=False,
        help_text="وقتی پرونده بدون مسئول ساخته شود، خودکار مسئول بگذار.",
    )
    auto_assign_mode = models.CharField(
        "روش تخصیص خودکار",
        max_length=20,
        choices=MODE_CHOICES,
        default=MODE_ROUND_ROBIN,
    )
    fixed_assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="panel_fixed_assignee_settings",
        verbose_name="مسئول ثابت",
    )
    daily_followup_enabled = models.BooleanField(
        "توزیع روزانهٔ خودکار",
        default=False,
        help_text="هر روز یک‌بار صف پیگیری/بدون‌مسئول را بین پرسنل فعال پخش کند.",
    )
    daily_followup_mode = models.CharField(
        "روش توزیع روزانه",
        max_length=20,
        choices=[
            (MODE_ROUND_ROBIN, "نوبتی (گردشی)"),
            (MODE_LEAST_LOAD, "کم‌بارترین مسئول"),
        ],
        default=MODE_LEAST_LOAD,
    )
    daily_followup_scope = models.CharField(
        "دامنهٔ توزیع روزانه",
        max_length=20,
        choices=SCOPE_CHOICES,
        default=SCOPE_FOLLOWUP,
    )
    rr_cursor = models.PositiveIntegerField("نشانگر نوبتی", default=0)
    last_daily_run_on = models.DateField("آخرین اجرای روزانه", null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="panel_settings_updates",
    )

    class Meta:
        verbose_name = "تنظیمات پنل"
        verbose_name_plural = "تنظیمات پنل"

    def __str__(self) -> str:
        return "تنظیمات پنل پیگیری"

    @classmethod
    def load(cls) -> "PanelSettings":
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class StaffAssignmentProfile(models.Model):
    """وضعیت هر حساب برای تخصیص/توزیع خودکار."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="panel_assignment_profile",
        verbose_name="کاربر",
    )
    is_active = models.BooleanField(
        "فعال در تخصیص خودکار",
        default=True,
        help_text="اگر خاموش باشد در نوبت خودکار/روزانه شرکت نمی‌کند.",
    )
    weight = models.PositiveSmallIntegerField(
        "وزن نوبت",
        default=1,
        help_text="عدد بالاتر = سهم بیشتر در نوبتی.",
    )
    sort_order = models.PositiveSmallIntegerField("ترتیب", default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "پروفایل تخصیص پرسنل"
        verbose_name_plural = "پروفایل‌های تخصیص پرسنل"
        ordering = ["sort_order", "user__username"]

    def __str__(self) -> str:
        state = "فعال" if self.is_active else "خاموش"
        return f"{self.user.get_username()} ({state})"
