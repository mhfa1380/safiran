"""
AdminSite سفارشی برای دسته‌بندی ادمین و نمایش badge تعداد پیام‌های جدید.
"""
from django.contrib import admin


# نگاشت مدل‌ها به دسته‌های ادمین؛ ترتیب بر اساس اولویت و کاربرد روزانه
ADMIN_APP_GROUPS = [
    ("admin_requests", "درخواست‌ها و تماس", ["consultationrequest", "consultationslot", "evaluationrequest", "contactmessage"]),
    ("admin_universities", "دانشگاه‌ها", ["university", "universitygalleryimage"]),
    ("admin_content", "محتوا و صفحات", ["blogpost", "faq", "service", "major", "course", "coursesyllabus"]),
    ("admin_institute", "موسسه و تیم", ["institute", "teammember"]),
]


def _get_requests_pending_count():
    """تعداد موارد مشاهده‌نشده در بخش درخواست‌ها."""
    from core.models import (
        ConsultationRequest,
        ContactMessage,
        EvaluationRequest,
    )

    count = 0
    count += ContactMessage.objects.filter(admin_seen_at__isnull=True).count()
    count += ConsultationRequest.objects.filter(admin_seen_at__isnull=True).count()
    count += EvaluationRequest.objects.filter(admin_seen_at__isnull=True).count()
    return count


class SafiranAdminSite(admin.AdminSite):
    """ادمین سایت با دسته‌بندی و badge پیام جدید."""

    def get_app_list(self, request, app_label=None):
        app_list = super().get_app_list(request, app_label)
        result = []

        for app in app_list:
            if app["app_label"] != "core":
                result.append(app)
                continue

            models_by_name = {m["object_name"].lower(): m for m in app["models"]}
            pending_count = _get_requests_pending_count()

            for group_key, group_name, model_names in ADMIN_APP_GROUPS:
                group_models = [
                    models_by_name[mn]
                    for mn in model_names
                    if mn in models_by_name
                ]
                if not group_models:
                    continue

                first_model_url = group_models[0].get("admin_url") or app["app_url"]
                virtual_app = {
                    "app_label": group_key,
                    "app_url": first_model_url,
                    "has_module_perms": app["has_module_perms"],
                    "models": group_models,
                    "name": group_name,
                }
                if group_key == "admin_requests":
                    virtual_app["pending_count"] = pending_count
                result.append(virtual_app)

        return result


admin_site = SafiranAdminSite(name="admin")
