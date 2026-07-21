from django.contrib import admin
from django.core.cache import cache

from core.admin_audit import AdminAuditMixin
from core.admin_export import SafiranExportMixin
from core.models import University, UniversityFAQ, UniversityGalleryImage, UniversityMajorLink
from core.widgets import rich_text_widget


class ClearCacheAdminMixin(SafiranExportMixin, AdminAuditMixin):
    """لاگ تغییرات + پاک کردن کش بعد از هر تغییر در ادمین."""

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        cache.clear()

    def delete_model(self, request, obj):
        super().delete_model(request, obj)
        cache.clear()

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        cache.clear()


class UniversityGalleryImageInline(admin.TabularInline):
    model = UniversityGalleryImage
    extra = 0


class UniversityFAQInline(admin.TabularInline):
    model = UniversityFAQ
    extra = 1
    ordering = ("order",)


class UniversityMajorLinkInline(admin.TabularInline):
    model = UniversityMajorLink
    extra = 0
    ordering = ("order",)
    autocomplete_fields = ("major",)
    fields = ("major", "is_featured", "order")

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "major" and request.resolver_match:
            obj_id = request.resolver_match.kwargs.get("object_id")
            if obj_id:
                try:
                    uni = University.objects.only("country").get(pk=obj_id)
                    kwargs["queryset"] = kwargs.get("queryset", db_field.remote_field.model.objects.all()).filter(
                        country=uni.country,
                        is_active=True,
                    )
                except University.DoesNotExist:
                    pass
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(University)
class UniversityAdmin(ClearCacheAdminMixin, admin.ModelAdmin):
    list_display = ("name_fa", "name_en", "country", "city", "type", "world_rank")
    list_filter = ("country", "type", "is_approved_by_mo_science", "is_approved_by_mo_health")
    search_fields = ("name_fa", "name_en", "city")
    prepopulated_fields = {"slug": ("name_en",)}
    inlines = [UniversityGalleryImageInline, UniversityFAQInline, UniversityMajorLinkInline]
    save_on_top = True
    readonly_fields = ("created_at",)
    fieldsets = (
        (
            "نام و شناسه",
            {"fields": ("slug", "name_fa", "name_en", "image")},
        ),
        (
            "موقعیت و نوع",
            {"fields": ("country", "city", "type", "world_rank", "website")},
        ),
        ("توضیحات", {"fields": ("short_description", "description")}),
        (
            "تأییدیه‌های وزارت",
            {"fields": ("is_approved_by_mo_science", "is_approved_by_mo_health")},
        ),
        ("سئو", {"fields": ("meta_title", "meta_description"), "classes": ("collapse",)}),
        (
            "سیستم",
            {"classes": ("collapse",), "fields": ("created_at",)},
        ),
    )

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == "description":
            kwargs["widget"] = rich_text_widget(request)
        return super().formfield_for_dbfield(db_field, request, **kwargs)
