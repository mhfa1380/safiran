"""
فشرده‌سازی تصاویر آپلودی — تبدیل به JPEG و محدودیت حجم (پیش‌فرض ۴۰۰KB).
"""
from __future__ import annotations

import io
import os

from django.core.files.base import ContentFile
from PIL import Image, ImageOps

DEFAULT_MAX_BYTES = 400 * 1024
DEFAULT_MAX_SIDE = 1920
DEFAULT_MIN_QUALITY = 35
DEFAULT_QUALITY = 85
DEFAULT_QUALITY_STEP = 5


def compress_to_jpeg_bytes(
    raw: bytes,
    *,
    max_bytes: int = DEFAULT_MAX_BYTES,
    max_side: int = DEFAULT_MAX_SIDE,
) -> bytes:
    """خواندن بایت خام تصویر و برگرداندن JPEG فشرده زیر سقف حجم."""
    if not raw:
        return b""

    img = Image.open(io.BytesIO(raw))
    img = ImageOps.exif_transpose(img)
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGB")
    elif img.mode != "RGB":
        img = img.convert("RGB")

    if max(img.size) > max_side:
        img.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)

    quality = DEFAULT_QUALITY
    output = io.BytesIO()
    while quality >= DEFAULT_MIN_QUALITY:
        output.seek(0)
        output.truncate(0)
        img.save(output, format="JPEG", optimize=True, progressive=True, quality=quality)
        if output.tell() <= max_bytes:
            return output.getvalue()
        quality -= DEFAULT_QUALITY_STEP

    return output.getvalue()


def compress_image_field_to_jpeg(
    file_field,
    *,
    max_bytes: int = DEFAULT_MAX_BYTES,
    max_side: int = DEFAULT_MAX_SIDE,
    target_name: str | None = None,
) -> None:
    """
    فشرده‌سازی فایل موجود در ImageField/FileField و ذخیره مجدد به‌صورت JPEG.
    """
    if not file_field:
        return
    if not hasattr(file_field, "file") and not getattr(file_field, "name", None):
        return

    try:
        file_field.open("rb")
        raw = file_field.read()
    except (ValueError, FileNotFoundError, OSError):
        return
    finally:
        try:
            file_field.close()
        except Exception:
            pass

    if not raw:
        return

    compressed = compress_to_jpeg_bytes(raw, max_bytes=max_bytes, max_side=max_side)
    if not compressed:
        return

    if target_name:
        new_name = target_name
    else:
        name_root, _ = os.path.splitext(file_field.name or "image")
        new_name = f"{name_root}.jpg"

    storage = file_field.storage
    for name in {getattr(file_field, "name", None) or "", new_name}:
        if not name:
            continue
        try:
            if storage.exists(name):
                storage.delete(name)
        except OSError:
            pass

    file_field.save(new_name, ContentFile(compressed), save=False)
