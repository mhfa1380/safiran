"""
دریافت/تولید تصاویر برای دانشگاه‌ها، رشته‌ها و کشورهای مقصد هنگام seed.
"""
from __future__ import annotations

import hashlib
import io
import json
import logging
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import OperationalError, transaction
from django.db.models import Q
from PIL import Image, ImageDraw, ImageOps

from core.image_compression import compress_to_jpeg_bytes
from core.models import Major, StudyCountry, University, major_image_upload_to, university_image_upload_to
from core.seed_data.major_image_queries import (
    build_major_image_search_queries,
    build_wikipedia_fallback_query,
    build_wikipedia_query,
    is_acceptable_wikipedia_title,
)
from core.seed_data.university_image_queries import build_university_wikipedia_queries

logger = logging.getLogger(__name__)

WIKI_USER_AGENT = "SafiranStudyAbroadBot/1.0 (https://saroshan.ir; educational seed)"

COUNTRY_GRADIENTS: dict[str, tuple[tuple[int, int, int], tuple[int, int, int]]] = {
    "canada": ((180, 30, 40), (245, 245, 250)),
    "spain": ((200, 120, 20), (255, 240, 220)),
    "china": ((170, 30, 30), (255, 230, 200)),
}

COUNTRY_WIKI_LANDMARKS: dict[str, str] = {
    "canada": "Higher education in Canada",
    "spain": "Higher education in Spain",
    "china": "Higher education in China",
}

COUNTRY_SECTION_IMAGE_SLOTS = ("campus", "visa", "city")

_WIKI_RAW_CACHE: dict[str, bytes] = {}
_WIKI_SEARCH_LIST_CACHE: dict[str, list[bytes]] = {}
_USED_MAJOR_IMAGE_DIGESTS: set[str] = set()
_MAJOR_IMAGE_DIGEST_LOCK = threading.Lock()

MAJOR_COVER_SIZE = (1200, 675)  # 16:9 — کارت لیست، جزئیات، OG
MAJOR_IMAGE_MAX_BYTES = 480 * 1024

MAJOR_CATEGORY_COLORS: dict[str, tuple[tuple[int, int, int], tuple[int, int, int]]] = {
    "medical": ((20, 90, 160), (180, 220, 255)),
    "engineering": ((30, 80, 120), (200, 230, 255)),
    "business": ((40, 70, 50), (210, 235, 215)),
    "arts": ((120, 50, 90), (250, 220, 235)),
    "science": ((50, 40, 110), (220, 215, 250)),
    "education": ((90, 70, 30), (245, 235, 210)),
    "agriculture": ((50, 100, 40), (215, 240, 210)),
    "law": ((60, 50, 40), (235, 230, 220)),
    "language": ((70, 50, 120), (230, 220, 250)),
    "general": ((55, 65, 85), (225, 228, 235)),
}


def _country_gradient(country_code: str) -> tuple[tuple[int, int, int], tuple[int, int, int]]:
    code = (country_code or "").strip().lower()
    if code in COUNTRY_GRADIENTS:
        return COUNTRY_GRADIENTS[code]
    seed = int(hashlib.md5(code.encode("utf-8")).hexdigest()[:8], 16)
    top = (80 + seed % 100, 40 + (seed >> 8) % 90, 50 + (seed >> 16) % 80)
    bottom = (220 + seed % 25, 215 + (seed >> 4) % 30, 210 + (seed >> 12) % 35)
    return top, bottom


def major_category(title: str) -> str:
    t = title or ""
    if any(k in t for k in ("پزشکی", "دندان", "پرستاری", "دارو", "بهداشت", "زیست", "دامپزشکی", "فیزیوتراپی")):
        return "medical"
    if any(k in t for k in ("مهندسی", "کامپیوتر", "فناوری", "نرم", "برق", "مکانیک", "عمران", "معماری", "صنایع")):
        return "engineering"
    if any(k in t for k in ("مدیریت", "اقتصاد", "حسابداری", "MBA", "بازرگانی", "مالی")):
        return "business"
    if any(k in t for k in ("هنر", "موسیقی", "سینما", "طراحی", "گرافیک", "عکاسی", "نمایش")):
        return "arts"
    if any(k in t for k in ("ریاضی", "فیزیک", "شیمی", "آمار", "علوم", "زیست")):
        return "science"
    if any(k in t for k in ("آموزش", "تربیتی", "مشاوره")):
        return "education"
    if any(k in t for k in ("کشاورزی", "منابع طبیعی", "باغبانی", "شیلات")):
        return "agriculture"
    if any(k in t for k in ("حقوق", "قضایی")):
        return "law"
    if any(k in t for k in ("زبان", "ترجمه", "ادبیات")):
        return "language"
    return "general"


def _gradient_image(
    size: tuple[int, int],
    colors: tuple[tuple[int, int, int], tuple[int, int, int]],
    *,
    angle_seed: int = 0,
    footer_fade: bool = True,
) -> Image.Image:
    w, h = size
    top, bottom = colors
    img = Image.new("RGB", size, top)
    draw = ImageDraw.Draw(img)
    shift = (angle_seed % 40) - 20
    for y in range(h):
        ratio = max(0.0, min(1.0, (y + shift) / max(h - 1, 1)))
        r = int(top[0] * (1 - ratio) + bottom[0] * ratio)
        g = int(top[1] * (1 - ratio) + bottom[1] * ratio)
        b = int(top[2] * (1 - ratio) + bottom[2] * ratio)
        draw.line([(0, y), (w, y)], fill=(r, g, b))
    if footer_fade:
        draw.rectangle([0, int(h * 0.72), w, h], fill=(255, 255, 255))
    return img


def _cover_crop(
    img: Image.Image,
    target_w: int,
    target_h: int,
    *,
    offset_seed: int = 0,
) -> Image.Image:
    """برش مرکزی با نسبت ثابت — offset_seed برای تنوع بصری بین رشته‌های مشابه."""
    img = img.convert("RGB")
    src_w, src_h = img.size
    if src_w < 2 or src_h < 2:
        return Image.new("RGB", (target_w, target_h), (248, 248, 252))

    target_ratio = target_w / target_h
    src_ratio = src_w / src_h
    if src_ratio > target_ratio:
        new_w = int(src_h * target_ratio)
        max_left = max(0, src_w - new_w)
        left = (max_left * ((offset_seed * 17) % 97)) // 96 if max_left else 0
        img = img.crop((left, 0, left + new_w, src_h))
    else:
        new_h = int(src_w / target_ratio)
        max_top = max(0, src_h - new_h)
        top = (max_top * ((offset_seed * 23) % 97)) // 96 if max_top else 0
        img = img.crop((0, top, src_w, top + new_h))
    if img.size != (target_w, target_h):
        img = img.resize((target_w, target_h), Image.Resampling.LANCZOS)
    return img


def _upgrade_wikipedia_thumb_url(url: str, size: int = 1200) -> str:
    """بزرگ‌تر کردن URL بندانگشتی ویکی‌مدیا برای کیفیت بهتر."""
    if not url or "/thumb/" not in url:
        return url
    return re.sub(r"/(\d+)px-", f"/{size}px-", url, count=1)


def _fetch_url_bytes(url: str, timeout: int = 10) -> bytes | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": WIKI_USER_AGENT})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        logger.debug("fetch failed %s: %s", url, exc)
        return None


def _wikipedia_api_json(params: dict[str, str], *, host: str = "en.wikipedia.org") -> dict | None:
    qs = urllib.parse.urlencode({**params, "format": "json"})
    url = f"https://{host}/w/api.php?{qs}"
    raw = _fetch_url_bytes(url)
    if not raw:
        return None
    try:
        return json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError:
        return None


def fetch_wikipedia_thumbnail(name_en: str, *, thumb_size: int = 1200, host: str = "en.wikipedia.org") -> bytes | None:
    """دریافت تصویر بندانگشتی ویکی‌پدیا برای نام انگلیسی."""
    title = (name_en or "").strip()
    if not title:
        return None
    cache_key = f"thumb:{host}:{title.lower()}"
    if cache_key in _WIKI_RAW_CACHE:
        cached = _WIKI_RAW_CACHE[cache_key]
        return cached if cached else None

    encoded = urllib.parse.quote(title.replace(" ", "_"))
    api_url = f"https://{host}/api/rest_v1/page/summary/{encoded}"
    raw = _fetch_url_bytes(api_url)
    thumb_url = None
    if raw:
        try:
            data = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            data = {}
        wiki_title = (data.get("title") or "").strip()
        if wiki_title and is_acceptable_wikipedia_title(wiki_title) and data.get("type") != "disambiguation":
            thumb_url = (data.get("thumbnail") or {}).get("source")

    if not thumb_url:
        data = _wikipedia_api_json(
            {
                "action": "query",
                "titles": title,
                "prop": "pageimages",
                "piprop": "thumbnail",
                "pithumbsize": str(thumb_size),
            },
            host=host,
        )
        if data:
            pages = (data.get("query") or {}).get("pages") or {}
            for page in pages.values():
                wiki_title = (page.get("title") or "").strip()
                if wiki_title and not is_acceptable_wikipedia_title(wiki_title):
                    continue
                thumb_url = (page.get("thumbnail") or {}).get("source")
                if thumb_url:
                    break

    result = None
    if thumb_url:
        result = _fetch_url_bytes(_upgrade_wikipedia_thumb_url(thumb_url, thumb_size))

    _WIKI_RAW_CACHE[cache_key] = result or b""
    return result


def _image_digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _claim_major_image(raw: bytes) -> bool:
    """ثبت تصویر نهایی اگر قبلاً برای رشته دیگری استفاده نشده باشد."""
    digest = _image_digest(raw)
    with _MAJOR_IMAGE_DIGEST_LOCK:
        if digest in _USED_MAJOR_IMAGE_DIGESTS:
            return False
        _USED_MAJOR_IMAGE_DIGESTS.add(digest)
        return True


def reset_major_image_uniqueness_state() -> None:
    _WIKI_RAW_CACHE.clear()
    _WIKI_SEARCH_LIST_CACHE.clear()
    with _MAJOR_IMAGE_DIGEST_LOCK:
        _USED_MAJOR_IMAGE_DIGESTS.clear()


def preload_major_image_digests_from_db(
    country_codes: list[str] | None = None,
) -> int:
    """بارگذاری هش تصاویر فعلی رشته‌ها برای ادامه بدون تکرار."""
    qs = Major.objects.filter(is_active=True).exclude(image="").exclude(image__isnull=True)
    if country_codes:
        qs = qs.filter(country__in=country_codes)
    loaded = 0
    for major in qs.iterator():
        try:
            with major.image.open("rb") as fh:
                digest = _image_digest(fh.read())
        except OSError:
            continue
        with _MAJOR_IMAGE_DIGEST_LOCK:
            if digest not in _USED_MAJOR_IMAGE_DIGESTS:
                _USED_MAJOR_IMAGE_DIGESTS.add(digest)
                loaded += 1
    return loaded


def major_pks_not_refreshed_since(
    since,
    country_codes: list[str] | None = None,
) -> list[int]:
    """شناسه رشته‌هایی که از زمان مشخص هنوز تصویرشان بروز نشده."""
    import os

    from django.conf import settings
    from django.utils import timezone as dj_tz

    if since and dj_tz.is_naive(since):
        since = dj_tz.make_aware(since, timezone.utc)

    qs = Major.objects.filter(is_active=True).order_by("pk")
    if country_codes:
        qs = qs.filter(country__in=country_codes)

    pending: list[int] = []
    for major in qs.iterator():
        name = getattr(major.image, "name", "") or ""
        if not name:
            pending.append(major.pk)
            continue
        path = os.path.join(settings.MEDIA_ROOT, name.replace("/", os.sep))
        if not os.path.isfile(path):
            pending.append(major.pk)
            continue
        mtime = datetime.fromtimestamp(os.path.getmtime(path), tz=timezone.utc)
        if since is None or mtime < since:
            pending.append(major.pk)
    return pending


def _append_unique_image(results: list[bytes], raw: bytes | None, *, local_seen: set[str]) -> None:
    if not raw:
        return
    digest = _image_digest(raw)
    if digest in local_seen:
        return
    local_seen.add(digest)
    results.append(raw)


def wikipedia_search_images(
    query: str,
    *,
    thumb_size: int = 1200,
    host: str = "en.wikipedia.org",
    limit: int = 12,
) -> list[bytes]:
    """چند تصویر از نتایج جستجوی ویکی‌پدیا — برای تنوع بین رشته‌ها."""
    q = (query or "").strip()
    if not q:
        return []
    cache_key = f"wiki_imgs:{host}:{thumb_size}:{limit}:{q}"
    if cache_key in _WIKI_SEARCH_LIST_CACHE:
        return _WIKI_SEARCH_LIST_CACHE[cache_key]

    data = _wikipedia_api_json(
        {
            "action": "query",
            "generator": "search",
            "gsrsearch": q,
            "gsrlimit": str(max(limit, 8)),
            "prop": "pageimages",
            "piprop": "thumbnail",
            "pithumbsize": str(thumb_size),
        },
        host=host,
    )
    results: list[bytes] = []
    local_seen: set[str] = set()
    if data:
        pages = (data.get("query") or {}).get("pages") or {}
        for page in sorted(pages.values(), key=lambda p: p.get("index", 999)):
            if len(results) >= limit:
                break
            title = (page.get("title") or "").strip()
            if not title or not is_acceptable_wikipedia_title(title):
                continue
            thumb = (page.get("thumbnail") or {}).get("source")
            if thumb:
                raw = _fetch_url_bytes(_upgrade_wikipedia_thumb_url(thumb, thumb_size))
                _append_unique_image(results, raw, local_seen=local_seen)
                continue
            raw = fetch_wikipedia_thumbnail(title, thumb_size=thumb_size, host=host)
            _append_unique_image(results, raw, local_seen=local_seen)

    _WIKI_SEARCH_LIST_CACHE[cache_key] = results
    return results


def wikipedia_search_thumbnail(query: str, *, thumb_size: int = 1200, host: str = "en.wikipedia.org") -> bytes | None:
    """جستجوی ویکی‌پدیا و برگرداندن تصویر اولین نتیجه قابل قبول."""
    images = wikipedia_search_images(query, thumb_size=thumb_size, host=host, limit=1)
    return images[0] if images else None


def fetch_unique_major_thumbnail(major: Major) -> bytes | None:
    """سازگاری قدیمی — فقط اولین کاندید یکتا را برمی‌گرداند."""
    for prepared in iter_major_cover_candidates(major):
        if _claim_major_image(prepared):
            return prepared
    return None


def iter_major_cover_candidates(major: Major, *, raw_limit: int = 14) -> list[bytes]:
    """کاندیداهای تصویر نهایی برای یک رشته — مرتب‌شده بر اساس pk."""
    queries = build_major_image_search_queries(
        major.title,
        major.country or "",
        slug=major.slug or "",
        pk=major.pk or 0,
    )[:10]
    pk = major.pk or 0
    primary = build_wikipedia_query(major.title, major.country or "")
    country = (major.country or "").strip().lower()
    wiki_host = WIKIPEDIA_HOST_BY_COUNTRY.get(country, "en.wikipedia.org")
    wikidata_lang = WIKIDATA_LANG_BY_COUNTRY.get(country, "en")

    raw_pool: list[bytes] = []
    raw_seen: set[str] = set()

    def _add_raw(raw: bytes | None) -> None:
        if not raw or len(raw_pool) >= raw_limit:
            return
        digest = _image_digest(raw)
        if digest in raw_seen:
            return
        raw_seen.add(digest)
        raw_pool.append(raw)

    if primary != "Academic discipline":
        _add_raw(fetch_wikipedia_thumbnail(primary, host=wiki_host))
        if wiki_host != "en.wikipedia.org":
            _add_raw(fetch_wikipedia_thumbnail(primary, host="en.wikipedia.org"))
        _add_raw(wikidata_search_thumbnail(primary, lang=wikidata_lang))

    for qi, query in enumerate(queries):
        if len(raw_pool) >= raw_limit:
            break
        for raw in wikipedia_search_images(query, limit=10, host=wiki_host):
            _add_raw(raw)
        if len(raw_pool) < raw_limit:
            for raw in wikimedia_commons_search_images(query, limit=8):
                _add_raw(raw)
        if qi == 0 and len(raw_pool) < raw_limit:
            _add_raw(wikidata_search_thumbnail(query, lang=wikidata_lang))

    if raw_pool:
        start = pk % len(raw_pool)
        raw_pool = raw_pool[start:] + raw_pool[:start]

    prepared: list[bytes] = []
    prepared_seen: set[str] = set()
    variant_base = pk * 5
    for ri, raw in enumerate(raw_pool):
        for variant_offset in range(6):
            variant = variant_base + ri * 6 + variant_offset
            cover = prepare_major_image_bytes(raw, major.country or "", variant=variant)
            digest = _image_digest(cover)
            if digest in prepared_seen:
                continue
            prepared_seen.add(digest)
            prepared.append(cover)

    category = major_category(major.title)
    for salt in range(6):
        cover = generate_major_placeholder(
            category,
            major.country or "",
            f"p{pk}:{major.slug}:{salt}",
        )
        digest = _image_digest(cover)
        if digest in prepared_seen:
            continue
        prepared_seen.add(digest)
        prepared.append(cover)

    return prepared


def fetch_major_thumbnail(title: str, country: str) -> bytes | None:
    """سازگاری با کد قدیمی — برای یک رشته بدون کنترل یکتایی."""
    primary = build_wikipedia_query(title, country)
    raw = fetch_wikipedia_thumbnail(primary)
    if not raw:
        raw = wikipedia_search_thumbnail(primary)
    if not raw:
        fallback_q = build_wikipedia_fallback_query(title, country)
        if fallback_q != primary:
            raw = wikipedia_search_thumbnail(fallback_q)
    return raw


def _apply_country_overlay(img: Image.Image, country_code: str) -> Image.Image:
    """نوار رنگی کشور مقصد در پایین تصویر — تمایز بصری بین کشورها."""
    colors = _country_gradient(country_code)
    w, h = img.size
    overlay_h = max(int(h * 0.12), 36)
    bar = _gradient_image((w, overlay_h), colors)
    base = img.convert("RGB")
    base.paste(bar, (0, h - overlay_h))
    return base


def _bytes_to_image(raw: bytes) -> Image.Image | None:
    try:
        img = Image.open(io.BytesIO(raw))
        return ImageOps.exif_transpose(img)
    except OSError:
        return None


def prepare_major_image_bytes(raw: bytes, country_code: str, *, variant: int = 0) -> bytes:
    del country_code
    img = _bytes_to_image(raw)
    if img is None:
        return compress_to_jpeg_bytes(
            raw, max_bytes=MAJOR_IMAGE_MAX_BYTES, max_side=MAJOR_COVER_SIZE[0]
        )
    img = _cover_crop(img, *MAJOR_COVER_SIZE, offset_seed=variant)
    quality = max(82, min(95, 88 + (variant % 7)))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality, optimize=True)
    return compress_to_jpeg_bytes(
        buf.getvalue(), max_bytes=MAJOR_IMAGE_MAX_BYTES, max_side=MAJOR_COVER_SIZE[0]
    )


def generate_university_placeholder(country_code: str) -> bytes:
    colors = _country_gradient(country_code)
    img = _gradient_image((1200, 675), colors)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return compress_to_jpeg_bytes(buf.getvalue())


def prepare_university_image_bytes(raw: bytes) -> bytes:
    img = _bytes_to_image(raw)
    if img is None:
        return compress_to_jpeg_bytes(raw)
    img = img.convert("RGB")
    img.thumbnail((1200, 675), Image.Resampling.LANCZOS)
    if img.width < 800 or img.height < 450:
        canvas = Image.new("RGB", (1200, 675), (248, 248, 252))
        ox = (1200 - img.width) // 2
        oy = (675 - img.height) // 2
        canvas.paste(img, (ox, oy))
        img = canvas
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return compress_to_jpeg_bytes(buf.getvalue())


_PLACEHOLDER_BYTES_CACHE: dict[str, bytes] = {}
_PLACEHOLDER_SIZE_CACHE: dict[str, int] = {}


def _placeholder_bytes(country_code: str) -> bytes:
    code = (country_code or "").strip().lower()
    if code not in _PLACEHOLDER_BYTES_CACHE:
        _PLACEHOLDER_BYTES_CACHE[code] = generate_university_placeholder(code)
    return _PLACEHOLDER_BYTES_CACHE[code]


def _placeholder_size(country_code: str) -> int:
    code = (country_code or "").strip().lower()
    if code not in _PLACEHOLDER_SIZE_CACHE:
        _PLACEHOLDER_SIZE_CACHE[code] = len(_placeholder_bytes(code))
    return _PLACEHOLDER_SIZE_CACHE[code]


def university_has_placeholder_image(uni: University) -> bool:
    if not uni.image:
        return True
    try:
        stored_size = uni.image.size
    except OSError:
        return True
    if stored_size != _placeholder_size(uni.country or ""):
        return False
    try:
        with uni.image.open("rb") as fh:
            return fh.read() == _placeholder_bytes(uni.country or "")
    except OSError:
        return True


def wikimedia_commons_search_images(query: str, *, limit: int = 12) -> list[bytes]:
    """چند تصویر از ویکی‌مدیا کامنز — مکمل ویکی‌پدیا برای تنوع بیشتر."""
    q = (query or "").strip()
    if not q:
        return []
    cache_key = f"commons_imgs:{limit}:{q}"
    if cache_key in _WIKI_SEARCH_LIST_CACHE:
        return _WIKI_SEARCH_LIST_CACHE[cache_key]

    data = _wikipedia_api_json(
        {
            "action": "query",
            "generator": "search",
            "gsrsearch": q,
            "gsrnamespace": "6",
            "gsrlimit": str(max(limit, 8)),
            "prop": "imageinfo",
            "iiprop": "url",
            "iiurlwidth": "1200",
        },
        host="commons.wikimedia.org",
    )
    results: list[bytes] = []
    local_seen: set[str] = set()
    if not data:
        _WIKI_SEARCH_LIST_CACHE[cache_key] = results
        return results

    reject = (
        "logo",
        "seal",
        "emblem",
        "coat of arms",
        "flag",
        "map",
        "icon",
        "svg",
        "diagram",
        "chart",
    )
    pages = (data.get("query") or {}).get("pages") or {}
    for page in sorted(pages.values(), key=lambda p: p.get("index", 999)):
        if len(results) >= limit:
            break
        title = (page.get("title") or "").lower()
        if not title.startswith("file:"):
            continue
        if any(r in title for r in reject):
            continue
        info = (page.get("imageinfo") or [{}])[0]
        url = info.get("thumburl") or info.get("url")
        if not url:
            continue
        raw = _fetch_url_bytes(url)
        _append_unique_image(results, raw, local_seen=local_seen)

    _WIKI_SEARCH_LIST_CACHE[cache_key] = results
    return results


def wikimedia_commons_search_thumbnail(query: str) -> bytes | None:
    """جستجوی تصویر در ویکی‌مدیا کامنز وقتی مقاله ویکی‌پدیا تصویر ندارد."""
    images = wikimedia_commons_search_images(query, limit=1)
    return images[0] if images else None


def wikidata_search_thumbnail(query: str, *, lang: str = "en") -> bytes | None:
    """تصویر موجودیت ویکی‌دیتا (خاصیت P18) — مکمل برای دانشگاه‌های کم‌رسانه."""
    q = (query or "").strip()
    if not q:
        return None
    cache_key = f"wikidata:{lang}:{q.lower()}"
    if cache_key in _WIKI_RAW_CACHE:
        cached = _WIKI_RAW_CACHE[cache_key]
        return cached if cached else None

    search = _wikipedia_api_json(
        {
            "action": "wbsearchentities",
            "search": q,
            "language": lang,
            "limit": "6",
            "type": "item",
        },
        host="www.wikidata.org",
    )
    entity_ids: list[str] = []
    if search:
        for hit in search.get("search") or []:
            eid = (hit.get("id") or "").strip()
            if eid.startswith("Q"):
                entity_ids.append(eid)

    result = None
    for eid in entity_ids[:4]:
        entities = _wikipedia_api_json(
            {"action": "wbgetentities", "ids": eid, "props": "claims"},
            host="www.wikidata.org",
        )
        if not entities:
            continue
        entity = (entities.get("entities") or {}).get(eid) or {}
        claims = (entity.get("claims") or {}).get("P18") or []
        for claim in claims:
            mainsnak = claim.get("mainsnak") or {}
            datavalue = mainsnak.get("datavalue") or {}
            filename = (datavalue.get("value") or "").strip()
            if not filename:
                continue
            encoded = urllib.parse.quote(filename.replace(" ", "_"))
            url = f"https://commons.wikimedia.org/wiki/Special:FilePath/{encoded}?width=1200"
            raw = _fetch_url_bytes(url)
            if raw:
                result = raw
                break
        if result:
            break

    _WIKI_RAW_CACHE[cache_key] = result or b""
    return result


WIKIPEDIA_HOST_BY_COUNTRY: dict[str, str] = {
    "china": "zh.wikipedia.org",
    "spain": "es.wikipedia.org",
}

WIKIDATA_LANG_BY_COUNTRY: dict[str, str] = {
    "china": "zh",
    "spain": "es",
}


def fetch_university_thumbnail(uni: University) -> bytes | None:
    """تصویر واقعی دانشگاه: خلاصه ویکی‌پدیا، سپس جستجو با زمینه شهر/کشور."""
    cache_key = f"uni:{uni.pk}:{uni.name_en}"
    if cache_key in _WIKI_RAW_CACHE:
        cached = _WIKI_RAW_CACHE[cache_key]
        return cached or None

    country = (uni.country or "").strip().lower()
    wiki_host = WIKIPEDIA_HOST_BY_COUNTRY.get(country, "en.wikipedia.org")
    wikidata_lang = WIKIDATA_LANG_BY_COUNTRY.get(country, "en")

    queries = build_university_wikipedia_queries(
        uni.name_en,
        country=country,
        city=uni.city or "",
        name_fa=uni.name_fa or "",
    )
    for query in queries:
        if query in _WIKI_RAW_CACHE:
            raw = _WIKI_RAW_CACHE[query]
            if raw:
                _WIKI_RAW_CACHE[cache_key] = raw
                return raw
            continue

        hosts = [wiki_host, "en.wikipedia.org"] if wiki_host != "en.wikipedia.org" else ["en.wikipedia.org"]
        raw = None
        for host in hosts:
            raw = fetch_wikipedia_thumbnail(query, host=host)
            if not raw:
                raw = wikipedia_search_thumbnail(query, host=host)
            if raw:
                break
        if not raw:
            raw = wikimedia_commons_search_thumbnail(query)
        if not raw and "campus" not in query.lower() and "校园" not in query:
            raw = wikimedia_commons_search_thumbnail(f"{query} campus")
        if not raw:
            raw = wikidata_search_thumbnail(query, lang=wikidata_lang)
        if not raw and wikidata_lang != "en":
            raw = wikidata_search_thumbnail(query, lang="en")
        if raw:
            _WIKI_RAW_CACHE[query] = raw
            _WIKI_RAW_CACHE[cache_key] = raw
            return raw

    _WIKI_RAW_CACHE[cache_key] = b""
    return None


def _store_cover_at_path(path: str, raw: bytes) -> str:
    """ذخیره مستقیم با نام ثابت cover.jpg (بدون پسوند تصادفی Django)."""
    for attempt in range(4):
        try:
            if default_storage.exists(path):
                default_storage.delete(path)
            return default_storage.save(path, ContentFile(raw))
        except OSError as exc:
            if attempt >= 3:
                raise
            time.sleep(0.4 * (attempt + 1))
    return path


def _db_update_with_retry(model_cls, pk: int, **fields) -> None:
    from django.db import connection

    for attempt in range(12):
        try:
            model_cls.objects.filter(pk=pk).update(**fields)
            return
        except OperationalError as exc:
            if "locked" not in str(exc).lower() or attempt >= 11:
                raise
            connection.close()
            time.sleep(min(2.0, 0.25 * (2**attempt)))


def generate_major_placeholder(category: str, country_code: str, slug: str) -> bytes:
    cat_colors = MAJOR_CATEGORY_COLORS.get(category, MAJOR_CATEGORY_COLORS["general"])
    country_colors = _country_gradient(country_code)
    blended = (
        (
            (cat_colors[0][0] + country_colors[0][0]) // 2,
            (cat_colors[0][1] + country_colors[0][1]) // 2,
            (cat_colors[0][2] + country_colors[0][2]) // 2,
        ),
        (
            (cat_colors[1][0] + country_colors[1][0]) // 2,
            (cat_colors[1][1] + country_colors[1][1]) // 2,
            (cat_colors[1][2] + country_colors[1][2]) // 2,
        ),
    )
    seed = int(hashlib.md5(f"{country_code}:{slug}".encode()).hexdigest()[:6], 16)
    img = _gradient_image(MAJOR_COVER_SIZE, blended, angle_seed=seed % 80, footer_fade=False)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return compress_to_jpeg_bytes(
        buf.getvalue(), max_bytes=MAJOR_IMAGE_MAX_BYTES, max_side=MAJOR_COVER_SIZE[0]
    )


def attach_university_image(uni: University, *, force: bool = False) -> bool:
    if uni.image and not force and not university_has_placeholder_image(uni):
        return False

    raw = fetch_university_thumbnail(uni)
    if raw:
        raw = prepare_university_image_bytes(raw)
    elif uni.image and not university_has_placeholder_image(uni):
        return False
    else:
        raw = generate_university_placeholder(uni.country)

    path = university_image_upload_to(uni, "cover.jpg")
    stored = _store_cover_at_path(path, raw)
    _db_update_with_retry(University, uni.pk, image=stored)
    uni.image = stored
    return True


def attach_major_image(major: Major, *, force: bool = False) -> bool:
    if major.image and not force:
        return False

    prepared = _build_major_cover_bytes(major)

    path = major_image_upload_to(major, "cover.jpg")
    stored = _store_cover_at_path(path, prepared)
    _db_update_with_retry(Major, major.pk, image=stored)
    major.image = stored
    return True


def _country_hero_image_query(country: StudyCountry) -> str:
    code = (country.code or "").strip().lower()
    if code in COUNTRY_WIKI_LANDMARKS:
        return COUNTRY_WIKI_LANDMARKS[code]
    try:
        from core.seed_data.world_rich_country_facts import (
            COUNTRY_ENGLISH_NAMES,
            get_world_country_facts,
        )

        facts = get_world_country_facts(code)
        if facts and facts.get("image_queries"):
            return facts["image_queries"][0]
        name_en = COUNTRY_ENGLISH_NAMES.get(code, "")
        if name_en:
            return f"Higher education in {name_en}"
    except Exception:
        pass
    return country.name or code


def attach_country_section_images(
    country: StudyCountry,
    *,
    force: bool = False,
) -> int:
    """تصاویر بخش‌های محتوا (campus, visa, city) در media/countries/."""
    code = (country.code or "").strip().lower()
    queries: list[str] = []
    try:
        from core.seed_data.world_rich_country_facts import get_world_country_facts

        facts = get_world_country_facts(code)
        if facts:
            queries = list(facts.get("image_queries") or [])[:3]
    except Exception:
        pass
    while len(queries) < 3:
        queries.append(_country_hero_image_query(country))

    saved = 0
    for slot, query in zip(COUNTRY_SECTION_IMAGE_SLOTS, queries, strict=False):
        rel_path = f"countries/{code}-{slot}.jpg"
        if not force and default_storage.exists(rel_path):
            continue
        raw = fetch_wikipedia_thumbnail(query) or wikipedia_search_thumbnail(query)
        if not raw:
            raw = wikimedia_commons_search_thumbnail(query)
        if not raw:
            raw = generate_university_placeholder(code)
        else:
            img = _bytes_to_image(raw)
            if img:
                img = img.convert("RGB")
                img.thumbnail((1200, 675), Image.Resampling.LANCZOS)
                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=90)
                raw = compress_to_jpeg_bytes(buf.getvalue())
            else:
                raw = compress_to_jpeg_bytes(raw)
        _store_cover_at_path(rel_path, raw)
        saved += 1
        time.sleep(0.05)
    return saved


def attach_study_country_image(country: StudyCountry, *, force: bool = False) -> bool:
    if country.image and not force:
        return False

    query = _country_hero_image_query(country)
    raw = fetch_wikipedia_thumbnail(query) or wikipedia_search_thumbnail(query)
    if not raw:
        raw = generate_university_placeholder(country.code)
    else:
        img = _bytes_to_image(raw)
        if img:
            img = img.convert("RGB")
            img.thumbnail((1400, 700), Image.Resampling.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=90)
            raw = compress_to_jpeg_bytes(buf.getvalue())
        else:
            raw = compress_to_jpeg_bytes(raw)

    rel_path = f"countries/{country.code}.jpg"
    stored = _store_cover_at_path(rel_path, raw)
    _db_update_with_retry(StudyCountry, country.pk, image=stored)
    country.image = stored
    return True


def seed_university_images(
    country_codes: list[str] | None = None,
    *,
    force: bool = False,
) -> tuple[int, int]:
    _configure_sqlite_for_bulk_writes()
    qs = University.objects.all().order_by("country", "world_rank")
    if country_codes:
        qs = qs.filter(country__in=country_codes)
    ok = skip = 0
    for uni in qs.iterator():
        if not force and uni.image and not university_has_placeholder_image(uni):
            skip += 1
            continue
        if attach_university_image(uni, force=force):
            ok += 1
        else:
            skip += 1
        time.sleep(0.03)
    return ok, skip


def _configure_sqlite_for_bulk_writes() -> None:
    from django.db import connection

    from core.sqlite_db import configure_sqlite_connection

    configure_sqlite_connection(connection)


def _build_major_cover_bytes(major: Major) -> bytes:
    for prepared in iter_major_cover_candidates(major):
        if _claim_major_image(prepared):
            return prepared

    category = major_category(major.title)
    prepared = generate_major_placeholder(
        category,
        major.country or "",
        f"fallback-{major.pk}:{major.slug}",
    )
    _claim_major_image(prepared)
    return prepared


def seed_major_images(
    country_codes: list[str] | None = None,
    *,
    force: bool = False,
    batch_size: int = 25,
    chunk_size: int = 200,
    workers: int = 6,
    resume: bool = False,
    only_pks: list[int] | None = None,
) -> tuple[int, int]:
    if resume:
        _WIKI_RAW_CACHE.clear()
        _WIKI_SEARCH_LIST_CACHE.clear()
        preload_major_image_digests_from_db(country_codes)
    else:
        reset_major_image_uniqueness_state()
    _configure_sqlite_for_bulk_writes()

    if only_pks is not None:
        pk_list = list(only_pks)
        force = True
    else:
        qs = Major.objects.filter(is_active=True).order_by("pk")
        if country_codes:
            qs = qs.filter(country__in=country_codes)
        if not force:
            qs = qs.filter(Q(image="") | Q(image__isnull=True))
        pk_list = list(qs.values_list("pk", flat=True))

    ok = skip = 0
    pending: list[tuple[int, str]] = []

    def _flush_pending() -> None:
        nonlocal pending
        if not pending:
            return
        from core.sqlite_db import close_all_connections, is_retryable_db_error, retry_attempts, retry_delay_before_attempt

        for attempt in range(retry_attempts()):
            try:
                with transaction.atomic():
                    for pk, stored in pending:
                        Major.objects.filter(pk=pk).update(image=stored)
                pending = []
                return
            except OperationalError as exc:
                if not is_retryable_db_error(exc) or attempt >= retry_attempts() - 1:
                    raise
                close_all_connections()
                time.sleep(retry_delay_before_attempt(attempt))

    worker_count = max(1, min(int(workers or 1), 12))
    total = len(pk_list)

    for start in range(0, total, chunk_size):
        chunk_ids = pk_list[start : start + chunk_size]
        majors = list(Major.objects.filter(pk__in=chunk_ids).order_by("pk"))
        to_process = [m for m in majors if force or not m.image]
        skip += len(majors) - len(to_process)

        if not to_process:
            continue

        cover_by_pk: dict[int, bytes] = {}
        if worker_count == 1:
            for major in to_process:
                cover_by_pk[major.pk] = _build_major_cover_bytes(major)
        else:
            with ThreadPoolExecutor(max_workers=worker_count) as pool:
                futures = {pool.submit(_build_major_cover_bytes, major): major for major in to_process}
                for future in as_completed(futures):
                    major = futures[future]
                    cover_by_pk[major.pk] = future.result()

        for major in to_process:
            raw = cover_by_pk[major.pk]
            path = major_image_upload_to(major, "cover.jpg")
            if major.image:
                major.image.delete(save=False)
            stored = _store_cover_at_path(path, raw)
            pending.append((major.pk, stored))
            ok += 1

            if len(pending) >= batch_size:
                _flush_pending()

        _flush_pending()
        logger.info(
            "major images: %s/%s processed (%s updated, %s skipped)",
            min(start + chunk_size, total),
            total,
            ok,
            skip,
        )

    return ok, skip


def seed_study_country_images(
    country_codes: list[str] | None = None,
    *,
    force: bool = False,
    with_sections: bool = True,
) -> tuple[int, int]:
    qs = StudyCountry.objects.filter(is_active=True).order_by("order")
    if country_codes:
        qs = qs.filter(code__in=country_codes)
    ok = skip = 0
    for country in qs.iterator():
        if attach_study_country_image(country, force=force):
            ok += 1
        else:
            skip += 1
        if with_sections:
            attach_country_section_images(country, force=force)
    return ok, skip
