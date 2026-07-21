"""
Sitemap برای ایندکس شدن صفحات توسط موتورهای جستجو.

همهٔ بخش‌ها از دیتابیس خوانده می‌شوند؛ با انتشار یا ویرایش محتوا (مخصوصاً وبلاگ)
آدرس‌ها بلافاصله در /sitemap.xml ظاهر می‌شوند.
"""
from __future__ import annotations

from datetime import datetime
from urllib.parse import urlparse

from django.conf import settings
from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from django.utils import timezone

from .models import (
    BlogPost,
    CountryScholarshipGuide,
    Course,
    CourseInstructor,
    FAQ,
    FAQCategory,
    Major,
    MonthlyAchievement,
    ServiceCategory,
    StudyCountry,
    TeamMember,
    University,
)


def _site_domain_and_protocol() -> tuple[str | None, str]:
    raw = (getattr(settings, "SITE_URL", None) or "").strip()
    if not raw:
        return None, "https"
    parsed = urlparse(raw if "://" in raw else f"https://{raw}")
    domain = parsed.netloc or (parsed.path.split("/")[0] if parsed.path else None)
    return domain, parsed.scheme or "https"


def _latest_datetime(*values: datetime | None) -> datetime | None:
    candidates = [v for v in values if v is not None]
    return max(candidates) if candidates else None


class SafiranSitemap(Sitemap):
    """پایهٔ مشترک: دامنه و پروتکل از SITE_URL (canonical برای production)."""

    protocol = "https"

    def get_protocol(self, protocol=None):
        _, proto = _site_domain_and_protocol()
        return proto

    def get_domain(self, site=None):
        domain, _ = _site_domain_and_protocol()
        if domain:
            return domain
        return super().get_domain(site)


class StaticViewSitemap(SafiranSitemap):
    """صفحات استاتیک و لیست‌های اصلی."""

    priority = 0.9
    changefreq = "weekly"

    # (name, priority) — صفحهٔ اصلی و محتوای تازه اولویت بالاتر
    _PAGES: tuple[tuple[str, float], ...] = (
        ("index", 1.0),
        ("blog", 0.95),
        ("about", 0.88),
        ("services", 0.9),
        ("pricing", 0.88),
        ("appointment", 0.87),
        ("evaluation", 0.94),
        ("faq", 0.88),
        ("contact", 0.85),
        ("majors", 0.88),
        ("schools_list", 0.9),
        ("monthly_achievements", 0.86),
        ("courses_list", 0.87),
    )

    def items(self):
        available = {name for name, _ in self._PAGES}
        if not Course.objects.filter(is_active=True).exists():
            available.discard("courses_list")
        return [(name, priority) for name, priority in self._PAGES if name in available]

    def location(self, item):
        name, _priority = item
        return reverse(name)

    def priority(self, item):
        _name, priority = item
        return priority


class BlogPostSitemap(SafiranSitemap):
    """پست‌های منتشرشدهٔ وبلاگ — به‌روزرسانی روزانه."""

    changefreq = "daily"
    priority = 0.82

    def items(self):
        return (
            BlogPost.objects.filter(is_published=True)
            .only("slug", "canonical_url", "created_at", "updated_at")
            .order_by("-updated_at", "-created_at")
        )

    def location(self, obj):
        canonical = (obj.canonical_url or "").strip()
        if canonical:
            parsed = urlparse(canonical)
            domain, _ = _site_domain_and_protocol()
            if parsed.path and (not parsed.netloc or (domain and parsed.netloc == domain)):
                return parsed.path
        return reverse("blog_detail", kwargs={"slug": obj.slug})

    def lastmod(self, obj):
        return _latest_datetime(obj.updated_at, obj.created_at)

    def priority(self, obj):
        """مطالب تازه‌تر کمی اولویت بالاتر دارند."""
        from .gsc_indexing import gsc_boost_priority

        base = gsc_boost_priority(obj.slug, kind="blogs", default=0.82)
        ref = _latest_datetime(obj.updated_at, obj.created_at)
        if not ref:
            return base
        now = timezone.now()
        if timezone.is_naive(ref):
            ref = timezone.make_aware(ref)
        age_days = (now - ref).days
        if age_days <= 7:
            return max(base, 0.9)
        if age_days <= 30:
            return max(base, 0.85)
        return base


class UniversitySitemap(SafiranSitemap):
    changefreq = "monthly"
    priority = 0.85

    def items(self):
        return (
            University.objects.only("slug", "created_at")
            .order_by("country", "city", "name_fa")
        )

    def location(self, obj):
        return reverse("school_detail", kwargs={"slug": obj.slug})

    def lastmod(self, obj):
        return obj.created_at

    def priority(self, obj):
        from .gsc_indexing import gsc_boost_priority

        return gsc_boost_priority(obj.slug, kind="universities", default=0.85)


class CourseSitemap(SafiranSitemap):
    changefreq = "monthly"
    priority = 0.8

    def items(self):
        return (
            Course.objects.filter(is_active=True, external_url="")
            .only("slug")
            .order_by("order", "id")
        )

    def location(self, obj):
        return reverse("course_details", kwargs={"slug": obj.slug})


class CourseInstructorSitemap(SafiranSitemap):
    changefreq = "monthly"
    priority = 0.78

    def items(self):
        return (
            CourseInstructor.objects.filter(is_active=True)
            .only("slug")
            .order_by("order", "id")
        )

    def location(self, obj):
        return obj.get_absolute_url()


class MajorSitemap(SafiranSitemap):
    changefreq = "monthly"
    priority = 0.8

    def items(self):
        return Major.objects.filter(is_active=True).only("slug").order_by("order", "id")

    def location(self, obj):
        return reverse("major_details", kwargs={"slug": obj.slug})

    def priority(self, obj):
        from .gsc_indexing import gsc_boost_priority

        return gsc_boost_priority(obj.slug, kind="majors", default=0.8)


class FAQDetailSitemap(SafiranSitemap):
    changefreq = "monthly"
    priority = 0.72

    def items(self):
        return (
            FAQ.objects.filter(is_active=True)
            .select_related("category")
            .only("slug", "category_id")
            .order_by("order", "id")
        )

    def location(self, obj):
        return reverse("faq_detail", kwargs={"faq_slug": obj.slug})


class AchievementDetailSitemap(SafiranSitemap):
    changefreq = "monthly"
    priority = 0.74

    def items(self):
        return (
            MonthlyAchievement.objects.filter(is_active=True)
            .only("slug", "created_at")
            .order_by("-created_at")
        )

    def location(self, obj):
        return reverse("achievement_detail", kwargs={"achievement_slug": obj.slug})

    def lastmod(self, obj):
        return obj.created_at


class FAQCategorySitemap(SafiranSitemap):
    changefreq = "weekly"
    priority = 0.82

    def items(self):
        return FAQCategory.objects.filter(is_active=True).only("slug").order_by("order", "id")

    def location(self, obj):
        return reverse("faq_category", kwargs={"category_slug": obj.slug})


class ServiceCategorySitemap(SafiranSitemap):
    changefreq = "weekly"
    priority = 0.84

    def items(self):
        return ServiceCategory.objects.filter(is_active=True).only("slug").order_by("order", "id")

    def location(self, obj):
        return reverse("services_category", kwargs={"category_slug": obj.slug})


class CountrySitemap(SafiranSitemap):
    changefreq = "weekly"
    priority = 0.86

    def items(self):
        return list(
            StudyCountry.objects.filter(is_active=True)
            .only("code")
            .order_by("order", "id")
        )

    def location(self, obj):
        return reverse("country_detail", kwargs={"country_code": obj.code})


class CountryScholarshipSitemap(SafiranSitemap):
    """صفحات بورسیه هر کشور — به تفکیک مقطع (در صورت وجود راهنمای فعال)."""

    changefreq = "weekly"
    priority = 0.83

    def items(self):
        return (
            CountryScholarshipGuide.objects.filter(
                is_active=True,
                country__is_active=True,
            )
            .select_related("country")
            .only("target_degree", "updated_at", "country__code")
            .order_by("country__order", "country_id", "target_degree")
        )

    def location(self, obj):
        return obj.get_absolute_url()

    def lastmod(self, obj):
        return obj.updated_at


class TeamMemberSitemap(SafiranSitemap):
    changefreq = "monthly"
    priority = 0.7

    def items(self):
        return TeamMember.objects.filter(is_active=True).only("pk").order_by("order", "id")

    def location(self, obj):
        return reverse("team_member_detail", kwargs={"pk": obj.pk})
