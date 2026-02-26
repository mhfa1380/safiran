import re

from django import forms
from django.contrib import admin
from django.core.cache import cache

from core.models import BlogPost, Course, CourseFAQ, CourseSyllabus, FAQ, Major, MajorFAQ, Service
from core.utils import format_datetime_both
from core.widgets import RichTextEditorWidget


def is_empty_html(value):
    """بررسی می‌کند آیا محتوای HTML خالی است (فقط تگ‌های خالی، فاصله، br)."""
    if not value or not isinstance(value, str):
        return True
    stripped = re.sub(r"<[^>]+>", "", value)
    stripped = stripped.replace("&nbsp;", " ").strip()
    return len(stripped) == 0


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


@admin.register(BlogPost)
class BlogPostAdmin(ClearCacheAdminMixin, admin.ModelAdmin):
    list_display = ("title", "country_tag", "is_published", "created_at_both_display")

    def created_at_both_display(self, obj):
        return format_datetime_both(obj.created_at) if obj else "-"

    created_at_both_display.short_description = "تاریخ انتشار"
    list_filter = ("is_published", "country_tag")
    search_fields = ("title", "excerpt", "content")

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == "content":
            kwargs["widget"] = RichTextEditorWidget
        return super().formfield_for_dbfield(db_field, request, **kwargs)


@admin.register(FAQ)
class FAQAdmin(ClearCacheAdminMixin, admin.ModelAdmin):
    list_display = ("question", "order", "is_active")
    list_filter = ("is_active",)
    search_fields = ("question", "answer")
    list_editable = ("order", "is_active")


@admin.register(Service)
class ServiceAdmin(ClearCacheAdminMixin, admin.ModelAdmin):
    list_display = ("title", "order", "is_active")
    list_editable = ("order", "is_active")
    fieldsets = (
        (None, {"fields": ("title", "icon", "order", "is_active")}),
        ("توضیحات", {"fields": ("short_description", "description")}),
    )


class MajorAdminForm(forms.ModelForm):
    """فرم رشته با پاک‌سازی فیلد توضیحات و امکان خالی گذاشتن."""

    class Meta:
        model = Major
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["description"].required = False

    def clean_description(self):
        value = self.cleaned_data.get("description")
        return "" if is_empty_html(value) else (value or "")


class CourseSyllabusInline(admin.TabularInline):
    model = CourseSyllabus
    extra = 1
    ordering = ("order",)


class CourseFAQInline(admin.TabularInline):
    model = CourseFAQ
    extra = 1
    ordering = ("order",)


class MajorFAQInline(admin.TabularInline):
    model = MajorFAQ
    extra = 1
    ordering = ("order",)


@admin.register(Major)
class MajorAdmin(ClearCacheAdminMixin, admin.ModelAdmin):
    form = MajorAdminForm
    list_display = ("title", "slug", "country", "order", "is_active")
    list_filter = ("country",)
    list_editable = ("order", "is_active")
    search_fields = ("title",)
    prepopulated_fields = {"slug": ("title",)}
    inlines = [MajorFAQInline]
    fieldsets = (
        (None, {"fields": ("title", "slug", "short_description", "order", "is_active")}),
        ("محتوا", {"fields": ("description", "image", "country")}),
    )

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == "description":
            kwargs["widget"] = RichTextEditorWidget
            kwargs["required"] = False
        return super().formfield_for_dbfield(db_field, request, **kwargs)


class CourseAdminForm(forms.ModelForm):
    """فرم دوره با پاک‌سازی فیلدهای اختیاری CKEditor و امکان خالی گذاشتن."""

    class Meta:
        model = Course
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ("description", "objectives", "conditions"):
            self.fields[name].required = False

    def clean_description(self):
        value = self.cleaned_data.get("description")
        return "" if is_empty_html(value) else (value or "")

    def clean_objectives(self):
        value = self.cleaned_data.get("objectives")
        return "" if is_empty_html(value) else (value or "")

    def clean_conditions(self):
        value = self.cleaned_data.get("conditions")
        return "" if is_empty_html(value) else (value or "")


@admin.register(Course)
class CourseAdmin(ClearCacheAdminMixin, admin.ModelAdmin):
    form = CourseAdminForm
    list_display = ("title", "country", "duration_hours", "delivery_mode", "order", "is_active")
    list_filter = ("country", "delivery_mode")
    list_editable = ("order", "is_active")
    search_fields = ("title",)
    inlines = [CourseSyllabusInline, CourseFAQInline]
    fieldsets = (
        (None, {"fields": ("title", "slug", "short_description", "order", "is_active")}),
        ("اطلاعات دوره", {"fields": ("description", "objectives", "conditions", "features", "duration_hours", "price", "delivery_mode", "sample_video")}),
        ("تصویر و کشور", {"fields": ("image", "country")}),
    )

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name in ("description", "objectives", "conditions"):
            kwargs["widget"] = RichTextEditorWidget
            kwargs["required"] = False
        return super().formfield_for_dbfield(db_field, request, **kwargs)
