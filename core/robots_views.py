"""
View برای robots.txt — راهنمای خزنده‌های موتورهای جستجو.
"""
from django.conf import settings
from django.http import HttpResponse


def robots_txt(request):
    """فایل robots.txt برای گوگل و سایر موتورهای جستجو."""
    site_url = getattr(settings, "SITE_URL", "").rstrip("/")
    if not site_url:
        site_url = f"{request.scheme}://{request.get_host()}"
    sitemap_url = f"{site_url}/sitemap.xml"
    content = f"""User-agent: *
Allow: /

# مسیرهای غیرمجاز برای ایندکس
Disallow: /admin/
Disallow: /admin/ckeditor-upload/
Disallow: /appointment/slots/

Sitemap: {sitemap_url}
"""
    return HttpResponse(content, content_type="text/plain; charset=utf-8")
