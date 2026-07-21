"""اصلاح لینک‌های قدیمی /ارزیابی/ در محتوای HTML رشته‌ها و دانشگاه‌ها."""
from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db.models import Q

from core.models import Major, University


def fix_evaluation_hrefs(html: str) -> tuple[str, bool]:
    if not html or "/ارزیابی" not in html:
        return html, False
    updated = html
    replacements = (
        ('href="/ارزیابی/"', 'href="/ارزیابی-مهاجرت/"'),
        ("href='/ارزیابی/'", "href='/ارزیابی-مهاجرت/'"),
        ('href="/ارزیابی?', 'href="/ارزیابی-مهاجرت?'),
        ("href='/ارزیابی?", "href='/ارزیابی-مهاجرت?"),
    )
    changed = False
    for old, new in replacements:
        if old in updated:
            updated = updated.replace(old, new)
            changed = True
    return updated, changed


class Command(BaseCommand):
    help = "Replace legacy /ارزیابی/ links in major/university HTML with /ارزیابی-مهاجرت/"

    def handle(self, *args, **options):
        major_qs = Major.objects.filter(
            Q(description__contains="/ارزیابی/") | Q(description__contains="/ارزیابی?")
        ).exclude(description__contains="/ارزیابی-مهاجرت")
        uni_qs = University.objects.filter(
            Q(description__contains="/ارزیابی/") | Q(description__contains="/ارزیابی?")
        ).exclude(description__contains="/ارزیابی-مهاجرت")

        major_n = uni_n = 0
        for major in major_qs.iterator(chunk_size=200):
            new_html, changed = fix_evaluation_hrefs(major.description)
            if changed:
                major.description = new_html
                major.save(update_fields=["description"])
                major_n += 1

        for uni in uni_qs.iterator(chunk_size=200):
            new_html, changed = fix_evaluation_hrefs(uni.description)
            if changed:
                uni.description = new_html
                uni.save(update_fields=["description"])
                uni_n += 1

        if major_n or uni_n:
            from core.cache_utils import invalidate_content_html_caches

            invalidate_content_html_caches()

        self.stdout.write(
            self.style.SUCCESS(f"Fixed majors: {major_n}, universities: {uni_n}")
        )
