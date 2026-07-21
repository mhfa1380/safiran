"""
View برای robots.txt — راهنمای خزنده‌های موتورهای جستجو و هوش مصنوعی.
"""
from django.conf import settings
from django.http import HttpResponse

# خزنده‌های رایج مدل‌های زبانی — همان قوانین User-agent: * (بدون مسدودسازی)
_AI_CRAWLER_AGENTS = (
    "GPTBot",
    "OAI-SearchBot",
    "ChatGPT-User",
    "ClaudeBot",
    "anthropic-ai",
    "Google-Extended",
    "PerplexityBot",
    "Applebot-Extended",
    "Bytespider",
    "CCBot",
    "cohere-ai",
    "FacebookBot",
    "meta-externalagent",
)


def robots_txt(request):
    """فایل robots.txt برای گوگل، موتورهای جستجو و خزنده‌های هوش مصنوعی."""
    site_url = getattr(settings, "SITE_URL", "").rstrip("/")
    if not site_url:
        site_url = f"{request.scheme}://{request.get_host()}"
    sitemap_url = f"{site_url}/sitemap.xml"
    llms_url = f"{site_url}/llms.txt"
    ai_index_url = f"{site_url}/ai-index.json"
    blog_rss_url = f"{site_url}/blog/feed.xml"
    ai_agent_blocks = "\n".join(
        f"User-agent: {agent}\nAllow: /\n" for agent in _AI_CRAWLER_AGENTS
    )
    content = f"""User-agent: *
Allow: /

# خزنده‌های هوش مصنوعی — دسترسی آزاد به محتوای عمومی (مثل موتورهای جستجو)
{ai_agent_blocks}
# نقشهٔ محتوا برای مدل‌های زبانی: {llms_url}
# فهرست ماشین‌خوان: {ai_index_url}
# فید وبلاگ: {blog_rss_url}

# مسیرهای غیرمجاز برای ایندکس
Disallow: /admin/
Disallow: /admin/ckeditor-upload/
Disallow: /ckeditor-upload/
Disallow: /api/
Disallow: /elements/
Disallow: /appointment/slots/
Disallow: /quick-consultation/
Disallow: /pricing/calculate/
Disallow: /achievements/search/
Disallow: /achievements/suggest/
Disallow: /country/*/search/
Disallow: /country/*/suggest/
Disallow: /majors/search/
Disallow: /majors/suggest/
Disallow: /services/search/
Disallow: /services/suggest/
Disallow: /services/track/
Disallow: /faq/search/
Disallow: /faq/suggest/
Disallow: /faq/track/
Disallow: /search/suggest/
Disallow: /ارزیابی-مهاجرت/majors/suggest/
Disallow: /ارزیابی-مهاجرت/نتیجه/
Disallow: /ارزیابی-مهاجرت/process/
Disallow: /ارزیابی-مهاجرت/submit/

# جلوگیری از ایندکس نسخه‌های فیلتر/جستجو
Disallow: /*?q=
Disallow: /*?tag=
Disallow: /*?page=
Disallow: /*?country=
Disallow: /*?university=
Disallow: /*?major=
Disallow: /*?about=
Disallow: /*?ref=

Sitemap: {sitemap_url}
"""
    return HttpResponse(content, content_type="text/plain; charset=utf-8")
