"""
Viewهای کشف محتوا برای مدل‌های زبانی — llms.txt، JSON index و RSS.
"""
from django.core.cache import cache
from django.http import HttpResponse, HttpResponseRedirect
from .ai_discovery import (
    build_ai_index_json,
    build_llms_ctx_txt,
    build_llms_full_txt,
    build_llms_txt,
)
from .ai_feeds import build_blog_rss_xml
from .cache_utils import content_cache_version

_CACHE_SECONDS = 900
_CACHE_CONTROL = "public, max-age=900, must-revalidate"


def _cached_text(cache_key: str, builder, request) -> str:
    versioned_key = f"{cache_key}:c{content_cache_version()}"
    text = cache.get(versioned_key)
    if text is None:
        text = builder(request=request)
        cache.set(versioned_key, text, _CACHE_SECONDS)
    return text


def _plain_response(text: str) -> HttpResponse:
    response = HttpResponse(text, content_type="text/plain; charset=utf-8")
    response["Cache-Control"] = _CACHE_CONTROL
    response["X-Robots-Tag"] = "noindex"
    return response


def _json_response(text: str) -> HttpResponse:
    response = HttpResponse(text, content_type="application/json; charset=utf-8")
    response["Cache-Control"] = _CACHE_CONTROL
    response["X-Robots-Tag"] = "noindex"
    response["Access-Control-Allow-Origin"] = "*"
    return response


def llms_txt(request):
    return _plain_response(_cached_text("core:llms_txt", build_llms_txt, request))


def llms_full_txt(request):
    return _plain_response(_cached_text("core:llms_full_txt", build_llms_full_txt, request))


def llms_ctx_txt(request):
    return _plain_response(_cached_text("core:llms_ctx_txt", build_llms_ctx_txt, request))


def ai_index_json(request):
    return _json_response(_cached_text("core:ai_index_json", build_ai_index_json, request))


def blog_rss_feed(request):
    xml = _cached_text("core:blog_rss", build_blog_rss_xml, request)
    response = HttpResponse(xml, content_type="application/rss+xml; charset=utf-8")
    response["Cache-Control"] = _CACHE_CONTROL
    return response


def well_known_llms(request):
    """برخی agentها مسیر /.well-known/llms.txt را جستجو می‌کنند."""
    return HttpResponseRedirect("/llms.txt", permanent=True)
