"""
نقش‌های از پیش‌تعریف‌شده کارمندان پنل ادمین (بر اساس گروه Django).

هر گروه فقط به بخش‌های مشخص دسترسی دارد. سوپرکاربر همه بخش‌ها را می‌بیند.
"""
from __future__ import annotations

from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

# نام گروه = برچسب فارسی در ادمین
ADMIN_STAFF_ROLES: dict[str, dict] = {
    "کارمند — مشاوره و تماس": {
        "description": "درخواست مشاوره، پیام تماس، زمان‌های رزرو",
        "models": ("consultationrequest", "contactmessage", "consultationslot"),
        "permissions": ("view", "change"),
    },
    "کارمند — کال‌سنتر و ارزیابی": {
        "description": "پرونده ارزیابی، تماس‌های پیگیری، اشتراک گزارش",
        "models": (
            "evaluationrequest",
            "evaluationcontactlog",
            "evaluationreportshare",
        ),
        "permissions": ("view", "add", "change"),
    },
    "کارمند — محتوا و صفحات": {
        "description": "وبلاگ، FAQ، دستاوردها، کشورها، خدمات، رشته، دوره، تعرفه، فایل CKEditor",
        "models": (
            "blogpost",
            "ckeditorasset",
            "monthlyachievement",
            "faqcategory",
            "faq",
            "studycountry",
            "livingallowancecountry",
            "servicecategory",
            "service",
            "major",
            "course",
            "pricingcategory",
            "pricingtariff",
        ),
        "permissions": ("view", "add", "change", "delete"),
    },
    "کارمند — دانشگاه‌ها": {
        "description": "مدیریت دانشگاه‌ها و گالری",
        "models": ("university", "universitygalleryimage", "universityfaq"),
        "permissions": ("view", "add", "change", "delete"),
    },
    "کارمند — موسسه و تیم": {
        "description": "اطلاعات موسسه (فقط مشاهده) و اعضای تیم",
        "models": ("institute", "teammember"),
        "permissions": ("view", "change"),
    },
}

# مدل‌هایی که فقط سوپرکاربر باید ببیند (لاگ، کاربران)
SUPERUSER_ONLY_MODELS = frozenset({"adminchangelog"})


def _permissions_for_models(model_names: tuple[str, ...], actions: tuple[str, ...]):
    perms = []
    for model_name in model_names:
        try:
            ct = ContentType.objects.get(app_label="core", model=model_name)
        except ContentType.DoesNotExist:
            continue
        for action in actions:
            codename = f"{action}_{model_name}"
            try:
                perms.append(Permission.objects.get(content_type=ct, codename=codename))
            except Permission.DoesNotExist:
                continue
    return perms


def seed_admin_staff_roles() -> dict[str, int]:
    """
    ایجاد/بروزرسانی گروه‌های نقش کارمند و تخصیص دسترسی‌ها.
    برمی‌گرداند: {نام گروه: تعداد permission}
    """
    result = {}
    for group_name, spec in ADMIN_STAFF_ROLES.items():
        group, created = Group.objects.get_or_create(name=group_name)
        if not created:
            group.permissions.clear()
        perms = _permissions_for_models(spec["models"], spec["permissions"])
        group.permissions.set(perms)
        result[group_name] = len(perms)
    return result


def role_choices_for_help() -> str:
    lines = ["نقش‌های پیشنهادی (در بخش گروه‌ها یا کاربر، گروه را انتخاب کنید):"]
    for name, spec in ADMIN_STAFF_ROLES.items():
        lines.append(f"• {name}: {spec['description']}")
    lines.append("سوپرکاربر: دسترسی کامل به همه بخش‌ها شامل کاربران و لاگ.")
    return "\n".join(lines)
