"""
سیگنال‌ها برای فشرده‌سازی خودکار تصاویر و بهینه‌سازی دیتابیس.
"""

import logging

from django.conf import settings
from django.core.cache import cache
from django.db.backends.signals import connection_created
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .bale_notifier import build_admin_link, truncate_text
from .task_queue import _thread, enqueue_bale_text
from .mhfa_live import post_inbox_event
from .cache_utils import invalidate_layout_caches
from .models import (
    BlogPost,
    ConsultationRequest,
    ConsultationSlot,
    ContactMessage,
    Course,
    CourseInstructor,
    EvaluationContactLog,
    EvaluationRequest,
    FAQ,
    FAQCategory,
    Institute,
    Major,
    MonthlyAchievement,
    Service,
    ServiceCategory,
    PricingCategory,
    PricingTariff,
    LivingAllowanceCountry,
    TeamMember,
    CountryScholarship,
    CountryScholarshipGuide,
    StudyCountry,
    University,
)
from .seo_ping import ping_search_engines_sitemap

logger = logging.getLogger(__name__)

_ADMIN_CACHE_KEYS = (
    "admin:callcenter_pending",
    "admin:requests_pending",
    "admin:quick_stats",
)


def _invalidate_admin_stats_cache(**kwargs):
    cache.delete_many(list(_ADMIN_CACHE_KEYS))


@receiver(connection_created)
def setup_sqlite_pragmas(sender, connection, **kwargs):
    """فعال‌سازی WAL و بهینه‌سازی SQLite برای ترافیک بالا و جلوگیری از قفل دیتابیس."""
    from .sqlite_db import configure_sqlite_connection

    configure_sqlite_connection(connection)


@receiver(post_save, sender=ContactMessage)
@receiver(post_save, sender=ConsultationRequest)
@receiver(post_save, sender=EvaluationRequest)
@receiver(post_save, sender=EvaluationContactLog)
def invalidate_admin_cache_on_request_change(sender, **kwargs):
    _invalidate_admin_stats_cache()


def _send_new_record_notification(title: str, lines: list[str], list_path: str, change_path: str) -> None:
    """Send a safe notification to Bale (never raises)."""
    message_lines = [
        f"🔔 {title}",
        *lines,
        "",
        # f"لیست ادمین: {build_admin_link(list_path)}",
        f"جزئیات رکورد: {build_admin_link(change_path)}",
    ]
    enqueue_bale_text("\n".join(message_lines))


def _blog_live_notifications_enabled() -> bool:
    return bool(getattr(settings, "MHFA_NOTIFY_BLOG_SAVES", True))


def _blog_bale_notifications_enabled() -> bool:
    return bool(getattr(settings, "BALE_NOTIFY_BLOG_SAVES", True))


def _format_blog_notification(instance: BlogPost, *, action: str) -> str:
    status = "منتشر شده" if instance.is_published else "پیش‌نویس (غیرفعال)"
    lines = [
        action,
        f"عنوان: {instance.title}",
        f"وضعیت: {status}",
    ]
    if instance.country_tag:
        lines.append(f"برچسب: {instance.country_tag}")
    if "حذف" not in action:
        lines.append(f"صفحه سایت: {instance.get_public_url()}")
    lines.append(f"ویرایش ادمین: {build_admin_link(f'/admin/core/blogpost/{instance.pk}/change/')}")
    return "\n".join(lines)


def _notify_blog_bale(instance: BlogPost, *, action: str) -> None:
    if not _blog_bale_notifications_enabled():
        return
    try:
        enqueue_bale_text(_format_blog_notification(instance, action=action), blog=True)
    except Exception:
        logger.exception("blog bale notify failed pk=%s", instance.pk)


@receiver(post_save, sender=BlogPost)
def notify_blog_post_saved(sender, instance, created, **kwargs):
    """اعلان به بله و پنل MHFA Live هنگام افزودن یا ویرایش پست وبلاگ."""
    if kwargs.get("raw"):
        return

    action_label = "پست جدید وبلاگ" if created else "ویرایش پست وبلاگ"
    bale_action = "📝 پست جدید وبلاگ" if created else "✏️ ویرایش پست وبلاگ"
    _notify_blog_bale(instance, action=bale_action)

    if not _blog_live_notifications_enabled():
        return
    try:
        try:
            author_name = instance.author.name
        except Exception:
            author_name = "ادمین وبلاگ"

        post_inbox_event(
            name=author_name,
            subject="blog",
            message=_format_blog_notification(instance, action=f"رویداد: {action_label}"),
        )
    except Exception:
        logger.exception("notify_blog_post_saved failed pk=%s", instance.pk)


@receiver(post_delete, sender=BlogPost)
def notify_blog_post_deleted(sender, instance, **kwargs):
    """اعلان بله هنگام حذف پست وبلاگ."""
    if kwargs.get("raw"):
        return
    _notify_blog_bale(instance, action="🗑️ حذف پست وبلاگ")


@receiver(post_save, sender=ContactMessage)
def notify_new_contact_message(sender, instance, created, **kwargs):
    if not created:
        return
    post_inbox_event(
        name=instance.full_name,
        email=instance.email,
        subject=instance.subject or "contact",
        message=instance.message,
    )
    _send_new_record_notification(
        title="پیام جدید ارتباط با ما",
        lines=[
            f"نام: {instance.full_name}",
            f"ایمیل: {instance.email}",
            f"موضوع: {truncate_text(instance.subject, 80)}",
        ],
        list_path="/admin/core/contactmessage/",
        change_path=f"/admin/core/contactmessage/{instance.pk}/change/",
    )


@receiver(post_save, sender=ConsultationRequest)
def notify_new_consultation_request(sender, instance, created, **kwargs):
    if not created:
        return
    slot_text = str(instance.slot) if instance.slot else "-"
    post_inbox_event(
        name=instance.full_name,
        email=instance.email or "",
        phone=instance.phone,
        subject="appointment",
        message=(
            f"نوع: {instance.get_consultation_type_display()}\n"
            f"کشور: {instance.get_country_display()}\n"
            f"اسلات: {slot_text}\n"
            f"توضیحات: {instance.description or '-'}"
        ),
    )
    _send_new_record_notification(
        title="رزرو جدید مشاوره",
        lines=[
            f"نام: {instance.full_name}",
            f"تلفن: {instance.phone}",
            f"نوع مشاوره: {instance.get_consultation_type_display()}",
            f"کشور: {instance.get_country_display()}",
            f"اسلات: {slot_text}",
        ],
        list_path="/admin/core/consultationrequest/",
        change_path=f"/admin/core/consultationrequest/{instance.pk}/change/",
    )


@receiver(post_save, sender=EvaluationRequest)
def persist_evaluation_snapshot(sender, instance, created, **kwargs):
    """ذخیره پیشنهاد هوشمند بلافاصله پس از ثبت (قبل از اعلان)."""
    if not created or instance.recommendation_snapshot:
        return
    try:
        from core.evaluation_pipeline import skip_sync_evaluation_snapshot

        if skip_sync_evaluation_snapshot():
            return
    except Exception:
        pass
    try:
        from core.evaluation_engine import build_evaluation_report

        EvaluationRequest.objects.filter(pk=instance.pk).update(
            recommendation_snapshot=build_evaluation_report(instance)
        )
        instance.recommendation_snapshot = EvaluationRequest.objects.filter(pk=instance.pk).values_list(
            "recommendation_snapshot", flat=True
        ).first()
    except Exception:
        logger.exception("persist_evaluation_snapshot failed pk=%s", instance.pk)


_SITEMAP_CONTENT_MODELS = (
    BlogPost,
    University,
    Course,
    CourseInstructor,
    Major,
    FAQ,
    FAQCategory,
    MonthlyAchievement,
    ServiceCategory,
    CountryScholarshipGuide,
    CountryScholarship,
    StudyCountry,
    TeamMember,
)


def _schedule_sitemap_ping(**kwargs):
    try:
        ping_search_engines_sitemap()
    except Exception:
        logger.exception("sitemap ping failed")


for _model in _SITEMAP_CONTENT_MODELS:
    post_save.connect(_schedule_sitemap_ping, sender=_model, weak=False)
    post_delete.connect(_schedule_sitemap_ping, sender=_model, weak=False)


@receiver(post_save, sender=Institute)
@receiver(post_save, sender=University)
@receiver(post_save, sender=ConsultationSlot)
@receiver(post_save, sender=StudyCountry)
@receiver(post_save, sender=Course)
@receiver(post_save, sender=CourseInstructor)
@receiver(post_save, sender=Service)
@receiver(post_save, sender=ServiceCategory)
@receiver(post_save, sender=Major)
@receiver(post_save, sender=FAQ)
@receiver(post_save, sender=FAQCategory)
@receiver(post_save, sender=BlogPost)
@receiver(post_delete, sender=Institute)
@receiver(post_delete, sender=University)
@receiver(post_delete, sender=ConsultationSlot)
@receiver(post_delete, sender=StudyCountry)
@receiver(post_delete, sender=Course)
@receiver(post_delete, sender=CourseInstructor)
@receiver(post_delete, sender=Service)
@receiver(post_delete, sender=ServiceCategory)
@receiver(post_delete, sender=Major)
@receiver(post_delete, sender=FAQ)
@receiver(post_delete, sender=FAQCategory)
@receiver(post_delete, sender=BlogPost)
@receiver(post_save, sender=PricingCategory)
@receiver(post_save, sender=PricingTariff)
@receiver(post_save, sender=LivingAllowanceCountry)
@receiver(post_save, sender=TeamMember)
@receiver(post_delete, sender=PricingCategory)
@receiver(post_delete, sender=PricingTariff)
@receiver(post_delete, sender=LivingAllowanceCountry)
@receiver(post_delete, sender=TeamMember)
def invalidate_layout_cache_on_structure_change(sender, **kwargs):
    invalidate_layout_caches()


@receiver(post_save, sender=EvaluationRequest)
def refresh_evaluation_learning_on_change(sender, instance, **kwargs):
    """پس از ثبت یا به‌روزرسانی پرونده، یادگیری تطبیقی را برای پیشنهادهای بعدی آماده کن."""
    try:
        from core.evaluation_learning import mark_learning_stale

        mark_learning_stale()
    except Exception:
        logger.exception("mark_learning_stale failed pk=%s", instance.pk)


@receiver(post_save, sender=EvaluationRequest)
def notify_new_evaluation_request(sender, instance, created, **kwargs):
    if not created:
        return
    try:
        from core.evaluation_pipeline import skip_sync_evaluation_snapshot

        if skip_sync_evaluation_snapshot():
            _thread(f"eval-notify-{instance.pk}", _deliver_evaluation_request_notifications, instance.pk)
            return
    except Exception:
        logger.exception("eval async notify dispatch failed pk=%s", instance.pk)
    _deliver_evaluation_request_notifications(instance.pk)


def _deliver_evaluation_request_notifications(pk: int) -> None:
    try:
        instance = EvaluationRequest.objects.get(pk=pk)
    except EvaluationRequest.DoesNotExist:
        return
    if not instance.recommendation_snapshot:
        instance.refresh_from_db(fields=["recommendation_snapshot"])
    post_inbox_event(
        name=instance.full_name,
        email=instance.email or "",
        phone=instance.phone,
        subject="evaluation",
        message=(
            f"کشور مقصد: {instance.get_target_country_display()}\n"
            f"مقطع: {instance.get_current_degree_display()}\n"
            f"رشته: {instance.field_of_study or '-'}"
        ),
    )
    top_line = instance.get_recommendation_top_line() if hasattr(instance, "get_recommendation_top_line") else ""
    lines = [
        f"نام: {instance.full_name}",
        f"تلفن: {instance.phone}",
        f"کشور مقصد: {instance.get_target_country_display()}",
        f"مقطع: {instance.get_current_degree_display()}",
        f"رشته: {truncate_text(instance.field_of_study, 80)}",
    ]
    if top_line:
        lines.append(f"پیشنهاد هوشمند: {truncate_text(top_line, 100)}")
    _send_new_record_notification(
        title="فرم جدید ارزیابی اولیه",
        lines=lines,
        list_path="/admin/core/evaluationrequest/",
        change_path=f"/admin/core/evaluationrequest/{instance.pk}/change/",
    )
