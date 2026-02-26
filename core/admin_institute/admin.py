from django.contrib import admin

from core.models import Institute, TeamMember


@admin.register(Institute)
class InstituteAdmin(admin.ModelAdmin):
    list_display = ("name", "city", "phone", "students_sent", "countries_count")
    fieldsets = (
        ("اطلاعات اصلی", {"fields": ("name", "province", "city", "type_title")}),
        ("تماس", {"fields": ("phone", "email", "address", "website")}),
        ("مجوز", {"fields": ("license_issue_date", "license_expiry_date")}),
        ("آمار", {"fields": ("students_sent", "countries_count")}),
    )

    def has_add_permission(self, request):
        return not Institute.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(TeamMember)
class TeamMemberAdmin(admin.ModelAdmin):
    list_display = ("name", "position", "order", "is_active")
    list_editable = ("order", "is_active")
    search_fields = ("name", "position", "title")
    fieldsets = (
        ("اطلاعات اصلی", {"fields": ("name", "position", "image", "title")}),
        ("تماس", {"fields": ("phone", "email")}),
        ("معرفی", {"fields": ("description",)}),
        ("شبکه‌های اجتماعی", {"fields": ("telegram", "whatsapp", "instagram", "linkedin", "website"), "classes": ("collapse",)}),
        ("تنظیمات", {"fields": ("order", "is_active")}),
    )
