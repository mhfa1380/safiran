"""
فهرست‌سازی و ردیابی فایل‌های آپلودشده در CKEditor.
"""
from __future__ import annotations

import os
import re
from collections import Counter

from django.apps import apps
from django.conf import settings
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone

CKEDITOR_PATH_PATTERN = re.compile(
    r"""(?:https?://[^"'\s]+)?(?:/media/|media/)(ckeditor/[^"'\s?#]+)""",
    flags=re.IGNORECASE,
)

CKEDITOR_MEDIA_SUBDIR = "ckeditor"


def extract_ckeditor_paths(html_value: str) -> set[str]:
    if not html_value:
        return set()
    paths = set()
    for match in CKEDITOR_PATH_PATTERN.findall(html_value):
        cleaned = match.lstrip("/").strip()
        if cleaned.startswith(f"{CKEDITOR_MEDIA_SUBDIR}/"):
            paths.add(cleaned)
    return paths


def _get_model(label: str):
    return apps.get_model(label)


# منابع محتوای HTML که ممکن است تصویر CKEditor داشته باشند.
RICH_TEXT_SOURCES = (
    {
        "label": "وبلاگ",
        "model": "core.BlogPost",
        "title_attr": "title",
        "fields": (("content", "متن مقاله"),),
    },
    {
        "label": "سوالات متداول",
        "model": "core.FAQ",
        "title_attr": "question",
        "fields": (("answer", "پاسخ کوتاه"), ("detail_content", "متن کامل")),
    },
    {
        "label": "دستاوردهای ما",
        "model": "core.MonthlyAchievement",
        "title_attr": "title",
        "fields": (("detail_content", "متن کامل"),),
    },
    {
        "label": "رشته تحصیلی",
        "model": "core.Major",
        "title_attr": "title",
        "fields": (("description", "توضیحات"),),
    },
    {
        "label": "دوره آموزشی",
        "model": "core.Course",
        "title_attr": "title",
        "fields": (
            ("description", "توضیحات"),
            ("objectives", "اهداف"),
            ("conditions", "شرایط"),
        ),
    },
    {
        "label": "کشور تحصیلی",
        "model": "core.StudyCountry",
        "title_attr": "name",
        "fields": (
            ("description", "توضیحات"),
            ("visa_info", "ویزا"),
            ("admission_info", "پذیرش"),
            ("living_info", "هزینه زندگی"),
            ("scholarship_info", "بورسیه"),
        ),
    },
    {
        "label": "دانشگاه",
        "model": "core.University",
        "title_attr": "name_fa",
        "fields": (("description", "توضیحات"),),
    },
    {
        "label": "خدمات",
        "model": "core.Service",
        "title_attr": "title",
        "fields": (("description", "توضیحات"),),
    },
)


def rich_text_model_fields():
    """سازگاری با signals — {(Model, (field_names...))}."""
    result = {}
    for source in RICH_TEXT_SOURCES:
        model = _get_model(source["model"])
        field_names = tuple(name for name, _ in source["fields"])
        result[model] = field_names
    return result


def format_bytes(size: int) -> str:
    if size < 1024:
        return f"{size} بایت"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} کیلوبایت"
    return f"{size / (1024 * 1024):.2f} مگابایت"


def _path_needles(rel_path: str) -> tuple[str, ...]:
    return (
        f"/media/{rel_path}",
        f"media/{rel_path}",
        rel_path,
    )


def _admin_change_url(model, pk: int) -> str:
    return reverse(
        f"admin:{model._meta.app_label}_{model._meta.model_name}_change",
        args=[pk],
    )


def find_usages_for_path(rel_path: str) -> list[dict]:
    needles = _path_needles(rel_path)
    usages: list[dict] = []

    for source in RICH_TEXT_SOURCES:
        model = _get_model(source["model"])
        title_attr = source["title_attr"]
        for field_name, field_label in source["fields"]:
            query = Q()
            for needle in needles:
                query |= Q(**{f"{field_name}__contains": needle})
            if not query:
                continue
            for obj in model.objects.filter(query).only("pk", title_attr):
                title = str(getattr(obj, title_attr, "") or f"#{obj.pk}")
                usages.append(
                    {
                        "source_label": source["label"],
                        "model": model._meta.label_lower,
                        "pk": obj.pk,
                        "title": title,
                        "field_name": field_name,
                        "field_label": field_label,
                        "admin_url": _admin_change_url(model, obj.pk),
                    }
                )
    return usages


def _summarize_categories(usages: list[dict]) -> tuple[str, str]:
    if not usages:
        return "", ""
    counts = Counter(u["source_label"] for u in usages)
    parts = [f"{label} ({count})" for label, count in counts.most_common()]
    summary = " · ".join(parts)
    primary = counts.most_common(1)[0][0]
    return primary, summary


def index_ckeditor_asset(asset) -> None:
    usages = find_usages_for_path(asset.path)
    primary, summary = _summarize_categories(usages)
    asset.usage_count = len(usages)
    asset.usage_snapshot = usages
    asset.primary_category = primary
    asset.categories_summary = summary
    asset.is_orphan = len(usages) == 0
    asset.indexed_at = timezone.now()
    asset.save(
        update_fields=[
            "usage_count",
            "usage_snapshot",
            "primary_category",
            "categories_summary",
            "is_orphan",
            "indexed_at",
        ]
    )


def sync_ckeditor_assets_from_disk() -> tuple[int, int, int]:
    """
    همگام‌سازی پوشه media/ckeditor با دیتابیس و بروزرسانی محل استفاده.
    برمی‌گرداند: (تعداد فایل‌ها، تعداد بدون استفاده، تعداد حذف‌شده از دیتابیس)
    """
    from core.models import CkeditorAsset

    media_dir = os.path.join(settings.MEDIA_ROOT, CKEDITOR_MEDIA_SUBDIR)
    found_paths: set[str] = set()
    created_or_updated = 0

    if os.path.isdir(media_dir):
        for filename in os.listdir(media_dir):
            full_path = os.path.join(media_dir, filename)
            if not os.path.isfile(full_path):
                continue
            rel_path = f"{CKEDITOR_MEDIA_SUBDIR}/{filename}"
            found_paths.add(rel_path)
            size_bytes = os.path.getsize(full_path)
            asset, _created = CkeditorAsset.objects.get_or_create(
                path=rel_path,
                defaults={"size_bytes": size_bytes},
            )
            dirty = False
            if asset.size_bytes != size_bytes:
                asset.size_bytes = size_bytes
                dirty = True
            if dirty:
                asset.save(update_fields=["size_bytes"])
            index_ckeditor_asset(asset)
            created_or_updated += 1

    removed, _ = CkeditorAsset.objects.exclude(path__in=found_paths).delete()
    orphan_count = CkeditorAsset.objects.filter(is_orphan=True).count()
    return created_or_updated, orphan_count, removed


def register_uploaded_file(
    rel_path: str,
    size_bytes: int,
    *,
    uploaded_by=None,
) -> None:
    from core.models import CkeditorAsset

    asset, created = CkeditorAsset.objects.update_or_create(
        path=rel_path,
        defaults={
            "size_bytes": size_bytes,
            "uploaded_by": uploaded_by,
        },
    )
    if created:
        asset.uploaded_at = timezone.now()
        asset.save(update_fields=["uploaded_at"])
    index_ckeditor_asset(asset)


def delete_ckeditor_file(rel_path: str) -> bool:
    from core.models import CkeditorAsset

    abs_path = os.path.join(settings.MEDIA_ROOT, rel_path)
    if os.path.exists(abs_path):
        try:
            os.remove(abs_path)
        except OSError:
            return False
    CkeditorAsset.objects.filter(path=rel_path).delete()
    return True


def refresh_assets_for_paths(paths: set[str]) -> None:
    """پس از ذخیره محتوا، وضعیت استفاده فایل‌های مرتبط را بروز می‌کند."""
    if not paths:
        return
    from core.models import CkeditorAsset

    for rel_path in paths:
        try:
            asset = CkeditorAsset.objects.get(path=rel_path)
        except CkeditorAsset.DoesNotExist:
            full_path = os.path.join(settings.MEDIA_ROOT, rel_path)
            if os.path.isfile(full_path):
                register_uploaded_file(rel_path, os.path.getsize(full_path))
            continue
        index_ckeditor_asset(asset)
