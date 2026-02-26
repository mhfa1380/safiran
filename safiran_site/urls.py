"""URL configuration for سفیران آینده روشن."""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import path, include

from core.robots_views import robots_txt
from core.sitemaps import (
    BlogPostSitemap,
    CourseSitemap,
    MajorSitemap,
    StaticViewSitemap,
    UniversitySitemap,
)

handler403 = "core.views.permission_denied"
handler404 = "core.views.page_not_found"

from core.ckeditor_views import ckeditor_upload

sitemaps = {
    "static": StaticViewSitemap,
    "blog": BlogPostSitemap,
    "universities": UniversitySitemap,
    "courses": CourseSitemap,
    "majors": MajorSitemap,
}

urlpatterns = [
    path("admin/", admin.site.urls),
    path("admin/ckeditor-upload/", ckeditor_upload),
    path("sitemap.xml", sitemap, {"sitemaps": sitemaps}, name="django.contrib.sitemaps.views.sitemap"),
    path("robots.txt", robots_txt),
    path("", include("core.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
