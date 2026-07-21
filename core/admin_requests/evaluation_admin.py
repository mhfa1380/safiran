"""ادمین کال‌سنتر — درخواست‌های ارزیابی و لاگ تماس."""

from django.contrib import admin
from django.contrib import messages
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html

from core.admin_audit import AdminAuditMixin
from core.admin_export import SafiranExportMixin
from core.admin_referral import ReferralSourceAdminMixin
from core.evaluation_share import build_share_absolute_url, ensure_evaluation_share
from core.models import EvaluationContactLog, EvaluationRequest
from core.utils import format_datetime_both


class EvaluationContactLogInline(admin.TabularInline):
    """لاگ تماس — در بالای فرم پرونده ارزیابی."""

    model = EvaluationContactLog
    extra = 1
    min_num = 0
    classes = ("collapse-open", "eval-contact-log-inline")
    verbose_name = "تماس"
    verbose_name_plural = "لاگ‌های تماس (جدیدترین بالا)"
    fields = (
        "contact_result",
        "notes",
        "follow_up_required",
        "follow_up_category",
        "next_follow_up_at",
        "created_by",
        "created_at",
    )
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)
    show_change_link = True


class FollowUpDueListFilter(admin.SimpleListFilter):
    title = "موعد پیگیری"
    parameter_name = "followup_due"

    def lookups(self, request, model_admin):
        return (
            ("overdue", "عقب‌افتاده"),
            ("today", "امروز"),
            ("upcoming", "آینده (۷ روز)"),
            ("none", "بدون موعد"),
        )

    def queryset(self, request, queryset):
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timezone.timedelta(days=1)
        week_end = today_start + timezone.timedelta(days=7)

        if self.value() == "overdue":
            return queryset.filter(
                follow_up_required=True,
                next_follow_up_at__lt=now,
            ).exclude(status__in=[EvaluationRequest.STATUS_COMPLETED, EvaluationRequest.STATUS_LOST])
        if self.value() == "today":
            return queryset.filter(
                follow_up_required=True,
                next_follow_up_at__gte=today_start,
                next_follow_up_at__lt=today_end,
            )
        if self.value() == "upcoming":
            return queryset.filter(
                follow_up_required=True,
                next_follow_up_at__gte=now,
                next_follow_up_at__lt=week_end,
            )
        if self.value() == "none":
            return queryset.filter(next_follow_up_at__isnull=True, follow_up_required=True)
        return queryset


@admin.register(EvaluationContactLog)
class EvaluationContactLogAdmin(SafiranExportMixin, admin.ModelAdmin):
    """لیست مستقل لاگ‌های تماس — دسترسی سریع از منوی ادمین."""

    list_display = (
        "created_at_both_display",
        "applicant_name",
        "applicant_phone",
        "contact_result",
        "follow_up_required",
        "follow_up_category",
        "next_follow_up_at_display",
        "notes_short",
        "created_by",
        "evaluation_link",
    )
    list_filter = (
        "contact_result",
        "follow_up_required",
        "follow_up_category",
        ("created_at", admin.DateFieldListFilter),
    )
    search_fields = (
        "notes",
        "evaluation__full_name",
        "evaluation__phone",
        "evaluation__email",
    )
    date_hierarchy = "created_at"
    list_per_page = 40
    list_select_related = ("evaluation", "created_by")
    autocomplete_fields = ("evaluation",)
    readonly_fields = ("created_at", "created_by")
    ordering = ("-created_at",)

    fieldsets = (
        (
            "تماس",
            {
                "fields": (
                    "evaluation",
                    "contact_result",
                    "notes",
                ),
            },
        ),
        (
            "پیگیری",
            {
                "fields": (
                    "follow_up_required",
                    "follow_up_category",
                    "next_follow_up_at",
                ),
            },
        ),
        (
            "سیستم",
            {
                "classes": ("collapse",),
                "fields": ("created_by", "created_at"),
            },
        ),
    )

    def save_model(self, request, obj, form, change):
        if not obj.created_by_id:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    @admin.display(description="تاریخ")
    def created_at_both_display(self, obj):
        return format_datetime_both(obj.created_at) if obj else "-"

    @admin.display(description="متقاضی")
    def applicant_name(self, obj):
        return obj.evaluation.full_name if obj and obj.evaluation_id else "—"

    @admin.display(description="تلفن")
    def applicant_phone(self, obj):
        return obj.evaluation.phone if obj and obj.evaluation_id else "—"

    @admin.display(description="پیگیری بعدی")
    def next_follow_up_at_display(self, obj):
        if not obj or not obj.next_follow_up_at:
            return "—"
        text = format_datetime_both(obj.next_follow_up_at)
        if obj.evaluation_id and obj.evaluation.is_follow_up_overdue:
            return format_html('<span class="eval-admin-overdue">{}</span>', text)
        return text

    @admin.display(description="خلاصه")
    def notes_short(self, obj):
        if not obj or not obj.notes:
            return "—"
        return obj.notes[:50] + ("…" if len(obj.notes) > 50 else "")

    @admin.display(description="پرونده")
    def evaluation_link(self, obj):
        if not obj or not obj.evaluation_id:
            return "—"
        url = reverse("admin:core_evaluationrequest_change", args=[obj.evaluation_id])
        return format_html('<a href="{}">{}</a>', url, obj.evaluation.full_name)


class EvaluationCallCenterAdmin(
    ReferralSourceAdminMixin, SafiranExportMixin, AdminAuditMixin, admin.ModelAdmin
):
    """پنل کال‌سنتر برای پیگیری فرم‌های ارزیابی."""

    change_form_template = "admin/core/evaluationrequest/change_form.html"
    list_display = (
        "full_name",
        "phone",
        "referral_display_column",
        "status_badge",
        "priority_badge",
        "contact_result",
        "follow_up_required",
        "follow_up_category",
        "next_follow_up_at_display",
        "recommendation_short",
        "target_country",
        "assigned_to",
        "created_at_both_display",
    )
    list_filter = (
        "referral_source",
        "referral_social_platform",
        "status",
        "priority",
        "follow_up_required",
        FollowUpDueListFilter,
        "follow_up_category",
        "contact_result",
        "target_country",
        "current_degree",
        "has_financial_capacity",
        "assigned_to",
    )
    search_fields = (
        "full_name",
        "phone",
        "email",
        "field_of_study",
        "desired_major",
        "admin_notes",
        "notes",
    )
    date_hierarchy = "created_at"
    list_per_page = 30
    list_select_related = ("assigned_to",)
    ordering = ("-created_at",)
    inlines = (EvaluationContactLogInline,)
    autocomplete_fields = ("assigned_to",)
    save_on_top = True
    readonly_fields = (
        "created_at",
        "updated_at",
        "recommendation_display",
        "applicant_summary",
    )
    fieldsets = (
        (
            "کال‌سنتر — وضعیت و اولویت",
            {
                "fields": (
                    "status",
                    "priority",
                    "assigned_to",
                ),
            },
        ),
        (
            "تماس و پیگیری",
            {
                "fields": (
                    "contact_result",
                    "follow_up_required",
                    "follow_up_category",
                    "contacted_at",
                    "next_follow_up_at",
                    "admin_notes",
                ),
            },
        ),
        (
            "خلاصه متقاضی",
            {
                "fields": ("applicant_summary",),
            },
        ),
        (
            "پیشنهاد هوشمند (هنگام ثبت فرم)",
            {
                "classes": ("collapse",),
                "fields": ("recommendation_display",),
            },
        ),
        (
            "اطلاعات شخصی",
            {
                "classes": ("collapse",),
                "fields": (
                    "full_name",
                    "phone",
                    "email",
                    "birth_year",
                    "marital_status",
                    "apply_timeline",
                    "has_financial_capacity",
                ),
            },
        ),
        (
            "سوابق تحصیلی و زبان",
            {
                "classes": ("collapse",),
                "fields": (
                    "current_degree",
                    "field_of_study",
                    "average_grade",
                    "graduation_year",
                    "language_test_type",
                    "has_ielts",
                    "language_score",
                    "has_journal_article",
                    "has_conference_article",
                    "has_book",
                    "has_international_tests",
                ),
            },
        ),
        (
            "اولویت‌های متقاضی",
            {
                "classes": ("collapse",),
                "fields": (
                    "target_country",
                    "desired_countries",
                    "desired_major",
                    "service_scope",
                    "preferred_intake",
                    "notes",
                ),
            },
        ),
        (
            "منبع آشنایی",
            {
                "fields": (
                    "referral_summary_admin",
                    "referral_source",
                    "referral_social_platform",
                    "referral_detail",
                ),
            },
        ),
        (
            "سیستم",
            {
                "classes": ("collapse",),
                "fields": ("admin_seen_at", "created_at", "updated_at", "recommendation_snapshot"),
            },
        ),
    )
    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for obj in instances:
            if isinstance(obj, EvaluationContactLog) and not obj.created_by_id:
                obj.created_by = request.user
            obj.save()
        for obj in formset.deleted_objects:
            obj.delete()
        formset.save_m2m()

    actions = (
        "action_mark_contacted",
        "action_mark_follow_up",
        "action_mark_in_progress",
        "action_mark_completed",
        "action_mark_lost",
        "action_clear_follow_up",
    )

    def change_view(self, request, object_id, form_url="", extra_context=None):
        extra_context = extra_context or {}
        obj = self.get_object(request, object_id)
        if obj is not None:
            share = ensure_evaluation_share(obj)
            extra_context["evaluation_result_url"] = build_share_absolute_url(
                request, share
            )
            extra_context["evaluation_result_expires_display"] = format_datetime_both(
                share.expires_at
            )
        return super().change_view(
            request, object_id, form_url, extra_context=extra_context
        )

    @admin.display(description="تاریخ ثبت")
    def created_at_both_display(self, obj):
        return format_datetime_both(obj.created_at) if obj else "-"

    @admin.display(description="پیگیری بعدی")
    def next_follow_up_at_display(self, obj):
        if not obj or not obj.next_follow_up_at:
            return "—"
        text = format_datetime_both(obj.next_follow_up_at)
        if obj.is_follow_up_overdue:
            return format_html('<span class="eval-admin-overdue">{}</span>', text)
        return text

    @admin.display(description="پیشنهاد")
    def recommendation_short(self, obj):
        line = obj.get_recommendation_top_line() if obj else ""
        if not line:
            return "—"
        return line[:60] + ("…" if len(line) > 60 else "")

    @admin.display(description="وضعیت")
    def status_badge(self, obj):
        colors = {
            EvaluationRequest.STATUS_NEW: "#2563eb",
            EvaluationRequest.STATUS_CONTACTED: "#0891b2",
            EvaluationRequest.STATUS_FOLLOW_UP: "#d97706",
            EvaluationRequest.STATUS_IN_PROGRESS: "#7c3aed",
            EvaluationRequest.STATUS_COMPLETED: "#059669",
            EvaluationRequest.STATUS_LOST: "#6b7280",
        }
        color = colors.get(obj.status, "#374151")
        return format_html(
            '<span class="eval-admin-badge" style="background:{};">{}</span>',
            color,
            obj.get_status_display(),
        )

    @admin.display(description="اولویت")
    def priority_badge(self, obj):
        colors = {
            EvaluationRequest.PRIORITY_LOW: "#9ca3af",
            EvaluationRequest.PRIORITY_NORMAL: "#64748b",
            EvaluationRequest.PRIORITY_HIGH: "#ea580c",
            EvaluationRequest.PRIORITY_URGENT: "#dc2626",
        }
        color = colors.get(obj.priority, "#64748b")
        return format_html(
            '<span class="eval-admin-badge" style="background:{};">{}</span>',
            color,
            obj.get_priority_display(),
        )

    @admin.display(description="پیشنهاد هوشمند")
    def recommendation_display(self, obj):
        snap = obj.recommendation_snapshot if obj else None
        if not snap:
            return "— (پس از ثبت فرم ذخیره می‌شود)"
        if not snap.get("has_data"):
            return snap.get("message", "داده کافی نیست")
        top = snap.get("top_pick") or {}
        lines = [
            f"<strong>تطابق:</strong> {top.get('match_percent', '—')}٪",
            f"<strong>خلاصه:</strong> {top.get('summary', '')}",
        ]
        country = (top.get("country") or {}).get("name", "")
        uni = (top.get("university") or {}).get("name_fa", "")
        major = (top.get("major") or {}).get("title", "")
        if country:
            lines.append(f"<strong>کشور:</strong> {country}")
        if uni:
            lines.append(f"<strong>دانشگاه:</strong> {uni}")
        if major:
            lines.append(f"<strong>رشته:</strong> {major}")
        return format_html("<br>".join(lines))

    @admin.display(description="خلاصه پرونده")
    def applicant_summary(self, obj):
        if not obj:
            return "—"
        parts = [
            f"<strong>نام:</strong> {obj.full_name}",
            f"<strong>تلفن:</strong> {obj.phone}",
            f"<strong>مقطع:</strong> {obj.get_current_degree_display()}",
            f"<strong>رشته:</strong> {obj.field_of_study}",
            f"<strong>معدل:</strong> {obj.average_grade}",
            f"<strong>کشور مقصد:</strong> {obj.get_target_country_display()}",
        ]
        if obj.desired_major:
            parts.append(f"<strong>رشته مورد نظر:</strong> {obj.desired_major}")
        if obj.referral_source:
            parts.append(f"<strong>از کجا آشنا شد:</strong> {obj.referral_display}")
        return format_html("<br>".join(parts))

    @admin.action(description="علامت‌گذاری: تماس گرفته شد")
    def action_mark_contacted(self, request, queryset):
        n = queryset.update(
            status=EvaluationRequest.STATUS_CONTACTED,
            contact_result=EvaluationRequest.CONTACT_ANSWERED,
            contacted_at=timezone.now(),
        )
        self.message_user(request, f"{n} پرونده به‌روز شد.", messages.SUCCESS)

    @admin.action(description="علامت‌گذاری: نیاز به پیگیری")
    def action_mark_follow_up(self, request, queryset):
        n = queryset.update(
            status=EvaluationRequest.STATUS_FOLLOW_UP,
            follow_up_required=True,
        )
        self.message_user(request, f"{n} پرونده برای پیگیری علامت خورد.", messages.SUCCESS)

    @admin.action(description="علامت‌گذاری: در حال پیگیری")
    def action_mark_in_progress(self, request, queryset):
        n = queryset.update(status=EvaluationRequest.STATUS_IN_PROGRESS)
        self.message_user(request, f"{n} پرونده در حال پیگیری است.", messages.SUCCESS)

    @admin.action(description="علامت‌گذاری: تکمیل / قرارداد")
    def action_mark_completed(self, request, queryset):
        n = queryset.update(
            status=EvaluationRequest.STATUS_COMPLETED,
            contact_result=EvaluationRequest.CONTACT_CONVERTED,
            follow_up_required=False,
        )
        self.message_user(request, f"{n} پرونده تکمیل شد.", messages.SUCCESS)

    @admin.action(description="علامت‌گذاری: منصرف / بسته")
    def action_mark_lost(self, request, queryset):
        n = queryset.update(
            status=EvaluationRequest.STATUS_LOST,
            contact_result=EvaluationRequest.CONTACT_NOT_INTERESTED,
            follow_up_required=False,
        )
        self.message_user(request, f"{n} پرونده بسته شد.", messages.SUCCESS)

    @admin.action(description="برداشتن نیاز پیگیری")
    def action_clear_follow_up(self, request, queryset):
        n = queryset.update(follow_up_required=False, next_follow_up_at=None)
        self.message_user(request, f"پیگیری برای {n} پرونده غیرفعال شد.", messages.SUCCESS)
