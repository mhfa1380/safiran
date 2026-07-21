"""
حذف خودکار فایل‌های آپلودی از دیسک هنگام جایگزینی، پاک کردن یا حذف رکورد.
برای همه مدل‌های دارای ImageField/FileField (به‌جز مدل‌های سیستمی).
"""

from __future__ import annotations

import logging
import os
import re

from django.apps import apps
from django.conf import settings
from django.db import models
from django.db.models.signals import post_delete, post_save, pre_save

from core.ckeditor_assets import (
    delete_ckeditor_file,
    extract_ckeditor_paths,
    refresh_assets_for_paths,
)

logger = logging.getLogger(__name__)

FILE_FIELD_CLASSES = (models.FileField, models.ImageField)

# مدل‌هایی که نباید سیگنال فایل بگیرند
SKIP_MODEL_NAMES = frozenset(
    {
        "adminchangelog",
        "logentry",
        "session",
        "contenttype",
        "permission",
    }
)

# فشرده‌سازی پس از ذخیره (BlogPost / University / Major / Gallery خودشان در save فشرده می‌کنند)
COMPRESS_IMAGE_FIELDS: dict[str, tuple[str, ...]] = {
    "core.teammember": ("image",),
    "core.courseinstructor": ("image",),
}

# فیلدهای HTML که ممکن است تصویر CKEditor داشته باشند
RICH_TEXT_CKEDITOR_FIELDS: dict[str, tuple[str, ...]] = {
    "core.blogpost": ("content",),
    "core.course": ("description", "objectives", "conditions"),
    "core.major": ("description",),
    "core.faq": ("answer", "detail_content"),
    "core.monthlyachievement": ("detail_content",),
    "core.studycountry": (
        "description",
        "visa_info",
        "admission_info",
        "living_info",
        "scholarship_info",
    ),
    "core.service": ("description",),
    "core.university": ("description",),
}

_upload_signals_connected = False


def get_upload_file_field_names(model: type[models.Model]) -> list[str]:
    return [
        f.name
        for f in model._meta.concrete_fields
        if isinstance(f, FILE_FIELD_CLASSES)
    ]


def delete_stored_file(file_field) -> None:
    """حذف فایل از storage؛ خطا باعث شکست save نمی‌شود."""
    if not file_field:
        return
    name = getattr(file_field, "name", None) or ""
    if not name:
        return
    try:
        storage = file_field.storage
        if storage.exists(name):
            storage.delete(name)
    except Exception:
        logger.debug("delete_stored_file failed for %s", name, exc_info=True)


def _upload_names_differ(old_field, new_field) -> bool:
    old_name = (getattr(old_field, "name", None) or "") if old_field else ""
    new_name = (getattr(new_field, "name", None) or "") if new_field else ""
    return old_name != new_name


def cleanup_replaced_upload_files(sender, instance, **kwargs):
    if not instance.pk:
        return
    field_names = get_upload_file_field_names(sender)
    if not field_names:
        return
    try:
        old_instance = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        return
    for field_name in field_names:
        old_file = getattr(old_instance, field_name, None)
        new_file = getattr(instance, field_name, None)
        if old_file and _upload_names_differ(old_file, new_file):
            delete_stored_file(old_file)


def cleanup_upload_files_on_delete(sender, instance, **kwargs):
    for field_name in get_upload_file_field_names(sender):
        file_field = getattr(instance, field_name, None)
        if file_field:
            delete_stored_file(file_field)


def _compress_model_images(sender, instance, **kwargs):
    from core.utils import compress_image_file

    label = sender._meta.label_lower
    for field_name in COMPRESS_IMAGE_FIELDS.get(label, ()):
        file_field = getattr(instance, field_name, None)
        if file_field:
            compress_image_file(file_field)


def _rich_text_models() -> list[type[models.Model]]:
    result = []
    for label in RICH_TEXT_CKEDITOR_FIELDS:
        try:
            result.append(apps.get_model(label))
        except LookupError:
            continue
    return result


def _is_ckeditor_path_used_elsewhere(path: str, current_model, current_pk) -> bool:
    needle = f"/media/{path}"
    for model_cls in _rich_text_models():
        if model_cls == current_model and current_pk:
            qs = model_cls.objects.exclude(pk=current_pk)
        else:
            qs = model_cls.objects.all()
        fields = RICH_TEXT_CKEDITOR_FIELDS.get(model_cls._meta.label_lower, ())
        for field_name in fields:
            if qs.filter(**{f"{field_name}__contains": needle}).exists():
                return True
    return False


def _delete_ckeditor_file_by_path(rel_path: str) -> None:
    if not delete_ckeditor_file(rel_path):
        logger.debug("ckeditor file remove failed: %s", rel_path)


def cleanup_removed_ckeditor_assets(sender, instance, **kwargs):
    fields = RICH_TEXT_CKEDITOR_FIELDS.get(sender._meta.label_lower)
    if not fields or not instance.pk:
        return
    try:
        old_instance = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        return
    for field_name in fields:
        old_html = getattr(old_instance, field_name, "") or ""
        new_html = getattr(instance, field_name, "") or ""
        removed = extract_ckeditor_paths(old_html) - extract_ckeditor_paths(new_html)
        for path in removed:
            if not _is_ckeditor_path_used_elsewhere(path, sender, instance.pk):
                _delete_ckeditor_file_by_path(path)


def cleanup_ckeditor_assets_on_delete(sender, instance, **kwargs):
    fields = RICH_TEXT_CKEDITOR_FIELDS.get(sender._meta.label_lower)
    if not fields:
        return
    for field_name in fields:
        for path in extract_ckeditor_paths(getattr(instance, field_name, "") or ""):
            if not _is_ckeditor_path_used_elsewhere(path, sender, instance.pk):
                _delete_ckeditor_file_by_path(path)


def refresh_ckeditor_assets_after_save(sender, instance, **kwargs):
    fields = RICH_TEXT_CKEDITOR_FIELDS.get(sender._meta.label_lower)
    if not fields:
        return
    paths: set[str] = set()
    for field_name in fields:
        paths |= extract_ckeditor_paths(getattr(instance, field_name, "") or "")
    refresh_assets_for_paths(paths)


def _should_skip_model(model: type[models.Model]) -> bool:
    if not model._meta.managed:
        return True
    if model._meta.proxy or model._meta.abstract:
        return True
    if model._meta.model_name in SKIP_MODEL_NAMES:
        return True
    return False


def connect_upload_file_signals() -> None:
    """اتصال سیگنال‌ها به همه مدل‌های دارای فایل آپلودی (یک‌بار در ready)."""
    global _upload_signals_connected
    if _upload_signals_connected:
        return

    for model in apps.get_models():
        if _should_skip_model(model):
            continue

        label = model._meta.label_lower
        uid_base = label.replace(".", "_")
        file_fields = get_upload_file_field_names(model)

        if file_fields:
            pre_save.connect(
                cleanup_replaced_upload_files,
                sender=model,
                dispatch_uid=f"upload_replace_{uid_base}",
            )
            post_delete.connect(
                cleanup_upload_files_on_delete,
                sender=model,
                dispatch_uid=f"upload_delete_{uid_base}",
            )
            if label in COMPRESS_IMAGE_FIELDS:
                post_save.connect(
                    _compress_model_images,
                    sender=model,
                    dispatch_uid=f"upload_compress_{uid_base}",
                )

        if label in RICH_TEXT_CKEDITOR_FIELDS:
            pre_save.connect(
                cleanup_removed_ckeditor_assets,
                sender=model,
                dispatch_uid=f"ckeditor_replace_{uid_base}",
            )
            post_save.connect(
                refresh_ckeditor_assets_after_save,
                sender=model,
                dispatch_uid=f"ckeditor_refresh_{uid_base}",
            )
            post_delete.connect(
                cleanup_ckeditor_assets_on_delete,
                sender=model,
                dispatch_uid=f"ckeditor_delete_{uid_base}",
            )

    _upload_signals_connected = True
