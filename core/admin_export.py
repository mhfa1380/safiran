"""
خروجی CSV/Excel از پنل ادمین — django-import-export.

- دکمه «خروجی» در لیست هر مدل (با فیلترهای فعال)
- اکشن گروهی «خروجی از موارد انتخاب‌شده»
- انتخاب فیلدها و فرمت (CSV / Excel) — همه برچسب‌ها فارسی
"""

from __future__ import annotations

from django.core.exceptions import FieldDoesNotExist
from django.utils.encoding import force_str

from import_export import resources
from import_export.admin import ExportActionMixin
from import_export.formats import base_formats
from import_export.forms import SelectableFieldsExportForm

# فیلدهایی که در خروجی نمی‌آیند
SKIP_EXPORT_FIELD_NAMES = frozenset({"password"})

# فیلدهای رایج با عنوان پیش‌فرض انگلیسی در جنگو
COMMON_FIELD_VERBOSE_FA = {
    "id": "شناسه",
    "pk": "شناسه",
}

# برچسب فارسی فیلدهای auth (مدل جنگو verbose_name انگلیسی دارد)
AUTH_FIELD_VERBOSE_FA = {
    "id": "شناسه",
    "username": "نام کاربری",
    "first_name": "نام",
    "last_name": "نام خانوادگی",
    "email": "ایمیل",
    "is_staff": "وضعیت کارمند",
    "is_active": "فعال",
    "is_superuser": "سوپرکاربر",
    "last_login": "آخرین ورود",
    "date_joined": "تاریخ عضویت",
    "groups": "گروه‌ها",
    "user_permissions": "مجوزهای کاربر",
    "name": "نام گروه",
    "permissions": "مجوزهای گروه",
}

_RESOURCE_CACHE: dict[str, type[resources.ModelResource]] = {}


def _persian_field_label(model, field_name: str, django_field=None) -> str:
    """عنوان فارسی فیلد برای فرم انتخاب و سرستون فایل خروجی."""
    if field_name in COMMON_FIELD_VERBOSE_FA:
        return COMMON_FIELD_VERBOSE_FA[field_name]
    if model._meta.app_label == "auth" and field_name in AUTH_FIELD_VERBOSE_FA:
        return AUTH_FIELD_VERBOSE_FA[field_name]
    if django_field is not None:
        verbose = getattr(django_field, "verbose_name", None)
        if verbose:
            return force_str(verbose)
    try:
        f = model._meta.get_field(field_name)
        return force_str(f.verbose_name)
    except FieldDoesNotExist:
        return field_name.replace("_", " ")


class SafiranModelResource(resources.ModelResource):
    """Resource با سرستون و برچسب‌های فارسی (verbose_name مدل)."""

    @classmethod
    def field_from_django_field(cls, field_name, django_field, readonly):
        field = super().field_from_django_field(field_name, django_field, readonly)
        field.column_name = _persian_field_label(cls._meta.model, field_name, django_field)
        return field

    @classmethod
    def get_display_name(cls):
        return force_str(cls._meta.model._meta.verbose_name_plural)


class _SafiranExportFormat:
    """برچسب فارسی فقط برای UI — get_title() باید کلید tablib (csv/xlsx) بماند."""

    display_title: str = ""

    @classmethod
    def get_display_title(cls) -> str:
        return cls.display_title or cls().get_title()


class SafiranCSV(_SafiranExportFormat, base_formats.CSV):
    display_title = "CSV (جدول متنی)"


class SafiranXLSX(_SafiranExportFormat, base_formats.XLSX):
    display_title = "اکسل (XLSX)"


class SafiranSelectableFieldsExportForm(SelectableFieldsExportForm):
    """فرم خروجی — برچسب فیلدها و فرمت به فارسی."""

    def __init__(self, formats, resources, **kwargs):
        super().__init__(formats, resources, **kwargs)
        if "format" in self.fields:
            self.fields["format"].label = "فرمت فایل"
        if "resource" in self.fields:
            self.fields["resource"].label = "بخش داده"

    def _init_formats(self, formats):
        if not formats:
            raise ValueError("invalid formats list")

        choices = [
            (
                str(i),
                fmt.get_display_title()
                if hasattr(fmt, "get_display_title")
                else fmt().get_title(),
            )
            for i, fmt in enumerate(formats)
        ]
        if len(formats) == 1:
            field = self.fields["format"]
            field.value = "0"
            field.initial = "0"
            field.widget.attrs["readonly"] = True
        if len(formats) > 1:
            choices.insert(0, ("", "---"))

        self.fields["format"].choices = choices

    def _get_field_label(self, resource: resources.ModelResource, field_name: str) -> str:
        field = resource.fields.get(field_name)
        if field and field.column_name:
            return force_str(field.column_name)
        return _persian_field_label(resource._meta.model, field_name)


def safiran_model_resource(model) -> type[SafiranModelResource]:
    """Resource پویا برای مدل — با کش بر اساس label."""
    label = model._meta.label_lower
    if label in _RESOURCE_CACHE:
        return _RESOURCE_CACHE[label]

    field_names: list[str] = []
    for field in model._meta.fields:
        if field.name in SKIP_EXPORT_FIELD_NAMES:
            continue
        field_names.append(field.name)
    for field in model._meta.many_to_many:
        field_names.append(field.name)

    meta = type(
        "Meta",
        (),
        {
            "model": model,
            "fields": tuple(field_names),
            "export_order": tuple(field_names),
        },
    )
    resource_cls = type(
        f"{model.__name__}SafiranExportResource",
        (SafiranModelResource,),
        {"Meta": meta},
    )
    _RESOURCE_CACHE[label] = resource_cls
    return resource_cls


class SafiranExportMixin(ExportActionMixin):
    """
    ExportMixin + اکشن گروهی.
    resource به‌صورت خودکار از فیلدهای مدل ساخته می‌شود.
    """

    export_form_class = SafiranSelectableFieldsExportForm

    def get_export_resource_classes(self, request):
        return [safiran_model_resource(self.model)]

    def get_export_formats(self):
        return [SafiranCSV, SafiranXLSX]

    def get_actions(self, request):
        actions = super().get_actions(request)
        if self.has_export_permission(request) and "export_admin_action" in actions:
            actions["export_admin_action"] = (
                type(self).export_admin_action,
                "export_admin_action",
                "خروجی CSV/Excel از موارد انتخاب‌شده",
            )
        return actions
