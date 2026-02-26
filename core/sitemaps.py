"""
Sitemap برای بهبود ایندکس شدن سایت توسط موتورهای جستجو.
"""
from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from .models import BlogPost, Course, Major, University


class StaticViewSitemap(Sitemap):
    """صفحات استاتیک سایت."""
    protocol = "https"
    priority = 0.9
    changefreq = "weekly"

    def items(self):
        return [
            "index",
            "about",
            "contact",
            "blog",
            "majors",
            "courses_list",
            "services",
            "appointment",
            "evaluation",
            "faq",
            "schools_list",
        ]

    def location(self, item):
        return reverse(item)


class BlogPostSitemap(Sitemap):
    """پست‌های وبلاگ."""
    protocol = "https"
    changefreq = "monthly"
    priority = 0.8

    def items(self):
        return BlogPost.objects.filter(is_published=True)

    def location(self, obj):
        return reverse("blog_detail", kwargs={"slug": obj.slug})

    def lastmod(self, obj):
        return obj.updated_at


class UniversitySitemap(Sitemap):
    """صفحات دانشگاه‌ها."""
    protocol = "https"
    changefreq = "monthly"
    priority = 0.85

    def items(self):
        return University.objects.all()

    def location(self, obj):
        return reverse("school_detail", kwargs={"slug": obj.slug})


class CourseSitemap(Sitemap):
    """صفحات دوره‌ها."""
    protocol = "https"
    changefreq = "monthly"
    priority = 0.8

    def items(self):
        return Course.objects.all()

    def location(self, obj):
        return reverse("course_details", kwargs={"slug": obj.slug})


class MajorSitemap(Sitemap):
    """صفحات رشته‌ها."""
    protocol = "https"
    changefreq = "monthly"
    priority = 0.8

    def items(self):
        return Major.objects.all()

    def location(self, obj):
        return reverse("major_details", kwargs={"slug": obj.slug})
