from django.contrib import admin

from panel.models import (
    CaseAppointment,
    CaseDocument,
    CaseEvent,
    Customer,
    CustomerCase,
    PanelSettings,
    StaffAssignmentProfile,
)


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("full_name", "phone_display", "phone_normalized", "email", "updated_at")
    search_fields = ("full_name", "phone_normalized", "phone_display", "email")


class CaseEventInline(admin.TabularInline):
    model = CaseEvent
    extra = 0
    readonly_fields = ("created_at", "created_by")


@admin.register(CustomerCase)
class CustomerCaseAdmin(admin.ModelAdmin):
    list_display = (
        "case_code",
        "customer",
        "stage",
        "status",
        "assigned_to",
        "next_follow_up_at",
        "source_type",
        "progress",
    )
    list_filter = ("stage", "status", "source_type", "priority")
    search_fields = ("case_code", "customer__full_name", "customer__phone_normalized")
    raw_id_fields = ("customer", "evaluation", "consultation", "contact_message", "assigned_to")
    inlines = [CaseEventInline]


@admin.register(CaseEvent)
class CaseEventAdmin(admin.ModelAdmin):
    list_display = ("case", "event_type", "contact_result", "created_by", "created_at")
    list_filter = ("event_type",)


@admin.register(CaseAppointment)
class CaseAppointmentAdmin(admin.ModelAdmin):
    list_display = ("case", "kind", "mode", "starts_at", "assignee")
    list_filter = ("kind", "mode")


@admin.register(CaseDocument)
class CaseDocumentAdmin(admin.ModelAdmin):
    list_display = ("case", "title", "uploaded_by", "created_at")
    raw_id_fields = ("case", "uploaded_by")


@admin.register(PanelSettings)
class PanelSettingsAdmin(admin.ModelAdmin):
    list_display = (
        "auto_assign_enabled",
        "auto_assign_mode",
        "daily_followup_enabled",
        "last_daily_run_on",
        "updated_at",
    )


@admin.register(StaffAssignmentProfile)
class StaffAssignmentProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "is_active", "weight", "sort_order", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("user__username", "user__first_name", "user__last_name")
