"""
اعتبارسنجی JSON-LD و هم‌خوانی FAQPage با بلوک‌های Q&A visible.

  python manage.py validate_google_ai_schema
  python manage.py validate_google_ai_schema --live
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.management.base import BaseCommand
from django.test import RequestFactory
from django.urls import reverse


@dataclass
class CheckResult:
    label: str
    ok: bool
    detail: str = ""


@dataclass
class ValidationReport:
    results: list[CheckResult] = field(default_factory=list)

    def add(self, label: str, ok: bool, detail: str = "") -> None:
        self.results.append(CheckResult(label=label, ok=ok, detail=detail))

    @property
    def passed(self) -> bool:
        return all(r.ok for r in self.results)


def _extract_faq_from_graph(graph: list[dict[str, Any]]) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for node in graph:
        if node.get("@type") != "FAQPage":
            continue
        for entity in node.get("mainEntity") or []:
            answer = entity.get("acceptedAnswer") or {}
            items.append(
                {
                    "question": (entity.get("name") or "").strip(),
                    "short_answer": (answer.get("text") or "").strip(),
                }
            )
    return items


def _validate_schema_json(
    report: ValidationReport,
    *,
    label: str,
    schema_json: str,
    qa_blocks: list[dict[str, str]] | None,
) -> dict[str, Any] | None:
    try:
        data = json.loads(schema_json)
    except json.JSONDecodeError as exc:
        report.add(f"{label}: JSON", False, str(exc))
        return None

    report.add(f"{label}: JSON", True)
    graph = data.get("@graph")
    if not isinstance(graph, list) or not graph:
        report.add(f"{label}: @graph", False, "گراف schema خالی یا نامعتبر است")
        return data

    report.add(f"{label}: @graph", True, f"{len(graph)} node")
    has_web = any(
        n.get("@type") in ("WebPage", "BlogPosting", "AboutPage") or "WebPage" in (n.get("@type") or [])
        for n in graph
    )
    report.add(f"{label}: page node", has_web, "WebPage/BlogPosting یافت نشد" if not has_web else "")

    if qa_blocks:
        schema_faq = _extract_faq_from_graph(graph)
        if not schema_faq:
            report.add(f"{label}: FAQPage", False, "بلوک Q&A داریم ولی FAQPage در schema نیست")
        else:
            expected = [
                {"question": b["question"], "short_answer": b["short_answer"]}
                for b in qa_blocks
                if b.get("question") and b.get("short_answer")
            ]
            match = schema_faq[: len(expected)] == expected
            report.add(
                f"{label}: FAQ هم‌خوان",
                match,
                f"schema={len(schema_faq)} visible={len(expected)}"
                if not match
                else f"{len(expected)} سوال",
            )
    return data


def _validate_live_page(report: ValidationReport, url: str) -> None:
    try:
        req = Request(url, headers={"User-Agent": "SafiranSchemaValidator/1.0"})
        with urlopen(req, timeout=20) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except URLError as exc:
        report.add(f"live: {url}", False, str(exc.reason if hasattr(exc, "reason") else exc))
        return

    blocks = re.findall(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html,
        flags=re.DOTALL | re.IGNORECASE,
    )
    if not blocks:
        report.add(f"live: {url}", False, "هیچ application/ld+json یافت نشد")
        return

    parsed = 0
    for block in blocks:
        try:
            json.loads(block.strip())
            parsed += 1
        except json.JSONDecodeError:
            report.add(f"live: {url}", False, "JSON-LD نامعتبر در HTML")
            return

    has_faq = "FAQPage" in html or '"@type": "FAQPage"' in html or '"@type":"FAQPage"' in html
    report.add(
        f"live: {url}",
        True,
        f"{parsed} بلوک JSON-LD" + (" + FAQPage" if has_faq else ""),
    )


class Command(BaseCommand):
    help = "اعتبارسنجی schema و FAQPage برای صفحات Google AI"

    def add_arguments(self, parser):
        parser.add_argument(
            "--live",
            action="store_true",
            help="درخواست HTTP به SITE_URL و بررسی JSON-LD در HTML",
        )

    def handle(self, *args, **options):
        from core.about_seo import build_about_page_seo
        from core.blog_seo import build_blog_post_seo
        from core.country_seo import build_country_page_seo
        from core.country_scholarship_seo import build_country_scholarship_seo
        from core.google_ai_seo import build_pricing_ai_qa_blocks
        from core.major_seo import build_major_page_seo
        from core.models import BlogPost, Major, StudyCountry, University
        from core.models import CountryScholarshipGuide
        from core.pricing_seo import build_pricing_page_seo
        from core.service_seo import build_services_page_seo
        from core.university_seo import build_university_page_seo
        from core.cache_utils import (
            get_institute_cached,
            get_pricing_page_data_cached,
            get_service_categories_cached,
        )
        from core.service_search import filter_services

        report = ValidationReport()
        site_url = getattr(settings, "SITE_URL", "").rstrip("/") or "https://www.saroshan.ir"
        institute = get_institute_cached()
        institute_name = getattr(institute, "name", "") or "موسسه"
        factory = RequestFactory()
        request = factory.get("/")

        sample_urls: list[tuple[str, str]] = [("صفحه اصلی", f"{site_url}/")]

        country = StudyCountry.objects.filter(is_active=True).first()
        if country:
            seo = build_country_page_seo(
                request=request,
                country=country,
                institute_name=institute_name,
                site_url=site_url,
            )
            _validate_schema_json(
                report,
                label=f"کشور ({country.code})",
                schema_json=seo["country_schema_json"],
                qa_blocks=seo["country_ai_qa_blocks"],
            )
            sample_urls.append(("کشور", seo["country_page_url"]))

            guide = (
                CountryScholarshipGuide.objects.filter(country=country, is_active=True)
                .prefetch_related("scholarships")
                .first()
            )
            if guide:
                scholarships = list(guide.scholarships.filter(is_active=True).order_by("-is_featured", "order", "id"))
                schol_seo = build_country_scholarship_seo(
                    request=request,
                    country=country,
                    guide=guide,
                    scholarships=scholarships,
                    institute_name=institute_name,
                    site_url=site_url,
                )
                _validate_schema_json(
                    report,
                    label=f"بورسیه ({country.code})",
                    schema_json=schol_seo["scholarship_schema_json"],
                    qa_blocks=schol_seo["scholarship_ai_qa_blocks"],
                )
                sample_urls.append(("بورسیه", schol_seo["scholarship_page_url"]))

        major = Major.objects.filter(is_active=True).first()
        if major:
            major_faqs = list(major.faqs.filter(is_active=True).order_by("order", "id"))
            canonical = f"{site_url}{reverse('major_details', kwargs={'slug': major.slug})}"
            major_seo = build_major_page_seo(
                major=major,
                major_faqs=major_faqs,
                linked_universities=[],
                linked_universities_count=0,
                site_url=site_url,
                canonical_url=canonical,
                institute_name=institute_name,
            )
            _validate_schema_json(
                report,
                label="رشته",
                schema_json=major_seo["major_schema_json"],
                qa_blocks=major_seo["major_ai_qa_blocks"],
            )
            sample_urls.append(("رشته", canonical))

        university = University.objects.first()
        if university:
            canonical = f"{site_url}{reverse('school_detail', kwargs={'slug': university.slug})}"
            uni_seo = build_university_page_seo(
                university=university,
                university_faqs=list(university.faqs.filter(is_active=True).order_by("order", "id")),
                linked_majors=[],
                site_url=site_url,
                canonical_url=canonical,
                institute_name=institute_name,
            )
            _validate_schema_json(
                report,
                label="دانشگاه",
                schema_json=uni_seo["university_schema_json"],
                qa_blocks=uni_seo["university_ai_qa_blocks"],
            )
            sample_urls.append(("دانشگاه", canonical))

        categories = get_service_categories_cached()
        services = list(filter_services())
        svc_seo = build_services_page_seo(
            request=request,
            institute_name=institute_name,
            active_category=None,
            categories=categories,
            services=services,
            site_url=site_url,
        )
        _validate_schema_json(
            report,
            label="خدمات",
            schema_json=svc_seo["services_schema_json"],
            qa_blocks=svc_seo["services_ai_qa_blocks"],
        )
        sample_urls.append(("خدمات", svc_seo["services_page_url"]))

        pricing_data = get_pricing_page_data_cached()
        pricing_seo = build_pricing_page_seo(
            request=request,
            institute_name=institute_name,
            site_url=site_url,
            tariffs=pricing_data["tariffs"],
        )
        _validate_schema_json(
            report,
            label="تعرفه",
            schema_json=pricing_seo["pricing_schema_json"],
            qa_blocks=pricing_seo["pricing_ai_qa_blocks"],
        )
        sample_urls.append(("تعرفه", pricing_seo["pricing_page_url"]))

        about_seo = build_about_page_seo(
            institute=institute,
            site_url=site_url,
            canonical_url=f"{site_url}{reverse('about')}",
        )
        _validate_schema_json(
            report,
            label="درباره ما",
            schema_json=about_seo["about_schema_json"],
            qa_blocks=about_seo["about_ai_qa_blocks"],
        )
        sample_urls.append(("درباره ما", f"{site_url}{reverse('about')}"))

        post = BlogPost.objects.filter(is_published=True).select_related("author").first()
        if post:
            blog_seo = build_blog_post_seo(
                post=post,
                site_url=site_url,
                canonical_url=f"{site_url}{reverse('blog_detail', kwargs={'slug': post.slug})}",
                institute_name=institute_name,
                org_schema_id=f"{site_url}/#organization",
                static_logo_path="/static/img/logo.png",
            )
            _validate_schema_json(
                report,
                label="وبلاگ",
                schema_json=blog_seo["blog_schema_json"],
                qa_blocks=blog_seo["blog_ai_qa_blocks"],
            )
            sample_urls.append(("وبلاگ", f"{site_url}{reverse('blog_detail', kwargs={'slug': post.slug})}"))

        # pricing blocks sanity
        pricing_blocks = build_pricing_ai_qa_blocks(institute_name)
        report.add("تعرفه: بلوک Q&A", len(pricing_blocks) >= 3, f"{len(pricing_blocks)} سوال")

        self.stdout.write("")
        self.stdout.write("=== اعتبارسنجی Google AI Schema ===")
        for item in report.results:
            style = self.style.SUCCESS if item.ok else self.style.ERROR
            suffix = f" — {item.detail}" if item.detail else ""
            self.stdout.write(style(f"{'OK' if item.ok else 'FAIL'}  {item.label}{suffix}"))

        self.stdout.write("")
        self.stdout.write("=== نمونه URL برای Rich Results Test ===")
        self.stdout.write(f"https://search.google.com/test/rich-results")
        for label, url in sample_urls:
            self.stdout.write(f"  [{label}] {url}")

        if options["live"]:
            self.stdout.write("")
            self.stdout.write("=== بررسی زنده HTML ===")
            for label, url in sample_urls[:6]:
                _validate_live_page(report, url)

        self.stdout.write("")
        self.stdout.write("=== خلاصه ===")
        if report.passed:
            self.stdout.write(self.style.SUCCESS("همه بررسی‌ها موفق بود."))
        else:
            self.stdout.write(self.style.ERROR("برخی بررسی‌ها ناموفق بود."))
            raise SystemExit(1)
