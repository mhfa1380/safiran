"""
فید RSS وبلاگ — برای خزنده‌ها، خبرخوان‌ها و مدل‌های زبانی.
"""
from __future__ import annotations

import html
from xml.etree.ElementTree import Element, SubElement, tostring

from django.utils import timezone
from django.utils.feedgenerator import rfc2822_date

from .ai_discovery import resolve_site_url


def build_blog_rss_xml(*, request=None) -> str:
    from .models import BlogPost

    site = resolve_site_url(request)
    institute_name = "موسسه سفیران آینده روشن"
    try:
        from .cache_utils import get_institute_cached

        institute_name = getattr(get_institute_cached(), "name", "") or institute_name
    except Exception:
        pass

    channel_title = f"وبلاگ مهاجرت تحصیلی | {institute_name}"
    channel_link = f"{site}/blog/"
    channel_desc = (
        f"اخبار، راهنما و مطالب تخصصی مهاجرت تحصیلی، ویزا، بورسیه و اعزام دانشجو — "
        f"{institute_name}"
    )

    rss = Element("rss", version="2.0")
    rss.set("xmlns:atom", "http://www.w3.org/2005/Atom")
    channel = SubElement(rss, "channel")
    SubElement(channel, "title").text = channel_title
    SubElement(channel, "link").text = channel_link
    SubElement(channel, "description").text = channel_desc
    SubElement(channel, "language").text = "fa-IR"
    SubElement(channel, "lastBuildDate").text = rfc2822_date(timezone.now())
    atom_link = SubElement(channel, "{http://www.w3.org/2005/Atom}link")
    atom_link.set("href", f"{site}/blog/feed.xml")
    atom_link.set("rel", "self")
    atom_link.set("type", "application/rss+xml")

    posts = (
        BlogPost.objects.filter(is_published=True)
        .select_related("author")
        .order_by("-created_at")[:40]
    )
    for post in posts:
        item = SubElement(channel, "item")
        SubElement(item, "title").text = post.title
        link = f"{site}/blog/{post.slug}/"
        SubElement(item, "link").text = link
        guid = SubElement(item, "guid")
        guid.text = link
        guid.set("isPermaLink", "true")
        pub = post.created_at
        if timezone.is_naive(pub):
            pub = timezone.make_aware(pub, timezone.get_current_timezone())
        SubElement(item, "pubDate").text = rfc2822_date(pub)
        body = post.excerpt or post.content
        from django.utils.html import strip_tags

        plain = strip_tags(body or "")
        SubElement(item, "description").text = html.escape(plain[:500])
        if post.author_id and getattr(post, "author", None):
            SubElement(item, "author").text = getattr(post.author, "name", "") or institute_name
        if post.country_tag:
            SubElement(item, "category").text = post.country_tag

    xml_bytes = tostring(rss, encoding="utf-8", xml_declaration=True)
    return xml_bytes.decode("utf-8")
