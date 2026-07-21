from django.contrib import admin
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import path
from django.utils import timezone

from core.management.commands.reserve_random_consultation_slots import (
    run_reserve_random_slots,
    _format_message,
)
from core.admin_audit import AdminAuditMixin
from core.admin_export import SafiranExportMixin
from core.admin_referral import ReferralSourceAdminMixin
from core.admin_requests.evaluation_admin import EvaluationCallCenterAdmin
from core.models import ConsultationRequest, ConsultationSlot, ContactMessage, EvaluationRequest
from core.utils import format_date_both, format_datetime_both


def _mark_seen(model_class, queryset_filter=None):
    """وقتی ادمین لیست را می‌بیند، موارد را مشاهده‌شده علامت می‌زند."""
    qs = model_class.objects.filter(admin_seen_at__isnull=True)
    if queryset_filter:
        qs = qs.filter(**queryset_filter)
    if qs.exists():
        qs.update(admin_seen_at=timezone.now())
        from core.admin_site import invalidate_admin_menu_cache

        invalidate_admin_menu_cache()


@admin.register(ConsultationSlot)
class ConsultationSlotAdmin(SafiranExportMixin, AdminAuditMixin, admin.ModelAdmin):
    list_display = ("date_both_display", "time_label", "is_booked", "order")
    list_filter = ("date", "is_booked")
    list_editable = ("is_booked", "order")
    ordering = ["date", "order"]
    search_fields = ("time_label",)
    save_on_top = True
    change_list_template = "admin/core/consultationslot/change_list.html"
    fieldsets = (
        ("زمان رزرو", {"fields": ("date", "time_label", "order")}),
        ("وضعیت", {"fields": ("is_booked",)}),
        (
            "سیستم",
            {
                "classes": ("collapse",),
                "fields": ("admin_seen_at",),
            },
        ),
    )
    readonly_fields = ("admin_seen_at",)

    def date_both_display(self, obj):
        return format_date_both(obj.date) if obj else "-"

    date_both_display.short_description = "تاریخ"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "reserve-random/",
                self.admin_site.admin_view(self.reserve_random_slots),
                name="core_consultationslot_reserve_random",
            ),
        ]
        return custom_urls + urls

    def changelist_view(self, request, extra_context=None):
        _mark_seen(ConsultationSlot, {"is_booked": True})
        return super().changelist_view(request, extra_context)

    def reserve_random_slots(self, request):
        """ساخت اسلات‌های ۱ هفته (۹ تا ۱۷) + رزرو رندوم."""
        result = run_reserve_random_slots()
        message = _format_message(result, lang="fa")
        messages.success(request, message)
        return HttpResponseRedirect("../")


@admin.register(ConsultationRequest)
class ConsultationRequestAdmin(
    ReferralSourceAdminMixin, SafiranExportMixin, AdminAuditMixin, admin.ModelAdmin
):
    list_display = (
        "full_name",
        "phone",
        "referral_display_column",
        "slot",
        "interest_university",
        "country",
        "consultation_type",
        "status",
        "created_at_both_display",
    )
    list_editable = ("status",)
    ordering = ("-created_at",)
    save_on_top = True
    date_hierarchy = "created_at"
    list_filter = (
        "status",
        "consultation_type",
        "country",
        "referral_source",
        "referral_social_platform",
    )
    search_fields = ("full_name", "phone", "email")
    autocomplete_fields = ("slot", "interest_university")
    readonly_fields = ("admin_seen_at", "created_at", "updated_at")
    fieldsets = (
        (
            "اطلاعات متقاضی",
            {"fields": ("full_name", "phone", "email")},
        ),
        (
            "جزئیات مشاوره",
            {
                "fields": (
                    "consultation_type",
                    "country",
                    "slot",
                    "interest_university",
                    "description",
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
        ("پیگیری", {"fields": ("status",)}),
        (
            "سیستم",
            {
                "classes": ("collapse",),
                "fields": ("admin_seen_at", "created_at", "updated_at"),
            },
        ),
    )

    def created_at_both_display(self, obj):
        return format_datetime_both(obj.created_at) if obj else "-"

    created_at_both_display.short_description = "تاریخ ثبت"

    def changelist_view(self, request, extra_context=None):
        _mark_seen(ConsultationRequest)
        return super().changelist_view(request, extra_context)


@admin.register(EvaluationRequest)
class EvaluationRequestAdmin(EvaluationCallCenterAdmin):
    def changelist_view(self, request, extra_context=None):
        _mark_seen(EvaluationRequest)
        return super().changelist_view(request, extra_context)


@admin.register(ContactMessage)
class ContactMessageAdmin(SafiranExportMixin, AdminAuditMixin, admin.ModelAdmin):
    list_display = ("full_name", "email", "subject", "status", "created_at_both_display")
    list_editable = ("status",)
    ordering = ("-created_at",)
    save_on_top = True
    date_hierarchy = "created_at"
    list_filter = ("status",)
    search_fields = ("full_name", "email", "subject", "message")
    readonly_fields = ("admin_seen_at", "created_at")
    fieldsets = (
        (
            "فرستنده",
            {"fields": ("full_name", "email")},
        ),
        (
            "پیام",
            {"fields": ("subject", "message")},
        ),
        ("پیگیری", {"fields": ("status",)}),
        (
            "سیستم",
            {
                "classes": ("collapse",),
                "fields": ("admin_seen_at", "created_at"),
            },
        ),
    )

    def created_at_both_display(self, obj):
        return format_datetime_both(obj.created_at) if obj else "-"

    created_at_both_display.short_description = "تاریخ ثبت"

    def changelist_view(self, request, extra_context=None):
        _mark_seen(ContactMessage)
        return super().changelist_view(request, extra_context)
