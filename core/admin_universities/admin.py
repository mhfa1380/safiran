from django.contrib import admin
from django.core.cache import cache

from core.models import University, UniversityFAQ, UniversityGalleryImage
from core.widgets import RichTextEditorWidget


class ClearCacheAdminMixin:
    """Mixin برای پاک کردن کش بعد از هر تغییر در ادمین."""

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


@admin.register(University)
class UniversityAdmin(ClearCacheAdminMixin, admin.ModelAdmin):
    list_display = ("name_fa", "name_en", "country", "city", "type", "world_rank")
    list_filter = ("country", "type", "is_approved_by_mo_science", "is_approved_by_mo_health")
    search_fields = ("name_fa", "name_en", "city")
    prepopulated_fields = {"slug": ("name_en",)}
    inlines = [UniversityGalleryImageInline, UniversityFAQInline]
    fieldsets = (
        (None, {"fields": ("slug", "name_fa", "name_en", "image")}),
        ("اطلاعات اصلی", {"fields": ("country", "city", "type", "world_rank", "website")}),
        ("توضیحات", {"fields": ("short_description", "description")}),
        ("سئو", {"fields": ("meta_title", "meta_description"), "classes": ("collapse",)}),
        ("تأییدیه‌ها", {"fields": ("is_approved_by_mo_science", "is_approved_by_mo_health")}),
    )

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == "description":
            kwargs["widget"] = RichTextEditorWidget
        return super().formfield_for_dbfield(db_field, request, **kwargs)
