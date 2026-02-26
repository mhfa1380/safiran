"""
View آپلود تصویر برای CKEditor.
فقط کاربران staff می‌توانند آپلود کنند.
"""
import os
import uuid
from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods


ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
MAX_SIZE = 5 * 1024 * 1024  # 5 MB


@staff_member_required
@csrf_exempt
@require_http_methods(["POST"])
def ckeditor_upload(request):
    """
    آپلود تصویر برای CKEditor.
    پاسخ JSON مطابق API مورد انتظار CKEditor 4.
    """
    upload_file = request.FILES.get("upload")
    if not upload_file:
        return JsonResponse({
            "uploaded": 0,
            "error": {"message": "فایلی ارسال نشده است."},
        }, status=400)

    ext = os.path.splitext(upload_file.name)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return JsonResponse({
            "uploaded": 0,
            "error": {"message": "فرمت فایل مجاز نیست. فقط تصویر (jpg, png, gif, webp)."},
        }, status=400)

    if upload_file.size > MAX_SIZE:
        return JsonResponse({
            "uploaded": 0,
            "error": {"message": "حجم فایل بیش از ۵ مگابایت است."},
        }, status=400)

    # ذخیره با نام یکتا برای جلوگیری از تداخل
    safe_name = f"{uuid.uuid4().hex}{ext}"
    upload_to = "ckeditor/"
    rel_path = os.path.join(upload_to, safe_name)
    full_path = os.path.join(settings.MEDIA_ROOT, rel_path)

    os.makedirs(os.path.dirname(full_path), exist_ok=True)

    try:
        with open(full_path, "wb") as f:
            for chunk in upload_file.chunks():
                f.write(chunk)
    except OSError as e:
        return JsonResponse({
            "uploaded": 0,
            "error": {"message": f"خطا در ذخیره فایل: {str(e)}"},
        }, status=500)

    url = f"{settings.MEDIA_URL}{rel_path.replace(os.sep, '/')}"
    return JsonResponse({
        "uploaded": 1,
        "fileName": safe_name,
        "url": url,
    })
