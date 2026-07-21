"""ادمین لاگ تغییرات — مشاهده و بازگردانی."""

from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404, redirect
from django.urls import path, reverse
from django.utils.html import format_html

from core.admin_audit import revert_change_log
from core.admin_export import SafiranExportMixin
from core.models import AdminChangeLog
from core.utils import format_datetime_both


@admin.register(AdminChangeLog)
class AdminChangeLogAdmin(SafiranExportMixin, admin.ModelAdmin):
    list_display = (
        "created_at_display",
        "action",
        "object_repr",
        "user",
        "changed_fields_short",
        "revert_status",
    )
    list_filter = ("action", "content_type", "reverted_at")
    search_fields = ("object_repr", "object_id", "note", "user__username")
    readonly_fields = (
        "user",
        "content_type",
        "object_id",
        "object_repr",
        "action",
        "payload",
        "note",
        "reverted_at",
        "reverted_by",
        "created_at",
        "revert_button",
    )
    date_hierarchy = "created_at"
    ordering = ("-created_at",)

    def has_module_permission(self, request):
        return request.user.is_superuser

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    @admin.display(description="زمان")
    def created_at_display(self, obj):
        return format_datetime_both(obj.created_at)

    @admin.display(description="فیلدهای تغییر")
    def changed_fields_short(self, obj):
        fields = obj.changed_fields
        if not fields:
            return "—"
        text = ", ".join(fields[:5])
        if len(fields) > 5:
            text += f" (+{len(fields) - 5})"
        return text

    @admin.display(description="بازگردانی")
    def revert_status(self, obj):
        if obj.reverted_at:
            return format_html('<span style="color:#059669">انجام شد</span>')
        if obj.can_revert:
            url = reverse("admin:core_adminchangelog_revert", args=[obj.pk])
            return format_html('<a class="button" href="{}">بازگردانی</a>', url)
        return "—"

    @admin.display(description="بازگردانی")
    def revert_button(self, obj):
        return self.revert_status(obj)

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "<int:log_id>/revert/",
                self.admin_site.admin_view(self.revert_view),
                name="core_adminchangelog_revert",
            ),
        ]
        return custom + urls

    def revert_view(self, request, log_id):
        if not request.user.is_staff:
            raise PermissionDenied
        log = get_object_or_404(AdminChangeLog, pk=log_id)
        if not log.can_revert:
            messages.error(request, "این تغییر قابل بازگردانی نیست.")
            return redirect("admin:core_adminchangelog_change", log.pk)

        if request.method == "POST":
            try:
                obj = revert_change_log(log, user=request.user)
                messages.success(
                    request,
                    f"بازگردانی انجام شد. شیء: {obj}",
                )
            except ValidationError as exc:
                messages.error(request, str(exc))
            except Exception as exc:
                messages.error(request, f"خطا در بازگردانی: {exc}")
            return redirect("admin:core_adminchangelog_changelist")

        context = {
            **self.admin_site.each_context(request),
            "title": f"بازگردانی — {log.object_repr}",
            "log": log,
            "opts": self.model._meta,
        }
        return self.admin_site.render(
            request,
            "admin/core/adminchangelog/revert_confirm.html",
            context,
        )
