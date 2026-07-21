"""
لاگ تغییرات ادمین — ذخیره فشرده، بازگردانی، نگهداری محدود.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any
from uuid import UUID

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone

logger = logging.getLogger(__name__)

# مدل‌هایی که لاگ نمی‌شوند (خود لاگ، سشن، لاگ پیش‌فرض جنگو)
SKIP_MODEL_LABELS = frozenset(
    {
        "adminchangelog",
        "logentry",
        "session",
        "contenttype",
        "permission",
    }
)

SKIP_FIELD_NAMES = frozenset({"password", "last_login"})


def _json_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, models.Model):
        return value.pk
    if hasattr(value, "name"):  # FileField
        return value.name or None
    if isinstance(value, (list, tuple)):
        return [_json_value(v) for v in value]
    return str(value)


def serialize_instance(instance: models.Model) -> dict[str, Any]:
    """تبدیل نمونه مدل به dict قابل ذخیره در JSON."""
    data: dict[str, Any] = {}
    for field in instance._meta.fields:
        if field.name in SKIP_FIELD_NAMES:
            continue
        if field.auto_created and not field.concrete:
            continue
        data[field.name] = _json_value(getattr(instance, field.name))

    for field in instance._meta.many_to_many:
        if not field.concrete:
            continue
        try:
            data[field.name] = list(
                getattr(instance, field.name).values_list("pk", flat=True)
            )
        except Exception:
            data[field.name] = []
    return data


def _changed_fields(before: dict | None, after: dict | None) -> list[str]:
    if not before or not after:
        return []
    keys = set(before) | set(after)
    return sorted(k for k in keys if before.get(k) != after.get(k))


def should_audit_model(model: type[models.Model]) -> bool:
    if not issubclass(model, models.Model):
        return False
    label = model._meta.model_name
    if label in SKIP_MODEL_LABELS:
        return False
    if model._meta.app_label not in ("core", "auth"):
        return False
    return True


def log_admin_change(
    *,
    user,
    instance: models.Model,
    action: str,
    before: dict[str, Any] | None = None,
    note: str = "",
) -> None:
    from core.models import AdminChangeLog

    model = instance.__class__
    if not should_audit_model(model):
        return

    after = serialize_instance(instance) if action != AdminChangeLog.ACTION_DELETE else None
    if action == AdminChangeLog.ACTION_DELETE:
        payload_before = before or after
        payload_after = None
    else:
        payload_before = before
        payload_after = after

    changed = _changed_fields(payload_before, payload_after)
    if action == AdminChangeLog.ACTION_UPDATE and not changed:
        return

    try:
        AdminChangeLog.objects.create(
            user=user if getattr(user, "is_authenticated", False) else None,
            content_type=ContentType.objects.get_for_model(model),
            object_id=str(instance.pk),
            object_repr=str(instance)[:255],
            action=action,
            payload={
                "before": payload_before,
                "after": payload_after,
                "changed_fields": changed,
            },
            note=note[:500],
        )
    except Exception:
        logger.exception("log_admin_change failed for %s pk=%s", model.__name__, instance.pk)


def revert_change_log(log, *, user) -> models.Model:
    """بازگردانی به وضعیت قبل بر اساس یک رکورد لاگ."""
    from core.models import AdminChangeLog

    if log.reverted_at:
        raise ValidationError("این تغییر قبلاً بازگردانی شده است.")

    if log.action not in (
        AdminChangeLog.ACTION_UPDATE,
        AdminChangeLog.ACTION_DELETE,
        AdminChangeLog.ACTION_CREATE,
    ):
        raise ValidationError("این نوع عملیات قابل بازگردانی نیست.")

    model = log.content_type.model_class()
    if model is None:
        raise ValidationError("مدل مربوطه دیگر وجود ندارد.")

    payload = log.payload or {}
    before = payload.get("before")
    after = payload.get("after")

    with transaction.atomic():
        if log.action == AdminChangeLog.ACTION_CREATE:
            if not log.object_id:
                raise ValidationError("شناسه شیء موجود نیست.")
            try:
                obj = model.objects.get(pk=log.object_id)
            except model.DoesNotExist:
                raise ValidationError("رکورد از قبل حذف شده است.") from None
            snapshot = serialize_instance(obj)
            obj.delete()
            log.reverted_at = timezone.now()
            log.reverted_by = user
            log.save(update_fields=["reverted_at", "reverted_by"])
            AdminChangeLog.objects.create(
                user=user,
                content_type=log.content_type,
                object_id=log.object_id,
                object_repr=log.object_repr,
                action=AdminChangeLog.ACTION_REVERT,
                payload={"before": snapshot, "after": None, "reverted_log_id": log.pk},
                note=f"بازگردانی ایجاد (حذف رکورد) — لاگ #{log.pk}",
            )
            return obj

        if log.action == AdminChangeLog.ACTION_DELETE:
            if not before:
                raise ValidationError("نسخه قبلی برای بازسازی موجود نیست.")
            obj = _restore_from_snapshot(model, before, object_id=log.object_id)
            log.reverted_at = timezone.now()
            log.reverted_by = user
            log.save(update_fields=["reverted_at", "reverted_by"])
            AdminChangeLog.objects.create(
                user=user,
                content_type=log.content_type,
                object_id=str(obj.pk),
                object_repr=str(obj)[:255],
                action=AdminChangeLog.ACTION_REVERT,
                payload={"before": None, "after": serialize_instance(obj), "reverted_log_id": log.pk},
                note=f"بازگردانی حذف — لاگ #{log.pk}",
            )
            return obj

        # update
        if not before:
            raise ValidationError("نسخه قبلی برای بازگردانی موجود نیست.")
        try:
            obj = model.objects.get(pk=log.object_id)
        except model.DoesNotExist:
            obj = _restore_from_snapshot(model, before, object_id=log.object_id)
        else:
            current = serialize_instance(obj)
            _apply_snapshot(obj, before)
            obj.save()
            AdminChangeLog.objects.create(
                user=user,
                content_type=log.content_type,
                object_id=str(obj.pk),
                object_repr=str(obj)[:255],
                action=AdminChangeLog.ACTION_REVERT,
                payload={
                    "before": current,
                    "after": serialize_instance(obj),
                    "reverted_log_id": log.pk,
                },
                note=f"بازگردانی ویرایش — لاگ #{log.pk}",
            )
        log.reverted_at = timezone.now()
        log.reverted_by = user
        log.save(update_fields=["reverted_at", "reverted_by"])
        return obj


def _restore_from_snapshot(
    model: type[models.Model], snapshot: dict, *, object_id: str | None = None
) -> models.Model:
    pk = object_id or snapshot.get(model._meta.pk.name)
    if pk is not None:
        try:
            return model.objects.get(pk=pk)
        except model.DoesNotExist:
            pass
    obj = model()
    _apply_snapshot(obj, snapshot)
    if pk is not None and model._meta.pk.name:
        setattr(obj, model._meta.pk.name, pk)
    obj.save()
    return obj


def _apply_snapshot(obj: models.Model, snapshot: dict) -> None:
    m2m_data: dict[str, list] = {}
    for field in obj._meta.fields:
        if field.name not in snapshot:
            continue
        if field.name in SKIP_FIELD_NAMES:
            continue
        if field.many_to_many:
            continue
        if field.primary_key and snapshot.get(field.name) is None:
            continue
        value = snapshot[field.name]
        if field.is_relation and field.many_to_one:
            if value is None or value == "":
                setattr(obj, field.attname, None)
            else:
                setattr(obj, field.attname, value)
            continue
        if field.get_internal_type() in ("DateTimeField", "DateField", "TimeField"):
            setattr(obj, field.name, value)
            continue
        setattr(obj, field.name, value)

    for field in obj._meta.many_to_many:
        if field.name in snapshot:
            m2m_data[field.name] = snapshot[field.name] or []

    obj.save()

    for name, pks in m2m_data.items():
        getattr(obj, name).set(pks)


class AdminAuditMixin:
    """ثبت خودکار تغییرات ادمین — روی ModelAdminها قرار دهید."""

    audit_enabled = True

    def save_model(self, request, obj, form, change):
        before_data = None
        if change and self.audit_enabled and obj.pk:
            try:
                old = obj.__class__.objects.get(pk=obj.pk)
                before_data = serialize_instance(old)
            except obj.__class__.DoesNotExist:
                before_data = None

        super().save_model(request, obj, form, change)

        if self.audit_enabled:
            from core.models import AdminChangeLog

            log_admin_change(
                user=request.user,
                instance=obj,
                action=AdminChangeLog.ACTION_UPDATE if change else AdminChangeLog.ACTION_CREATE,
                before=before_data,
            )

    def delete_model(self, request, obj):
        before_data = serialize_instance(obj) if self.audit_enabled else None
        super().delete_model(request, obj)
        if self.audit_enabled:
            from core.models import AdminChangeLog

            log_admin_change(
                user=request.user,
                instance=obj,
                action=AdminChangeLog.ACTION_DELETE,
                before=before_data,
            )

    def delete_queryset(self, request, queryset):
        if self.audit_enabled:
            from core.models import AdminChangeLog

            for obj in queryset:
                log_admin_change(
                    user=request.user,
                    instance=obj,
                    action=AdminChangeLog.ACTION_DELETE,
                    before=serialize_instance(obj),
                )
        super().delete_queryset(request, queryset)
