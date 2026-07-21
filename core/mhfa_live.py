"""MHFA Live panel integration (https://live.mhfa.ir)."""

from __future__ import annotations

import logging
import re
import time
from typing import Any, Optional
from urllib.parse import quote

import requests
from django.conf import settings
from django.core.cache import cache
from django.utils.html import escape, format_html

logger = logging.getLogger(__name__)

_FOOTER_CACHE_PREFIX = "mhfa_footer_payload:"
_FOOTER_HTML_CACHE_PREFIX = "mhfa_footer_html:"
_FOOTER_STALE_CACHE_PREFIX = "mhfa_footer_stale:"
_FOOTER_MISS_SENTINEL = "__mhfa_footer_miss__"
_FOOTER_STALE_CACHE_TIMEOUT = 60 * 60 * 24 * 30  # ۳۰ روز — فقط برای fallback
_FOOTER_NEGATIVE_CACHE_SECONDS = 900  # ۱۵ دقیقه — جلوگیری از درخواست تکراری به API قطع
_FOOTER_REFRESH_LOCK_PREFIX = "mhfa_footer_refresh_lock:"
_FOOTER_REFRESH_LOCK_SECONDS = 120
_SCRIPT_TAG_RE = re.compile(r"<script\b[^>]*>.*?</script>", re.IGNORECASE | re.DOTALL)
_IFRAME_TAG_RE = re.compile(r"<iframe\b[^>]*>.*?</iframe>", re.IGNORECASE | re.DOTALL)
_INLINE_EVENT_RE = re.compile(r"\s+on\w+\s*=\s*(['\"]).*?\1", re.IGNORECASE | re.DOTALL)
_JAVASCRIPT_URI_RE = re.compile(r"javascript:", re.IGNORECASE)


def is_inbox_configured() -> bool:
    return bool(
        getattr(settings, "MHFA_LIVE_ENABLED", False)
        and getattr(settings, "MHFA_PANEL_URL", "")
        and getattr(settings, "MHFA_SITE_SLUG", "")
        and getattr(settings, "MHFA_INBOX_TOKEN", "")
    )


def _panel_url(path: str) -> str:
    base = str(getattr(settings, "MHFA_PANEL_URL", "https://live.mhfa.ir")).rstrip("/")
    if not path.startswith("/"):
        path = f"/{path}"
    return f"{base}{path}"


def _footer_cache_timeout() -> int:
    return int(getattr(settings, "MHFA_FOOTER_CACHE_SECONDS", 86400))


def _footer_cache_keys(key: str) -> tuple[str, str]:
    slug = (key or "default").strip() or "default"
    return (
        f"{_FOOTER_CACHE_PREFIX}{slug}",
        f"{_FOOTER_STALE_CACHE_PREFIX}{slug}",
    )


def _footer_api_url(key: str) -> str:
    path = "/api/v1/public/footer/"
    slug = (key or "default").strip() or "default"
    if slug != "default":
        path = f"{path}{quote(slug, safe='')}/"
    return _panel_url(path)


def _footer_fetch_timeout() -> int:
    return int(getattr(settings, "MHFA_FOOTER_FETCH_TIMEOUT_SECONDS", 2))


def _fetch_footer_payload(key: str) -> Optional[dict[str, Any]]:
    if not getattr(settings, "MHFA_PANEL_URL", ""):
        return None
    timeout = _footer_fetch_timeout()
    try:
        response = requests.get(_footer_api_url(key), timeout=timeout)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, dict):
            return data
    except Exception as exc:  # noqa: BLE001
        logger.warning("MHFA Live footer fetch failed: %s", exc)
    return None


def _footer_html_cache_key(key: str) -> str:
    slug = (key or "default").strip() or "default"
    return f"{_FOOTER_HTML_CACHE_PREFIX}{slug}"


def _store_footer_cache(key: str, payload: dict[str, Any]) -> str:
    cache_key, stale_key = _footer_cache_keys(key)
    html = _build_footer_html(payload)
    ttl = _footer_cache_timeout()
    cache.set(cache_key, payload, ttl)
    cache.set(_footer_html_cache_key(key), html, ttl)
    cache.set(stale_key, payload, _FOOTER_STALE_CACHE_TIMEOUT)
    return html


def _refresh_lock_key(key: str) -> str:
    slug = (key or "default").strip() or "default"
    return f"{_FOOTER_REFRESH_LOCK_PREFIX}{slug}"


def _footer_refresh_job(key: str) -> None:
    """واکشی footer با آزادسازی قفل — برای thread و Celery."""
    try:
        refresh_footer_cache_sync(key)
    finally:
        cache.delete(_refresh_lock_key(key))


def _schedule_footer_refresh(key: str) -> None:
    """واکشی footer فقط در پس‌زمینه — هرگز در مسیر HTTP هم‌زمان نیست."""
    lock_key = _refresh_lock_key(key)
    if cache.get(lock_key):
        return
    cache.set(lock_key, 1, _FOOTER_REFRESH_LOCK_SECONDS)

    from core.task_queue import enqueue_mhfa_footer_refresh

    enqueue_mhfa_footer_refresh(key)


def warm_footer_cache_async() -> None:
    """پیش‌واکشی هنگام بالا آمدن سرور (اختیاری)."""
    if not getattr(settings, "MHFA_FOOTER_ENABLED", False):
        return
    key = str(getattr(settings, "MHFA_FOOTER_KEY", "default")).strip() or "default"
    _schedule_footer_refresh(key)


def _sanitize_footer_html(raw: str) -> str:
    """پاک‌سازی سبک HTML پنل — جلوگیری از اسکریپت و handlerهای خطرناک."""
    if not raw:
        return ""
    cleaned = str(raw)
    cleaned = _SCRIPT_TAG_RE.sub("", cleaned)
    cleaned = _IFRAME_TAG_RE.sub("", cleaned)
    cleaned = _INLINE_EVENT_RE.sub("", cleaned)
    cleaned = _JAVASCRIPT_URI_RE.sub("", cleaned)
    return cleaned.strip()


def _build_footer_html(data: dict[str, Any]) -> str:
    parts: list[str] = []
    title = (data.get("title") or "").strip()
    if title:
        parts.append(f'<p class="mhfa-footer-title m-0">{escape(title)}</p>')
    text_html = data.get("text_html")
    if text_html:
        parts.append(_sanitize_footer_html(str(text_html)))
    link_url = (data.get("link_url") or "").strip()
    link_label = (data.get("link_label") or "").strip()
    if link_url and link_label:
        parts.append(
            str(
                format_html(
                    ' <a href="{}" class="company-link" rel="noopener noreferrer">{}</a>',
                    link_url,
                    link_label,
                )
            )
        )
    return "".join(parts)


def refresh_footer_cache_sync(key: str | None = None) -> bool:
    """واکشی هم‌زمان footer (برای cron روزانه) — در صورت خطا False، سایت را متوقف نمی‌کند."""
    key = (key or getattr(settings, "MHFA_FOOTER_KEY", "default") or "default").strip() or "default"
    try:
        payload = _fetch_footer_payload(key)
        if payload:
            _store_footer_cache(key, payload)
            return True
        cache_key, stale_key = _footer_cache_keys(key)
        cache.set(cache_key, _FOOTER_MISS_SENTINEL, _FOOTER_NEGATIVE_CACHE_SECONDS)
        stale = cache.get(stale_key)
        if isinstance(stale, dict):
            cache.set(
                _footer_html_cache_key(key),
                _build_footer_html(stale),
                _FOOTER_NEGATIVE_CACHE_SECONDS,
            )
    except Exception as exc:  # noqa: BLE001
        logger.exception("MHFA footer sync refresh failed: %s", exc)
    return False


def get_central_footer_html() -> str:
    """Footer متمرکز پنل MHFA — کش روزانه؛ بدون انتظار برای API در هر کلیک."""
    try:
        if not getattr(settings, "MHFA_FOOTER_ENABLED", False):
            return ""

        key = str(getattr(settings, "MHFA_FOOTER_KEY", "default")).strip() or "default"
        html_key = _footer_html_cache_key(key)
        cached_html = cache.get(html_key)
        if cached_html:
            return str(cached_html)

        cache_key, stale_key = _footer_cache_keys(key)
        cached = cache.get(cache_key)

        if cached == _FOOTER_MISS_SENTINEL:
            stale = cache.get(stale_key)
            if isinstance(stale, dict):
                return _build_footer_html(stale)
            _schedule_footer_refresh(key)
            return ""

        if isinstance(cached, dict):
            html = _build_footer_html(cached)
            cache.set(html_key, html, _footer_cache_timeout())
            return html

        stale = cache.get(stale_key)
        if isinstance(stale, dict):
            html = _build_footer_html(stale)
            cache.set(html_key, html, _FOOTER_NEGATIVE_CACHE_SECONDS)
            _schedule_footer_refresh(key)
            return html

        _schedule_footer_refresh(key)
        return ""
    except Exception as exc:  # noqa: BLE001
        logger.exception("MHFA footer render failed: %s", exc)
        return ""


def _inbox_retry_attempts() -> int:
    return max(1, int(getattr(settings, "MHFA_INBOX_RETRY_MAX_ATTEMPTS", 3)))


def _inbox_retry_base_delay() -> float:
    return max(0.5, float(getattr(settings, "MHFA_INBOX_RETRY_DELAY_SECONDS", 2)))


def _post_inbox_once(payload: dict[str, Any], headers: dict[str, str], timeout: int) -> bool:
    try:
        response = requests.post(
            _panel_url("/api/v1/public/contact/"),
            json=payload,
            headers=headers,
            timeout=timeout,
        )
        if response.status_code == 200 and response.json().get("ok"):
            return True
        logger.warning(
            "MHFA Live inbox rejected event (status=%s): %s",
            response.status_code,
            response.text[:300],
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("MHFA Live inbox request failed: %s", exc)
    return False


def deliver_inbox_event(payload: dict[str, Any]) -> bool:
    """ارسال رویداد به inbox MHFA با retry — برای Celery و حالت sync."""
    if not is_inbox_configured():
        return False

    headers = {
        "Content-Type": "application/json",
        "X-Inbox-Token": str(getattr(settings, "MHFA_INBOX_TOKEN", "")),
        "Origin": str(getattr(settings, "SITE_URL", "")).rstrip("/"),
    }
    timeout = int(getattr(settings, "MHFA_LIVE_TIMEOUT_SECONDS", 8))
    attempts = _inbox_retry_attempts()
    base_delay = _inbox_retry_base_delay()

    for attempt in range(1, attempts + 1):
        if _post_inbox_once(payload, headers, timeout):
            if attempt > 1:
                logger.info("MHFA Live inbox succeeded on attempt %s/%s", attempt, attempts)
            return True
        if attempt < attempts:
            wait = base_delay * attempt
            logger.warning(
                "MHFA Live inbox retry in %.1fs (attempt %s/%s)",
                wait,
                attempt,
                attempts,
            )
            time.sleep(wait)
    return False


def post_inbox_event(
    *,
    name: str,
    message: str,
    subject: str = "contact",
    email: str = "",
    phone: str = "",
    source_slug: Optional[str] = None,
) -> bool:
    """Forward an event to MHFA Live public inbox (never raises). Retries on failure."""
    if not is_inbox_configured():
        return False

    payload: dict[str, Any] = {
        "name": (name or "").strip() or "—",
        "email": (email or "").strip(),
        "phone": (phone or "").strip(),
        "subject": (subject or "contact").strip() or "contact",
        "message": (message or "").strip() or "—",
        "source_slug": (source_slug or getattr(settings, "MHFA_SITE_SLUG", "")).strip(),
    }

    from core.task_queue import celery_enabled, enqueue_mhfa_inbox

    if celery_enabled():
        enqueue_mhfa_inbox(payload)
        return True

    return deliver_inbox_event(payload)
