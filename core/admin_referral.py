"""نمایش و فیلتر منبع آشنایی در پنل ادمین."""

from django.contrib import admin
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import render
from django.utils.html import format_html

from core.referral_stats import referral_stats_from_request


def user_can_view_referral_stats(user) -> bool:
    if not user.is_active or not user.is_staff:
        return False
    if user.is_superuser:
        return True
    return user.has_perm("core.view_evaluationrequest") or user.has_perm(
        "core.view_consultationrequest"
    )


def referral_stats_admin_view(request):
    """صفحه آمار «از کجا با ما آشنا شدید؟»."""
    stats = referral_stats_from_request(request)
    context = {
        **admin.site.each_context(request),
        "title": "آمار منبع آشنایی",
        "stats": stats,
        "filter_from": request.GET.get("from", ""),
        "filter_to": request.GET.get("to", ""),
    }
    return render(request, "admin/referral_stats.html", context)


referral_stats_admin_view = user_passes_test(user_can_view_referral_stats)(
    referral_stats_admin_view
)


class ReferralSourceAdminMixin:
    """ستون لیست، خلاصهٔ خوانا در فرم، و فیلتر شبکه اجتماعی."""

    referral_admin_readonly = ("referral_summary_admin",)

    @admin.display(description="از کجا آشنا شد")
    def referral_display_column(self, obj):
        return obj.referral_display if obj else "—"

    @admin.display(description="خلاصه منبع آشنایی")
    def referral_summary_admin(self, obj):
        if not obj or not obj.referral_source:
            return format_html('<span style="color:#888">ثبت نشده</span>')
        return format_html("<strong>{}</strong>", obj.referral_display)

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        for name in self.referral_admin_readonly:
            if name not in readonly:
                readonly.append(name)
        return readonly
