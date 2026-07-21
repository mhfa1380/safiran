"""کش شمارش و پاسخ‌های browse برای لیست دانشگاه/رشته."""
from __future__ import annotations

from collections.abc import Callable

from django.core.cache import cache
from django.db.models import QuerySet

from .cache_utils import api_cache_key

BROWSE_COUNT_TTL = 300
BROWSE_API_TTL = 180


def browse_count_key(namespace: str, *parts: str) -> str:
    return api_cache_key(f"browse_count:{namespace}", *parts)


def cached_queryset_count(
    namespace: str,
    parts: tuple[str, ...],
    count_fn: Callable[[], int],
    *,
    ttl: int = BROWSE_COUNT_TTL,
) -> int:
    key = browse_count_key(namespace, *parts)
    hit = cache.get(key)
    if hit is not None:
        return int(hit)
    total = count_fn()
    cache.set(key, total, ttl)
    return total


def invalidate_browse_counts() -> None:
    """پس از seed یا ویرایش محتوا — نسخه کلید browse بالا می‌رود."""
    try:
        cache.incr("core:browse_count:ver", 1)
    except ValueError:
        cache.set("core:browse_count:ver", 2, None)


def _versioned_parts(*parts: str) -> tuple[str, ...]:
    ver = cache.get("core:browse_count:ver", 1)
    return (str(ver), *parts)


def count_for_queryset(namespace: str, parts: tuple[str, ...], qs: QuerySet) -> int:
    return cached_queryset_count(
        namespace,
        _versioned_parts(*parts),
        lambda: qs.count(),
    )
