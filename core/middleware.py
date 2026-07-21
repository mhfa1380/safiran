"""میان‌افزارهای بهینه‌سازی درخواست و مدیریت خطای دیتابیس."""

import logging
import time
from urllib.parse import urlparse

from django.conf import settings
from django.db import close_old_connections
from django.http import HttpResponsePermanentRedirect
from django.db.utils import DatabaseError, OperationalError
from django.http import HttpResponse
from django.shortcuts import render

from .sqlite_db import (
    close_all_connections,
    is_retryable_db_error,
    retry_attempts,
    retry_delay_before_attempt,
    uses_sqlite,
)

logger = logging.getLogger(__name__)

_LOCAL_DEV_HOSTS = frozenset({"127.0.0.1", "localhost"})


class GscLegacyRedirectMiddleware:
    """ریدایرکت ۳۰۱ اسلاگ‌های قدیمی GSC (ubc، medicine، … و دانشگاه‌های -2)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        from .gsc_redirects import try_gsc_legacy_redirect

        redirect = try_gsc_legacy_redirect(request)
        if redirect is not None:
            return redirect
        return self.get_response(request)


class CanonicalHostMiddleware:
    """
    ریدایرکت ۳۰۱ به دامنهٔ canonical (SITE_URL) — یکپارچه‌سازی www و apex برای GSC.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        raw = (getattr(settings, "SITE_URL", None) or "").strip().rstrip("/")
        parsed = urlparse(raw if "://" in raw else (f"https://{raw}" if raw else ""))
        self.canonical_host = (parsed.netloc or "").lower()
        self.canonical_scheme = parsed.scheme or "https"

    def __call__(self, request):
        if not self.canonical_host:
            return self.get_response(request)
        host = (request.get_host() or "").split(":")[0].lower()
        if not host or host in _LOCAL_DEV_HOSTS or host == self.canonical_host:
            return self.get_response(request)
        target = f"{self.canonical_scheme}://{self.canonical_host}{request.get_full_path()}"
        return HttpResponsePermanentRedirect(target)


class FreshnessHeadersMiddleware:
    """
    هدرهای شفاف برای مرورگر — فرم‌ها بدون کش، API جستجو کوتاه‌مدت.
    """

    _NO_STORE_PREFIXES = (
        "/رزرو-مشاوره/",
        "/تماس-با-ما/",
        "/ارزیابی-مهاجرت/",
        "/appointment/",
        "/evaluation/",
        "/تماس-با-ما/",
        "/pricing/calculate/",
        "/admin/",
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if "Cache-Control" in response:
            return response
        path = request.path
        if any(path.startswith(p) for p in self._NO_STORE_PREFIXES):
            response["Cache-Control"] = "no-store, max-age=0"
            return response
        if path.endswith("/search/") or "/suggest/" in path or path.endswith("/track/"):
            response["Cache-Control"] = "private, max-age=0, must-revalidate"
            return response
        if request.method == "GET" and response.status_code == 200:
            from .cache_utils import page_cache_seconds

            ttl = page_cache_seconds()
            if ttl > 0:
                response["Cache-Control"] = f"private, max-age={ttl}, stale-while-revalidate=30"
        return response


class DatabaseConnectionMiddleware:
    """
    بستن اتصال‌های کهنه قبل و بعد از هر درخواست — کاهش احتمال قفل SQLite.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        close_old_connections()
        try:
            return self.get_response(request)
        finally:
            close_old_connections()
            if uses_sqlite():
                close_all_connections()


class DatabaseErrorMiddleware:
    """
    هندل امن خطاهای دیتابیس (قفل SQLite، busy) با تلاش مجدد نمایی قبل از 503.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        max_attempts = retry_attempts()
        last_exc: BaseException | None = None
        for attempt in range(max_attempts):
            try:
                close_old_connections()
                return self.get_response(request)
            except (OperationalError, DatabaseError) as exc:
                last_exc = exc
                if not is_retryable_db_error(exc):
                    raise
                if attempt >= max_attempts - 1:
                    break
                close_all_connections()
                delay = retry_delay_before_attempt(attempt)
                logger.warning(
                    "Database busy, retry %s/%s path=%s in %.2fs: %s",
                    attempt + 1,
                    max_attempts,
                    request.path,
                    delay,
                    exc,
                )
                time.sleep(delay)

        logger.error("Database error on %s after %s attempts: %s", request.path, max_attempts, last_exc)
        return self._service_unavailable(request, retry_after=15)

    def _wants_json_response(self, request) -> bool:
        path = request.path
        if path.startswith("/api/"):
            return True
        if path.endswith("/submit/") or path.endswith("/process/"):
            return True
        accept = (request.META.get("HTTP_ACCEPT") or "").lower()
        if "application/json" in accept:
            return True
        return request.META.get("HTTP_X_REQUESTED_WITH") == "XMLHttpRequest"

    def _service_unavailable(self, request, *, retry_after: int = 15):
        if self._wants_json_response(request):
            response = HttpResponse(
                '{"ok": false, "error": "سرویس موقتاً در دسترس نیست. لطفاً چند ثانیه بعد تلاش کنید.", "retryable": true, "status": "running"}',
                status=503,
                content_type="application/json; charset=utf-8",
            )
        else:
            try:
                response = render(
                    request,
                    "503.html",
                    {"retry_after": retry_after},
                    status=503,
                )
            except Exception:
                response = HttpResponse(
                    "سرویس موقتاً در دسترس نیست. لطفاً چند ثانیه بعد تلاش کنید.",
                    status=503,
                    content_type="text/plain; charset=utf-8",
                )
        response["Retry-After"] = str(retry_after)
        return response
