from django.contrib import admin
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import path
from django.utils import timezone

from core.management.commands.reserve_random_consultation_slots import (
    run_reserve_random_slots,
    _format_message,
)
from core.models import ConsultationRequest, ConsultationSlot, ContactMessage, EvaluationRequest
from core.utils import format_date_both, format_datetime_both


def _mark_seen(model_class, queryset_filter=None):
    """وقتی ادمین لیست را می‌بیند، موارد را مشاهده‌شده علامت می‌زند."""
    qs = model_class.objects.filter(admin_seen_at__isnull=True)
    if queryset_filter:
        qs = qs.filter(**queryset_filter)
    qs.update(admin_seen_at=timezone.now())


@admin.register(ConsultationSlot)
class ConsultationSlotAdmin(admin.ModelAdmin):
    list_display = ("date_both_display", "time_label", "is_booked", "order")

    def date_both_display(self, obj):
        return format_date_both(obj.date) if obj else "-"

    date_both_display.short_description = "تاریخ"
    list_filter = ("date", "is_booked")
    list_editable = ("is_booked", "order")
    ordering = ["date", "order"]
    change_list_template = "admin/core/consultationslot/change_list.html"

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
class ConsultationRequestAdmin(admin.ModelAdmin):
    list_display = ("full_name", "phone", "slot", "interest_university", "country", "consultation_type", "status", "created_at_both_display")

    def created_at_both_display(self, obj):
        return format_datetime_both(obj.created_at) if obj else "-"

    created_at_both_display.short_description = "تاریخ ثبت"

    def changelist_view(self, request, extra_context=None):
        _mark_seen(ConsultationRequest)
        return super().changelist_view(request, extra_context)
    list_filter = ("status", "consultation_type", "country")
    search_fields = ("full_name", "phone", "email")


@admin.register(EvaluationRequest)
class EvaluationRequestAdmin(admin.ModelAdmin):
    list_display = ("full_name", "phone", "target_country", "current_degree", "average_grade", "created_at_both_display")

    def created_at_both_display(self, obj):
        return format_datetime_both(obj.created_at) if obj else "-"

    created_at_both_display.short_description = "تاریخ ثبت"

    def changelist_view(self, request, extra_context=None):
        _mark_seen(EvaluationRequest)
        return super().changelist_view(request, extra_context)
    list_filter = ("target_country", "current_degree", "apply_timeline")
    search_fields = ("full_name", "phone", "email", "field_of_study")


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("full_name", "email", "subject", "status", "created_at_both_display")

    def created_at_both_display(self, obj):
        return format_datetime_both(obj.created_at) if obj else "-"

    created_at_both_display.short_description = "تاریخ ثبت"

    def changelist_view(self, request, extra_context=None):
        _mark_seen(ContactMessage)
        return super().changelist_view(request, extra_context)
    list_filter = ("status",)
    search_fields = ("full_name", "email", "subject", "message")
