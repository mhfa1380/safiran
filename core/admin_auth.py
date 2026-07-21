"""مدیریت کاربران و گروه‌های دسترسی کارمندان."""
from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin as DjangoGroupAdmin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.models import Group, User
from django.utils.html import format_html, format_html_join

from core.admin_export import SafiranExportMixin
from core.admin_roles import ADMIN_STAFF_ROLES


class SafiranUserAdmin(SafiranExportMixin, DjangoUserAdmin):
    """کاربران پنل — کارمند با انتخاب گروه به بخش‌های محدود دسترسی دارد."""

    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "is_staff",
        "is_superuser",
        "groups_display",
        "is_active",
    )
    list_filter = ("is_staff", "is_superuser", "is_active", "groups")
    search_fields = ("username", "first_name", "last_name", "email")
    filter_horizontal = ("groups", "user_permissions")
    ordering = ("-is_staff", "username")

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("اطلاعات شخصی", {"fields": ("first_name", "last_name", "email")}),
        (
            "دسترسی پنل",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
                "description": (
                    "برای کارمند: «وضعیت کارمند» را فعال کنید و یک یا چند "
                    "<strong>گروه نقش</strong> انتخاب کنید (مثلاً «کارمند — مشاوره و تماس»). "
                    "سوپرکاربر به همه بخش‌ها از جمله کاربران و لاگ دسترسی دارد."
                ),
            },
        ),
        ("تاریخ‌ها", {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "username",
                    "password1",
                    "password2",
                    "is_staff",
                    "groups",
                ),
            },
        ),
    )

    @admin.display(description="گروه‌های نقش")
    def groups_display(self, obj):
        names = list(obj.groups.values_list("name", flat=True)[:4])
        if not names:
            return "—"
        text = "، ".join(names)
        if obj.groups.count() > 4:
            text += " …"
        return text


class SafiranGroupAdmin(SafiranExportMixin, DjangoGroupAdmin):
    """گروه‌های دسترسی — نقش‌های از پیش‌تعریف‌شده."""

    search_fields = ("name",)

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        items = format_html_join(
            "",
            "<li><strong>{}</strong> — {}</li>",
            [(name, spec["description"]) for name, spec in ADMIN_STAFF_ROLES.items()],
        )
        extra_context["role_help_html"] = format_html(
            '<div class="help" style="margin:0 0 1rem;padding:.75rem 1rem;'
            "background:#f0f4fa;border-radius:8px;\">"
            "<p style=\"margin:0 0 .5rem;\"><strong>نقش‌های کارمند:</strong></p>"
            "<ul style=\"margin:0;padding-right:1.2rem;\">{}</ul>"
            "<p style=\"margin:.75rem 0 0;font-size:.85rem;color:#555;\">"
            "برای همگام‌سازی دسترسی‌ها: "
            "<code>python manage.py seed_admin_roles</code>"
            "</p></div>",
            items,
        )
        return super().changelist_view(request, extra_context=extra_context)


def register_auth_admin(site: admin.AdminSite) -> None:
    """ثبت User/Group سفارشی روی AdminSite."""
    for model in (User, Group):
        if model in site._registry:
            site.unregister(model)
    site.register(User, SafiranUserAdmin)
    site.register(Group, SafiranGroupAdmin)
