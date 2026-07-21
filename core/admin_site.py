"""

AdminSite سفارشی برای دسته‌بندی ادمین و نمایش badge تعداد پیام‌های جدید.

"""

from django.conf import settings
from django.contrib import admin
from django.core.cache import cache
from django.urls import path

from core.admin_login import SafiranAdminLoginForm





# نام فارسی اپ احراز هویت

AUTH_APP_LABEL = "auth"

AUTH_APP_NAME = "بررسی اصالت و اجازه‌ها"

# ترتیب مدل‌های auth در منو

AUTH_MODEL_ORDER = ("user", "group")



# ترتیب گروه‌های core در منوی ادمین (بالا = پرکاربردتر)

ADMIN_APP_GROUPS = [

    (

        "admin_audit",

        "لاگ و بازگردانی",

        ["adminchangelog"],

    ),

    (

        "admin_callcenter",

        "کال‌سنتر و ارزیابی",

        [

            "evaluationrequest",

            "evaluationcontactlog",

        ],

    ),

    (

        "admin_requests",

        "مشاوره و تماس",

        [

            "consultationrequest",

            "contactmessage",

            "consultationslot",

        ],

    ),

    (

        "admin_universities",

        "دانشگاه‌ها",

        ["university"],

    ),

    (

        "admin_content",

        "محتوا و صفحات",

        [

            # وبلاگ و موفقیت‌ها

            "blogauthor",

            "blogpost",

            "ckeditorasset",

            "monthlyachievement",

            # سوالات متداول

            "faqcategory",

            "faq",

            # کشورها و راهنما

            "studycountry",

            "livingallowancecountry",

            # خدمات

            "servicecategory",

            "service",

            # آموزش

            "major",

            "course",

            # تعرفه

            "pricingcategory",

            "pricingtariff",

        ],

    ),

    (

        "admin_institute",

        "موسسه و تیم",

        ["institute", "teammember"],

    ),

]



# گروه‌هایی که badge «جدید» روی عنوان می‌گیرند

_PENDING_BADGE_GROUPS = frozenset({"admin_callcenter", "admin_requests"})


def _admin_cache_seconds() -> int:
    return int(getattr(settings, "ADMIN_STATS_CACHE_SECONDS", 30))


def invalidate_admin_menu_cache() -> None:
    """پس از مشاهدهٔ لیست‌ها، شمارندهٔ badge منو را تازه می‌کند."""
    cache.delete_many(
        [
            "admin:callcenter_pending",
            "admin:requests_pending",
            "admin:quick_stats",
        ]
    )


def _get_callcenter_pending_count() -> int:
    """تعداد پرونده‌های ارزیابی که هنوز در لیست ادمین «مشاهده» نشده‌اند."""
    cache_key = "admin:callcenter_pending"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    from core.models import EvaluationRequest

    count = EvaluationRequest.objects.filter(admin_seen_at__isnull=True).count()
    cache.set(cache_key, count, _admin_cache_seconds())
    return count





def _get_requests_pending_count() -> int:
    """تعداد موارد مشاهده‌نشده در مشاوره و تماس."""
    cache_key = "admin:requests_pending"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    from core.models import ConsultationRequest, ContactMessage

    count = ContactMessage.objects.filter(admin_seen_at__isnull=True).count()
    count += ConsultationRequest.objects.filter(admin_seen_at__isnull=True).count()
    cache.set(cache_key, count, _admin_cache_seconds())
    return count





def _get_admin_quick_stats():
    """لینک‌های سریع داشبورد ادمین."""
    cache_key = "admin:quick_stats"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    from django.urls import reverse
    from django.utils import timezone

    from core.models import (
        ConsultationRequest,
        ContactMessage,
        EvaluationContactLog,
        EvaluationRequest,
    )

    now = timezone.now()

    eval_due = EvaluationRequest.objects.filter(

        follow_up_required=True,

        next_follow_up_at__lte=now,

    ).exclude(status__in=[EvaluationRequest.STATUS_COMPLETED, EvaluationRequest.STATUS_LOST]).count()



    stats = {
        "logs_today": EvaluationContactLog.objects.filter(
            created_at__date=now.date()
        ).count(),
        "eval_new": EvaluationRequest.objects.filter(
            status=EvaluationRequest.STATUS_NEW
        ).count(),
        "eval_follow_up_due": eval_due,
        "consultation_new": ConsultationRequest.objects.filter(
            admin_seen_at__isnull=True
        ).count(),
        "contact_new": ContactMessage.objects.filter(admin_seen_at__isnull=True).count(),
        "urls": {
            "evaluation_logs": reverse("admin:core_evaluationcontactlog_changelist"),
            "evaluation_requests": reverse("admin:core_evaluationrequest_changelist"),
            "consultations": reverse("admin:core_consultationrequest_changelist"),
            "contact_messages": reverse("admin:core_contactmessage_changelist"),
            "referral_stats": reverse("admin:referral_stats"),
        },
    }
    cache.set(cache_key, stats, _admin_cache_seconds())
    return stats





def _sort_auth_models(models: list) -> list:

    """مرتب‌سازی کاربران و گروه‌ها."""

    by_name = {m["object_name"].lower(): m for m in models}

    ordered = [by_name[n] for n in AUTH_MODEL_ORDER if n in by_name]

    ordered.extend(m for name, m in by_name.items() if name not in AUTH_MODEL_ORDER)

    return ordered





def _build_core_virtual_apps(app: dict) -> tuple[list, set[str]]:

    """تبدیل اپ core به گروه‌های مجازی منو."""

    models_by_name = {m["object_name"].lower(): m for m in app["models"]}

    result = []

    used_models: set[str] = set()



    for group_key, group_name, model_names in ADMIN_APP_GROUPS:

        group_models = [

            models_by_name[mn]

            for mn in model_names

            if mn in models_by_name

        ]

        if not group_models:

            continue



        for mn in model_names:

            if mn in models_by_name:

                used_models.add(mn)



        first_model_url = group_models[0].get("admin_url") or app["app_url"]

        virtual_app = {

            "app_label": group_key,

            "app_url": first_model_url,

            "has_module_perms": app["has_module_perms"],

            "models": group_models,

            "name": group_name,

            "is_priority": group_key == "admin_callcenter",

        }

        if group_key in _PENDING_BADGE_GROUPS:

            if group_key == "admin_callcenter":

                virtual_app["pending_count"] = _get_callcenter_pending_count()

                virtual_app["pending_badge_title"] = (
                    "پروندهٔ ارزیابی که هنوز لیست درخواست‌ها را باز نکرده‌اید"
                )

            else:

                virtual_app["pending_count"] = _get_requests_pending_count()

                virtual_app["pending_badge_title"] = (
                    "درخواست مشاوره یا پیام تماس مشاهده‌نشده"
                )

        result.append(virtual_app)



    leftover = [

        m

        for name, m in models_by_name.items()

        if name not in used_models

    ]

    if leftover:

        result.append(

            {

                "app_label": "admin_other",

                "app_url": leftover[0].get("admin_url") or app["app_url"],

                "has_module_perms": app["has_module_perms"],

                "models": leftover,

                "name": "سایر",

            }

        )



    return result, used_models





class SafiranAdminSite(admin.AdminSite):

    """ادمین سایت با دسته‌بندی و badge پیام جدید."""



    index_template = "admin/index.html"

    login_template = "admin/login.html"

    login_form = SafiranAdminLoginForm



    site_header = "داشبورد مدیریت"

    site_title = "سفیران"



    def login(self, request, extra_context=None):

        from core.admin_login import ADMIN_LOGIN_CAPTCHA_KEY

        from core.forms import generate_math_captcha



        extra_context = dict(extra_context or {})



        if request.method != "POST":

            _, _, question, answer = generate_math_captcha()

            request.session[ADMIN_LOGIN_CAPTCHA_KEY] = answer

            extra_context["captcha_question"] = question

        else:

            extra_context.setdefault("captcha_question", "")



        response = super().login(request, extra_context)



        if request.method == "POST" and ADMIN_LOGIN_CAPTCHA_KEY not in request.session:

            _, _, question, answer = generate_math_captcha()

            request.session[ADMIN_LOGIN_CAPTCHA_KEY] = answer

            if hasattr(response, "context_data") and response.context_data is not None:

                response.context_data["captcha_question"] = question



        return response



    def index(self, request, extra_context=None):

        extra_context = extra_context or {}

        try:

            extra_context["admin_quick_stats"] = _get_admin_quick_stats()

        except Exception:

            extra_context["admin_quick_stats"] = None

        return super().index(request, extra_context)

    def get_urls(self):
        from core.admin_referral import referral_stats_admin_view

        custom = [
            path(
                "referral-stats/",
                self.admin_view(referral_stats_admin_view),
                name="referral_stats",
            ),
        ]
        return custom + super().get_urls()

    def get_app_list(self, request, app_label=None):

        app_list = super().get_app_list(request, app_label)

        result = []



        auth_app = None

        core_app = None



        for app in app_list:

            if app["app_label"] == AUTH_APP_LABEL:

                auth_app = dict(app)

                auth_app["name"] = AUTH_APP_NAME

                auth_app["models"] = _sort_auth_models(app["models"])

            elif app["app_label"] == "core":

                core_app = app

            else:

                result.append(app)



        if auth_app and request.user.is_superuser:

            result.append(auth_app)



        if core_app:

            result.extend(_build_core_virtual_apps(core_app)[0])



        return result





admin_site = SafiranAdminSite(name="admin")


