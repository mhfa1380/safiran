"""
View آپلود تصویر برای CKEditor.
فقط کاربران staff می‌توانند آپلود کنند.
"""
import io
import json
import os
import uuid

from PIL import Image, ImageOps
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.urls import reverse
from django.views.decorators.http import require_http_methods


ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
MAX_SIZE = 5 * 1024 * 1024  # 5 MB
TARGET_SIZE = 450 * 1024  # 450 KB
MAX_SIDE = 1920


def _compress_to_jpeg_bytes(upload_file) -> bytes:
    raw = upload_file.read()
    upload_file.seek(0)
    if not raw:
        return b""

    image = Image.open(io.BytesIO(raw))
    image = ImageOps.exif_transpose(image)
    if image.mode in ("RGBA", "LA", "P"):
        image = image.convert("RGB")

    if max(image.size) > MAX_SIDE:
        image.thumbnail((MAX_SIDE, MAX_SIDE), Image.Resampling.LANCZOS)

    quality = 82
    min_quality = 35
    out = io.BytesIO()

    while quality >= min_quality:
        out.seek(0)
        out.truncate(0)
        image.save(out, format="JPEG", optimize=True, progressive=True, quality=quality)
        if out.tell() <= TARGET_SIZE:
            break
        quality -= 5

    return out.getvalue()


def _absolute_media_url(request, rel_path: str) -> str:
    media_url = f"{settings.MEDIA_URL.rstrip('/')}/{rel_path.replace(os.sep, '/').lstrip('/')}"
    if request:
        return request.build_absolute_uri(media_url)
    site = getattr(settings, "SITE_URL", "").rstrip("/")
    if site:
        return f"{site}{media_url}"
    return media_url


def _error_response(request, message: str, status: int = 400):
    func_num = request.GET.get("CKEditorFuncNum")
    if func_num is not None:
        escaped = json.dumps(message, ensure_ascii=False)
        script = (
            f'<script type="text/javascript">'
            f'window.parent.CKEDITOR.tools.callFunction({func_num}, "", {escaped});'
            f"</script>"
        )
        return HttpResponse(script, content_type="text/html; charset=utf-8", status=200)
    return JsonResponse({"uploaded": 0, "error": {"message": message}}, status=status)


def _success_response(request, *, file_name: str, url: str):
    func_num = request.GET.get("CKEditorFuncNum")
    payload = {"uploaded": 1, "fileName": file_name, "url": url}
    if func_num is not None:
        script = (
            f'<script type="text/javascript">'
            f"window.parent.CKEDITOR.tools.callFunction({func_num}, {json.dumps(url)}, '');"
            f"</script>"
        )
        return HttpResponse(script, content_type="text/html; charset=utf-8")
    return JsonResponse(payload)


def _get_uploaded_file(request):
    for key in ("upload", "file"):
        if key in request.FILES:
            return request.FILES[key]
    if request.FILES:
        return next(iter(request.FILES.values()))
    return None


@require_http_methods(["POST"])
def ckeditor_upload(request):
    if not request.user.is_authenticated or not request.user.is_staff:
        return _error_response(request, "برای آپلود باید وارد پنل ادمین شوید.", status=403)

    upload_file = _get_uploaded_file(request)
    if not upload_file:
        return _error_response(request, "فایلی ارسال نشده است.")

    ext = os.path.splitext(upload_file.name)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return _error_response(request, "فرمت فایل مجاز نیست. فقط jpg, png, gif, webp.")

    if upload_file.size > MAX_SIZE:
        return _error_response(request, "حجم فایل بیش از ۵ مگابایت است.")

    safe_name = f"{uuid.uuid4().hex}.jpg"
    rel_path = os.path.join("ckeditor", safe_name)
    full_path = os.path.join(settings.MEDIA_ROOT, rel_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)

    try:
        compressed = _compress_to_jpeg_bytes(upload_file)
        if not compressed:
            return _error_response(request, "فایل تصویر معتبر نیست.")

        with open(full_path, "wb") as f:
            f.write(compressed)

        try:
            from core.ckeditor_assets import register_uploaded_file

            register_uploaded_file(
                rel_path.replace("\\", "/"),
                len(compressed),
                uploaded_by=request.user,
            )
        except Exception:
            pass
    except Exception as exc:
        return _error_response(request, f"خطا در ذخیره فایل: {exc}", status=500)

    url = _absolute_media_url(request, rel_path)
    return _success_response(request, file_name=safe_name, url=url)


def get_ckeditor_upload_url(request=None) -> str:
    path = reverse("ckeditor_upload")
    if request:
        return request.build_absolute_uri(path)
    site = getattr(settings, "SITE_URL", "").rstrip("/")
    return f"{site}{path}" if site else path
