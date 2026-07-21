import re

from django import forms
from django.contrib import admin
from django.core.cache import cache
from django.utils.html import format_html

from core.models import (
    BlogAuthor,
    BlogPost,
    Course,
    CourseFAQ,
    CourseInstructor,
    CourseInstructorResumeEntry,
    CourseSyllabus,
    FAQ,
    FAQCategory,
    LivingAllowanceCountry,
    Major,
    MajorFAQ,
    UniversityMajorLink,
    MonthlyAchievement,
    PricingCategory,
    PricingTariff,
    Service,
    ServiceCategory,
    CountryScholarship,
    CountryScholarshipGuide,
    StudyCountry,
)
from core.admin_audit import AdminAuditMixin
from core.admin_export import SafiranExportMixin
from core.utils import format_datetime_both
from core.widgets import rich_text_widget

import core.admin_audit_admin  # noqa: F401 — ثبت AdminChangeLog در ادمین
import core.admin_ckeditor  # noqa: F401 — فایل‌های CKEditor


def is_empty_html(value):
    """بررسی می‌کند آیا محتوای HTML خالی است (فقط تگ‌های خالی، فاصله، br)."""
    if not value or not isinstance(value, str):
        return True
    stripped = re.sub(r"<[^>]+>", "", value)
    stripped = stripped.replace("&nbsp;", " ").strip()
    return len(stripped) == 0


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


@admin.register(BlogAuthor)
class BlogAuthorAdmin(ClearCacheAdminMixin, admin.ModelAdmin):
    list_display = ("name", "role", "is_active", "order", "post_count_display", "photo_thumb")
    list_filter = ("is_active",)
    search_fields = ("name", "role", "bio")
    list_editable = ("order", "is_active")
    ordering = ("order", "name")
    readonly_fields = ("photo_preview",)
    fieldsets = (
        (None, {"fields": ("name", "role", "bio", "photo", "photo_preview", "is_active", "order")}),
    )

    def photo_thumb(self, obj):
        if obj and obj.photo:
            return format_html(
                '<img src="{}" alt="" style="width:36px;height:36px;border-radius:50%;object-fit:cover;">',
                obj.photo.url,
            )
        return "—"

    photo_thumb.short_description = "عکس"

    def photo_preview(self, obj):
        if obj and obj.photo:
            return format_html(
                '<img src="{}" alt="" style="max-width:120px;border-radius:12px;">',
                obj.photo.url,
            )
        return "آواتار پیش‌فرض نمایش داده می‌شود."

    photo_preview.short_description = "پیش‌نمایش عکس"

    def post_count_display(self, obj):
        return obj.posts.count() if obj else 0

    post_count_display.short_description = "تعداد مطالب"

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == "bio":
            kwargs["widget"] = forms.Textarea(attrs={"rows": 3})
        return super().formfield_for_dbfield(db_field, request, **kwargs)


@admin.register(BlogPost)
class BlogPostAdmin(ClearCacheAdminMixin, admin.ModelAdmin):
    prepopulated_fields = {"slug": ("title",)}
    save_on_top = True
    autocomplete_fields = ("author",)
    list_display = ("title", "author", "country_tag", "is_published", "created_at_both_display")
    list_filter = ("is_published", "country_tag", "author")
    search_fields = ("title", "excerpt", "content", "author__name")
    fieldsets = (
        ("اطلاعات اصلی", {"fields": ("title", "slug", "author", "country_tag", "is_published")}),
        ("محتوا", {"fields": ("excerpt", "content", "image")}),
        ("تنظیمات SEO", {"fields": ("meta_title", "meta_description", "meta_keywords", "canonical_url")}),
    )

    def created_at_both_display(self, obj):
        return format_datetime_both(obj.created_at) if obj else "-"

    created_at_both_display.short_description = "تاریخ انتشار"

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == "content":
            kwargs["widget"] = rich_text_widget(request)
        return super().formfield_for_dbfield(db_field, request, **kwargs)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "author":
            kwargs["queryset"] = BlogAuthor.objects.filter(is_active=True).order_by("order", "name")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class FAQInline(admin.TabularInline):
    model = FAQ
    extra = 0
    fields = ("question", "order", "is_featured", "is_active")
    show_change_link = True
    verbose_name = "سوال"
    verbose_name_plural = "سوالات این دسته"


@admin.register(FAQCategory)
class FAQCategoryAdmin(ClearCacheAdminMixin, admin.ModelAdmin):
    list_display = ("name", "slug", "order", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "description")
    list_editable = ("order", "is_active")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [FAQInline]
    save_on_top = True
    fieldsets = (
        (
            "اطلاعات دسته",
            {"fields": ("name", "slug", "description", "icon")},
        ),
        ("نمایش", {"fields": ("order", "is_active")}),
        ("سئو", {"fields": ("meta_title", "meta_description"), "classes": ("collapse",)}),
    )


class FAQAdminForm(forms.ModelForm):
    class Meta:
        model = FAQ
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["detail_content"].required = False

    def clean_detail_content(self):
        value = self.cleaned_data.get("detail_content")
        return "" if is_empty_html(value) else (value or "")


@admin.register(FAQ)
class FAQAdmin(ClearCacheAdminMixin, admin.ModelAdmin):
    form = FAQAdminForm
    list_display = ("question", "category", "order", "is_featured", "is_active", "view_count")
    list_filter = ("is_featured", "is_active", "category")
    search_fields = ("question", "answer", "detail_content", "search_keywords")
    list_editable = ("order", "is_featured", "is_active")
    autocomplete_fields = ("category",)
    prepopulated_fields = {"slug": ("question",)}
    save_on_top = True
    fieldsets = (
        (
            "سوال و پاسخ",
            {
                "fields": (
                    "category",
                    "question",
                    "answer",
                    "detail_content",
                ),
            },
        ),
        (
            "نمایش و آدرس",
            {"fields": ("slug", "order", "is_active", "is_featured", "view_count")},
        ),
        ("سئو صفحه سوال", {"fields": ("meta_title", "meta_description"), "classes": ("collapse",)}),
        ("جستجو هوشمند", {"fields": ("search_keywords",), "classes": ("collapse",)}),
    )
    readonly_fields = ("view_count",)

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name in ("answer", "detail_content"):
            kwargs["widget"] = rich_text_widget(request)
        return super().formfield_for_dbfield(db_field, request, **kwargs)


@admin.register(MonthlyAchievement)
class MonthlyAchievementAdmin(ClearCacheAdminMixin, admin.ModelAdmin):
    prepopulated_fields = {"slug": ("title",)}
    list_display = (
        "person_name",
        "title",
        "slug",
        "month_label",
        "is_featured",
        "order",
        "is_active",
        "view_count",
        "has_video_display",
    )
    list_filter = ("is_active", "is_featured", "month_label")
    search_fields = (
        "person_name",
        "title",
        "description",
        "detail_content",
        "person_role",
        "month_label",
        "search_keywords",
        "slug",
    )
    list_editable = ("order", "is_featured", "is_active")
    readonly_fields = ("created_at", "view_count", "image_preview")
    save_on_top = True
    fieldsets = (
        (
            "شخص و دوره",
            {"fields": ("person_name", "person_role", "month_label")},
        ),
        (
            "محتوا",
            {
                "fields": (
                    "title",
                    "slug",
                    "description",
                    "detail_content",
                    "search_keywords",
                ),
            },
        ),
        (
            "رسانه",
            {"fields": ("image", "image_preview", "video_file", "video_url")},
        ),
        (
            "نمایش",
            {"fields": ("order", "is_featured", "is_active", "view_count")},
        ),
        ("سئو", {"fields": ("meta_title", "meta_description"), "classes": ("collapse",)}),
        (
            "سیستم",
            {"classes": ("collapse",), "fields": ("created_at",)},
        ),
    )

    @admin.display(boolean=True, description="ویدیو")
    def has_video_display(self, obj):
        return obj.has_video()

    @admin.display(description="پیش‌نمایش")
    def image_preview(self, obj):
        if obj and obj.image:
            from django.utils.html import format_html

            return format_html('<img src="{}" style="max-height:120px;border-radius:8px;">', obj.image.url)
        return "—"


@admin.register(ServiceCategory)
class ServiceCategoryAdmin(ClearCacheAdminMixin, admin.ModelAdmin):
    list_display = ("name", "slug", "order", "is_active")
    list_editable = ("order", "is_active")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name", "slug")
    save_on_top = True
    fieldsets = (
        ("اطلاعات دسته", {"fields": ("name", "slug", "icon", "description")}),
        ("نمایش", {"fields": ("order", "is_active")}),
        ("سئو", {"fields": ("meta_title", "meta_description"), "classes": ("collapse",)}),
    )


@admin.register(Service)
class ServiceAdmin(ClearCacheAdminMixin, admin.ModelAdmin):
    list_display = ("title", "category", "order", "is_featured", "is_active")
    list_editable = ("order", "is_featured", "is_active")
    list_filter = ("category", "is_active", "is_featured")
    search_fields = ("title", "description", "short_description", "search_keywords")
    prepopulated_fields = {"slug": ("title",)}
    autocomplete_fields = ("category",)
    save_on_top = True
    fieldsets = (
        (
            "اطلاعات اصلی",
            {"fields": ("title", "slug", "category", "icon")},
        ),
        ("توضیحات", {"fields": ("short_description", "description", "highlights")}),
        ("نمایش", {"fields": ("order", "is_featured", "is_active")}),
        ("جستجو", {"fields": ("search_keywords",), "classes": ("collapse",)}),
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


class CourseInstructorResumeInline(admin.TabularInline):
    model = CourseInstructorResumeEntry
    extra = 1
    ordering = ("order",)
    fields = ("period", "role_title", "organization", "description", "order")


class CourseInstructorAdminForm(forms.ModelForm):
    class Meta:
        model = CourseInstructor
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["bio"].required = False

    def clean_bio(self):
        value = self.cleaned_data.get("bio")
        return "" if is_empty_html(value) else (value or "")


@admin.register(CourseInstructor)
class CourseInstructorAdmin(ClearCacheAdminMixin, admin.ModelAdmin):
    form = CourseInstructorAdminForm
    list_display = ("name", "slug", "position", "order", "is_active")
    list_editable = ("order", "is_active")
    search_fields = ("name", "position", "slug")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [CourseInstructorResumeInline]
    save_on_top = True
    fieldsets = (
        ("اطلاعات اصلی", {"fields": ("name", "slug", "position", "title", "image")}),
        ("معرفی", {"fields": ("short_bio", "bio", "specialties", "highlights")}),
        (
            "تماس و شبکه‌ها",
            {
                "fields": (
                    "phone",
                    "email",
                    "telegram",
                    "whatsapp",
                    "instagram",
                    "linkedin",
                    "website",
                ),
                "classes": ("collapse",),
            },
        ),
        ("سئو", {"fields": ("meta_title", "meta_description", "search_keywords"), "classes": ("collapse",)}),
        ("نمایش", {"fields": ("order", "is_active")}),
    )

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == "bio":
            kwargs["widget"] = rich_text_widget(request)
            kwargs["required"] = False
        return super().formfield_for_dbfield(db_field, request, **kwargs)


class MajorFAQInline(admin.TabularInline):
    model = MajorFAQ
    extra = 1
    ordering = ("order",)


class MajorUniversityLinkInline(admin.TabularInline):
    model = UniversityMajorLink
    fk_name = "major"
    extra = 0
    ordering = ("order",)
    autocomplete_fields = ("university",)
    fields = ("university", "is_featured", "order")

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "university" and request.resolver_match:
            obj_id = request.resolver_match.kwargs.get("object_id")
            if obj_id:
                try:
                    major = Major.objects.only("country").get(pk=obj_id)
                    kwargs["queryset"] = kwargs.get("queryset", db_field.remote_field.model.objects.all()).filter(
                        country=major.country,
                    )
                except Major.DoesNotExist:
                    pass
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(Major)
class MajorAdmin(ClearCacheAdminMixin, admin.ModelAdmin):
    form = MajorAdminForm
    list_display = ("title", "slug", "country", "order", "is_active")
    list_filter = ("country",)
    list_editable = ("order", "is_active")
    search_fields = ("title",)
    prepopulated_fields = {"slug": ("title",)}
    inlines = [MajorFAQInline, MajorUniversityLinkInline]
    save_on_top = True
    fieldsets = (
        (
            "اطلاعات اصلی",
            {"fields": ("title", "slug", "country", "short_description")},
        ),
        ("محتوا", {"fields": ("description", "image")}),
        ("سئو", {"fields": ("meta_title", "meta_description"), "classes": ("collapse",)}),
        ("نمایش", {"fields": ("order", "is_active")}),
    )

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == "description":
            kwargs["widget"] = rich_text_widget(request)
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

    def clean_external_url(self):
        return (self.cleaned_data.get("external_url") or "").strip()

    def clean(self):
        cleaned = super().clean()
        external = cleaned.get("external_url") or ""
        if external and not external.startswith(("http://", "https://")):
            from django.core.exceptions import ValidationError

            raise ValidationError(
                {"external_url": "آدرس باید با http:// یا https:// شروع شود."}
            )
        return cleaned


class PricingTariffInline(admin.TabularInline):
    model = PricingTariff
    extra = 0
    fields = (
        "title",
        "calculator_key",
        "allowance_percent",
        "price_foreign_amount",
        "price_foreign_currency",
        "price_type",
        "order",
        "is_active",
    )
    show_change_link = True


@admin.register(PricingCategory)
class PricingCategoryAdmin(ClearCacheAdminMixin, admin.ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    list_display = ("name", "order", "is_active")
    list_editable = ("order", "is_active")
    search_fields = ("name", "slug")
    inlines = [PricingTariffInline]
    save_on_top = True
    fieldsets = (
        ("اطلاعات دسته", {"fields": ("name", "slug", "icon", "description")}),
        ("نمایش", {"fields": ("order", "is_active")}),
    )


@admin.register(PricingTariff)
class PricingTariffAdmin(ClearCacheAdminMixin, admin.ModelAdmin):
    list_display = (
        "title",
        "category",
        "allowance_percent",
        "price_foreign_amount",
        "price_foreign_currency",
        "price_type",
        "calculator_key",
        "order",
        "is_active",
    )
    list_filter = ("category", "price_type", "is_active")
    list_editable = ("order", "is_active")
    search_fields = ("title", "calculator_key")
    prepopulated_fields = {"slug": ("title",)}
    save_on_top = True
    autocomplete_fields = ("category",)
    fieldsets = (
        (
            "اطلاعات اصلی",
            {"fields": ("category", "title", "slug", "icon")},
        ),
        ("محتوا", {"fields": ("short_description", "description")}),
        (
            "قیمت",
            {
                "fields": (
                    "price_foreign_amount",
                    "price_foreign_currency",
                    "price_toman",
                    "price_type",
                    "allowance_percent",
                ),
            },
        ),
        (
            "ماشین‌حساب",
            {
                "fields": (
                    "calculator_key",
                    "is_calculator_option",
                    "is_core",
                    "auto_for_goals",
                    "depends_on_keys",
                ),
            },
        ),
        ("نمایش", {"fields": ("order", "is_active")}),
    )


STUDY_COUNTRY_RICH_FIELDS = (
    "description",
    "visa_info",
    "admission_info",
    "living_info",
    "scholarship_info",
)


class StudyCountryAdminForm(forms.ModelForm):
    class Meta:
        model = StudyCountry
        fields = "__all__"


class CountryScholarshipInline(admin.TabularInline):
    model = CountryScholarship
    extra = 0
    fields = (
        "name",
        "slug",
        "provider",
        "coverage",
        "is_featured",
        "order",
        "is_active",
    )
    prepopulated_fields = {"slug": ("name",)}


@admin.register(CountryScholarshipGuide)
class CountryScholarshipGuideAdmin(ClearCacheAdminMixin, admin.ModelAdmin):
    list_display = ("country", "target_degree", "headline", "is_active", "updated_at")
    list_filter = ("is_active", "target_degree", "country")
    search_fields = ("headline", "intro", "country__name", "country__code")
    autocomplete_fields = ("country",)
    inlines = (CountryScholarshipInline,)
    save_on_top = True
    fieldsets = (
        ("کشور و مقطع", {"fields": ("country", "target_degree", "is_active")}),
        ("محتوا", {"fields": ("headline", "intro", "overview", "application_guide")}),
        (
            "سئو و جستجو",
            {
                "classes": ("collapse",),
                "fields": ("search_keywords", "meta_title", "meta_description", "meta_keywords"),
            },
        ),
    )

    def get_form(self, request, obj=None, **kwargs):
        form_class = super().get_form(request, obj, **kwargs)
        rich_fields = ("overview", "application_guide")

        class GuideFormWithRichText(form_class):
            def __init__(self, *args, **form_kwargs):
                super().__init__(*args, **form_kwargs)
                for field_name in rich_fields:
                    if field_name in self.fields:
                        self.fields[field_name].widget = rich_text_widget(request)

        return GuideFormWithRichText


@admin.register(CountryScholarship)
class CountryScholarshipAdmin(ClearCacheAdminMixin, admin.ModelAdmin):
    list_display = ("name", "guide", "provider", "is_featured", "order", "is_active")
    list_filter = ("is_active", "is_featured", "guide__country")
    search_fields = ("name", "provider", "slug", "program_key")
    autocomplete_fields = ("guide",)
    prepopulated_fields = {"slug": ("name",)}
    save_on_top = True

    def get_form(self, request, obj=None, **kwargs):
        form_class = super().get_form(request, obj, **kwargs)

        class ScholarshipFormWithRichText(form_class):
            def __init__(self, *args, **form_kwargs):
                super().__init__(*args, **form_kwargs)
                if "eligibility" in self.fields:
                    self.fields["eligibility"].widget = rich_text_widget(request)

        return ScholarshipFormWithRichText


@admin.register(StudyCountry)
class StudyCountryAdmin(ClearCacheAdminMixin, admin.ModelAdmin):
    form = StudyCountryAdminForm

    def get_form(self, request, obj=None, **kwargs):
        form_class = super().get_form(request, obj, **kwargs)

        class StudyCountryFormWithRichText(form_class):
            def __init__(self, *args, **form_kwargs):
                super().__init__(*args, **form_kwargs)
                for field_name in STUDY_COUNTRY_RICH_FIELDS:
                    if field_name in self.fields:
                        self.fields[field_name].widget = rich_text_widget(request)

        return StudyCountryFormWithRichText
    list_display = ("name", "code", "order", "is_active")
    list_editable = ("order", "is_active")
    search_fields = ("name", "code", "intro", "search_keywords")
    save_on_top = True
    autocomplete_fields = ("allowance_country",)
    fieldsets = (
        (
            "شناسه و معرفی",
            {"fields": ("name", "code", "headline", "intro", "image")},
        ),
        (
            "تعرفه در صفحه خدمات",
            {
                "fields": (
                    "allowance_country",
                    "consultation_foreign_amount",
                    "consultation_foreign_currency",
                ),
                "description": "مبلغ هر جلسه مشاوره و ردیف مقرری برای محاسبه تعرفه در صفحه تعرفه خدمات.",
            },
        ),
        ("محتوای کامل", {"fields": ("description",)}),
        (
            "راهنماهای مهاجرت",
            {"fields": ("visa_info", "admission_info", "living_info", "scholarship_info")},
        ),
        ("مزایا و معایب", {"fields": ("pros", "cons")}),
        ("نمایش", {"fields": ("order", "is_active")}),
        (
            "جستجو و سئو",
            {
                "classes": ("collapse",),
                "fields": ("search_keywords", "meta_title", "meta_description", "meta_keywords"),
            },
        ),
    )


@admin.register(LivingAllowanceCountry)
class LivingAllowanceCountryAdmin(ClearCacheAdminMixin, admin.ModelAdmin):
    list_display = ("name", "amount", "currency", "region_group", "order", "is_active")
    list_filter = ("currency", "region_group", "is_active")
    list_editable = ("order", "is_active")
    search_fields = ("name", "search_keywords")
    prepopulated_fields = {"slug": ("name",)}
    save_on_top = True
    fieldsets = (
        (
            "کشور / منطقه",
            {"fields": ("name", "slug", "region_group")},
        ),
        (
            "مقرری بانکی",
            {"fields": ("amount", "currency")},
        ),
        ("نمایش", {"fields": ("order", "is_active")}),
        (
            "جستجو",
            {"classes": ("collapse",), "fields": ("search_keywords",)},
        ),
    )


@admin.register(Course)
class CourseAdmin(ClearCacheAdminMixin, admin.ModelAdmin):
    form = CourseAdminForm
    list_display = ("title", "link_destination_display", "country", "duration_hours", "delivery_mode", "order", "is_active")
    list_filter = ("country", "delivery_mode")
    list_editable = ("order", "is_active")
    search_fields = ("title", "external_url")
    inlines = [CourseSyllabusInline, CourseFAQInline]
    save_on_top = True
    fieldsets = (
        (
            "اطلاعات اصلی",
            {"fields": ("title", "slug", "country", "instructor", "short_description")},
        ),
        (
            "لینک مقصد",
            {
                "description": (
                    "اگر «لینک خارجی» پر شود، کلیک روی دوره در سایت مستقیم به آن آدرس می‌رود "
                    "و صفحه جزئیات داخلی نمایش داده نمی‌شود. برای دوره‌های روی همین سایت خالی بگذارید."
                ),
                "fields": ("external_url", "external_link_label"),
            },
        ),
        (
            "محتوای دوره",
            {"fields": ("description", "objectives", "conditions", "features")},
        ),
        (
            "جزئیات اجرایی",
            {
                "fields": (
                    "duration_hours",
                    "price",
                    "phone",
                    "delivery_mode",
                    "sample_video",
                    "image",
                ),
            },
        ),
        ("سئو", {"fields": ("meta_title", "meta_description"), "classes": ("collapse",)}),
        ("نمایش", {"fields": ("order", "is_active")}),
    )

    @admin.display(description="مقصد لینک")
    def link_destination_display(self, obj):
        if obj and obj.uses_external_link():
            return "خارجی"
        return "صفحه داخلی"

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name in ("description", "objectives", "conditions"):
            kwargs["widget"] = rich_text_widget(request)
            kwargs["required"] = False
        return super().formfield_for_dbfield(db_field, request, **kwargs)
