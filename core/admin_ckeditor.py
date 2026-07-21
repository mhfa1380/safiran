from django.contrib import admin, messages
from django.shortcuts import redirect
from django.urls import path, reverse
from django.utils.html import format_html, format_html_join

from core.ckeditor_assets import (
    delete_ckeditor_file,
    format_bytes,
    index_ckeditor_asset,
    sync_ckeditor_assets_from_disk,
)
from core.admin_export import SafiranExportMixin
from core.models import CkeditorAsset


@admin.register(CkeditorAsset)
class CkeditorAssetAdmin(SafiranExportMixin, admin.ModelAdmin):
    change_list_template = "admin/core/ckeditorasset/change_list.html"
    list_display = (
        "preview_thumb",
        "file_name",
        "size_display",
        "usage_count",
        "categories_summary",
        "primary_category",
        "is_orphan",
        "uploaded_at",
    )
    list_filter = ("is_orphan", "primary_category")
    search_fields = ("path", "categories_summary")
    readonly_fields = (
        "path",
        "file_link",
        "preview_large",
        "size_display",
        "uploaded_at",
        "uploaded_by",
        "usage_count",
        "categories_summary",
        "primary_category",
        "is_orphan",
        "indexed_at",
        "usages_table",
    )
    ordering = ("-uploaded_at", "-id")
    actions = ("action_reindex_selected", "action_delete_orphans")
    fieldsets = (
        (
            "فایل",
            {
                "fields": (
                    "preview_large",
                    "file_link",
                    "path",
                    "size_display",
                    "uploaded_at",
                    "uploaded_by",
                ),
            },
        ),
        (
            "دسته‌بندی و استفاده",
            {
                "fields": (
                    "is_orphan",
                    "usage_count",
                    "primary_category",
                    "categories_summary",
                    "indexed_at",
                    "usages_table",
                ),
            },
        ),
    )

    @admin.display(description="پیش‌نمایش")
    def preview_thumb(self, obj):
        if not obj or not obj.path:
            return "—"
        return format_html(
            '<img src="{}" alt="" style="max-height:48px;max-width:72px;object-fit:cover;border-radius:6px;">',
            obj.file_url,
        )

    @admin.display(description="نام فایل")
    def file_name(self, obj):
        return str(obj)

    @admin.display(description="حجم")
    def size_display(self, obj):
        return format_bytes(obj.size_bytes or 0)

    @admin.display(description="پیش‌نمایش")
    def preview_large(self, obj):
        if not obj or not obj.path:
            return "—"
        return format_html(
            '<img src="{}" alt="" style="max-width:100%;max-height:320px;border-radius:8px;">',
            obj.file_url,
        )

    @admin.display(description="لینک فایل")
    def file_link(self, obj):
        return format_html('<a href="{}" target="_blank" rel="noopener">{}</a>', obj.file_url, obj.file_url)

    @admin.display(description="محل استفاده در محتوا")
    def usages_table(self, obj):
        usages = obj.usage_snapshot or []
        if not usages:
            return format_html('<p style="color:#888;">در هیچ محتوایی استفاده نشده (فایل یتیم).</p>')
        body = format_html_join(
            "",
            "<tr>"
            "<td style='padding:6px;border-bottom:1px solid #eee;'>{}</td>"
            "<td style='padding:6px;border-bottom:1px solid #eee;'>"
            "<a href='{}'>{}</a></td>"
            "<td style='padding:6px;border-bottom:1px solid #eee;'>{}</td>"
            "<td style='padding:6px;border-bottom:1px solid #eee;'><code>{}</code></td>"
            "</tr>",
            [
                (
                    item.get("source_label", "—"),
                    item.get("admin_url", "#"),
                    item.get("title", "—"),
                    item.get("field_label", item.get("field_name", "")),
                    item.get("field_name", ""),
                )
                for item in usages
            ],
        )
        return format_html(
            "<table style='width:100%;border-collapse:collapse;'>"
            "<thead><tr>"
            "<th style='text-align:right;padding:6px;border-bottom:1px solid #ddd;'>دسته</th>"
            "<th style='text-align:right;padding:6px;border-bottom:1px solid #ddd;'>محتوا</th>"
            "<th style='text-align:right;padding:6px;border-bottom:1px solid #ddd;'>فیلد</th>"
            "<th style='text-align:right;padding:6px;border-bottom:1px solid #ddd;'>نام فیلد</th>"
            "</tr></thead><tbody>{}</tbody></table>",
            body,
        )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return True

    def has_delete_permission(self, request, obj=None):
        if obj is None:
            return True
        return obj.is_orphan

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "sync/",
                self.admin_site.admin_view(self.sync_view),
                name="core_ckeditorasset_sync",
            ),
        ]
        return custom + urls

    def sync_view(self, request):
        total, orphans, removed = sync_ckeditor_assets_from_disk()
        messages.success(
            request,
            f"فهرست بروزرسانی شد: {total} فایل، {orphans} بدون استفاده، {removed} رکورد حذف‌شده از دیتابیس.",
        )
        return redirect("admin:core_ckeditorasset_changelist")

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context["sync_url"] = reverse("admin:core_ckeditorasset_sync")
        return super().changelist_view(request, extra_context=extra_context)

    @admin.action(description="بروزرسانی محل استفاده (انتخاب‌شده‌ها)")
    def action_reindex_selected(self, request, queryset):
        for asset in queryset:
            index_ckeditor_asset(asset)
        self.message_user(request, f"{queryset.count()} فایل ایندکس شد.", messages.SUCCESS)

    @admin.action(description="حذف فایل‌های بدون استفاده (انتخاب‌شده)")
    def action_delete_orphans(self, request, queryset):
        deleted = 0
        for asset in queryset.filter(is_orphan=True):
            if delete_ckeditor_file(asset.path):
                asset.delete()
                deleted += 1
        self.message_user(request, f"{deleted} فایل یتیم حذف شد.", messages.SUCCESS)

    def delete_model(self, request, obj):
        if not obj.is_orphan:
            messages.error(request, "فقط فایل‌های بدون استفاده قابل حذف هستند.")
            return
        delete_ckeditor_file(obj.path)
        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        deleted = 0
        for asset in queryset.filter(is_orphan=True):
            if delete_ckeditor_file(asset.path):
                asset.delete()
                deleted += 1
        self.message_user(request, f"{deleted} فایل یتیم حذف شد.", messages.WARNING)
