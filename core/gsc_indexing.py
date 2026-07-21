"""
اولویت ایندکس صفحات GSC (Crawled/Discovered not indexed) — کش runtime.
"""
from __future__ import annotations

import json
from pathlib import Path

from django.core.cache import cache

_CACHE_FILE = (
    Path(__file__).resolve().parent / "seed_data" / "cache" / "gsc_not_indexed_slugs.json"
)
_RUNTIME_CACHE_KEY = "core:gsc_not_indexed_slugs:v1"
_RUNTIME_TTL = 3600


def _empty() -> dict[str, tuple[str, ...]]:
    return {"majors": (), "universities": (), "blogs": ()}


def get_gsc_not_indexed_slugs() -> dict[str, tuple[str, ...]]:
    """اسلاگ‌های not-indexed — از کش Django یا فایل JSON."""
    cached = cache.get(_RUNTIME_CACHE_KEY)
    if cached is not None:
        return cached

    if not _CACHE_FILE.is_file():
        result = _empty()
        cache.set(_RUNTIME_CACHE_KEY, result, _RUNTIME_TTL)
        return result

    try:
        data = json.loads(_CACHE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        result = _empty()
        cache.set(_RUNTIME_CACHE_KEY, result, 300)
        return result

    result = {
        "majors": tuple(data.get("majors") or ()),
        "universities": tuple(data.get("universities") or ()),
        "blogs": tuple(data.get("blogs") or ()),
    }
    cache.set(_RUNTIME_CACHE_KEY, result, _RUNTIME_TTL)
    return result


def gsc_boost_priority(slug: str, *, kind: str, default: float) -> float:
    """اولویت sitemap بالاتر برای URLهای not-indexed در GSC."""
    slugs = get_gsc_not_indexed_slugs()
    bucket = slugs.get(kind, ())
    if slug in bucket:
        return max(default, 0.88)
    return default


def invalidate_gsc_indexing_cache() -> None:
    cache.delete(_RUNTIME_CACHE_KEY)
