"""URL configuration for سفیران آینده روشن."""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

from core.llms_views import (
    ai_index_json,
    blog_rss_feed,
    llms_ctx_txt,
    llms_full_txt,
    llms_txt,
    well_known_llms,
)
from core.robots_views import robots_txt
from core.sitemap_views import sitemap_view
from core.sitemaps import (
    AchievementDetailSitemap,
    BlogPostSitemap,
    CountryScholarshipSitemap,
    CountrySitemap,
    CourseInstructorSitemap,
    CourseSitemap,
    FAQCategorySitemap,
    FAQDetailSitemap,
    MajorSitemap,
    ServiceCategorySitemap,
    StaticViewSitemap,
    TeamMemberSitemap,
    UniversitySitemap,
)

handler403 = "core.views.permission_denied"
handler404 = "core.views.page_not_found"

from core.agent_views import db_export
from core.ckeditor_views import ckeditor_upload

sitemaps = {
    "static": StaticViewSitemap,
    "blog": BlogPostSitemap,
    "universities": UniversitySitemap,
    "courses": CourseSitemap,
    "course_instructors": CourseInstructorSitemap,
    "majors": MajorSitemap,
    "countries": CountrySitemap,
    "country_scholarships": CountryScholarshipSitemap,
    "faq_categories": FAQCategorySitemap,
    "faq_items": FAQDetailSitemap,
    "service_categories": ServiceCategorySitemap,
    "achievements": AchievementDetailSitemap,
    "team": TeamMemberSitemap,
}

urlpatterns = [
    path(
        "favicon.ico",
        RedirectView.as_view(url="/static/panel/favicon.ico", permanent=False),
        name="favicon",
    ),
    path("api/agent/db-export", db_export, name="mhfa_db_export"),
    # باید قبل از admin.site.urls باشد؛ در غیر این صورت مسیر توسط ادمین 404 می‌شود.
    path("admin/ckeditor-upload/", ckeditor_upload, name="ckeditor_upload"),
    path("ckeditor-upload/", ckeditor_upload, name="ckeditor_upload_public"),
    path("admin/", admin.site.urls),
    path("panel/", include("panel.urls")),
    path("sitemap.xml", sitemap_view, {"sitemaps": sitemaps}, name="sitemap"),
    path("robots.txt", robots_txt),
    path("llms.txt", llms_txt),
    path("llms-full.txt", llms_full_txt),
    path("llms-ctx.txt", llms_ctx_txt),
    path("ai-index.json", ai_index_json),
    path("blog/feed.xml", blog_rss_feed, name="blog_rss"),
    path(".well-known/llms.txt", well_known_llms),
    path("", include("core.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
