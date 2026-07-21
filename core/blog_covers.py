"""
تولید تصویر شاخص اختصاصی برای پست‌های وبلاگ (Pillow).
"""
from __future__ import annotations

import hashlib
import math
from io import BytesIO
from typing import Any

from PIL import Image, ImageDraw, ImageFilter

# پالت کشور / موضوع
_COUNTRY_PALETTES: dict[str, tuple[str, str, str]] = {
    "کانادا": ("#C8102E", "#FFFFFF", "#0c2e60"),
    "اسپانیا": ("#AA151B", "#F1BF00", "#1e3a5f"),
    "چین": ("#DE2910", "#FFDE00", "#0c2e60"),
    "مهاجرت تحصیلی": ("#0c2e60", "#2e65a5", "#ff663b"),
    "خدمات موسسه": ("#0d9488", "#e0f2fe", "#0c2e60"),
    "ارزیابی رایگان": ("#0d9488", "#99f6e4", "#0f766e"),
    "قوانین و اخبار": ("#1e293b", "#64748b", "#f59e0b"),
    "مقایسه کشورها": ("#4f46e5", "#c7d2fe", "#0c2e60"),
    "زندگی دانشجویی": ("#0369a1", "#bae6fd", "#0c2e60"),
    "غذا و فرهنگ": ("#b45309", "#fde68a", "#78350f"),
}

_TOPIC_HINTS: list[tuple[tuple[str, ...], str]] = [
    (("visa", "ویزا", "permit", "gic", "nie", "x1", "x2", "immigration"), "visa"),
    (("scholarship", "csc", "burs", "بورسیه"), "scholarship"),
    (("food", "halal", "poutine", "tapas", "cuisine", "غذا"), "food"),
    (("job", "work", "pgwp", "کار"), "work"),
    (("cost", "living", "هزینه"), "money"),
    (("checklist", "consultation", "evaluation", "ارزیابی"), "guide"),
    (("winter", "festival", "culture", "زندگی"), "life"),
    (("language", "hsk", "spanish", "ielts", "زبان"), "language"),
    (("compare", "مقایسه"), "compare"),
    (("degree", "مدرک", "validity"), "docs"),
]


def _topic_from_slug(slug: str) -> str:
    s = slug.lower()
    for keys, topic in _TOPIC_HINTS:
        if any(k in s for k in keys):
            return topic
    return "study"


def _palette(country_tag: str, slug: str) -> tuple[str, str, str]:
    if country_tag in _COUNTRY_PALETTES:
        return _COUNTRY_PALETTES[country_tag]
    for key, pal in _COUNTRY_PALETTES.items():
        if key in (country_tag or ""):
            return pal
    h = int(hashlib.md5(slug.encode()).hexdigest()[:8], 16)
    hues = ["#0c2e60", "#0d9488", "#7c3aed", "#b45309", "#be123c"]
    return (hues[h % len(hues)], "#f8fafc", "#334155")


def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))


def _lerp(a: int, b: int, t: float) -> int:
    return int(a + (b - a) * t)


def _gradient(size: tuple[int, int], c1: str, c2: str, c3: str) -> Image.Image:
    w, h = size
    img = Image.new("RGB", size)
    px = img.load()
    r1, g1, b1 = _hex_to_rgb(c1)
    r2, g2, b2 = _hex_to_rgb(c2)
    r3, g3, b3 = _hex_to_rgb(c3)
    for y in range(h):
        for x in range(w):
            t = (x / w * 0.55 + y / h * 0.45)
            if t < 0.5:
                tt = t * 2
                r, g, b = _lerp(r1, r2, tt), _lerp(g1, g2, tt), _lerp(b1, b2, tt)
            else:
                tt = (t - 0.5) * 2
                r, g, b = _lerp(r2, r3, tt), _lerp(g2, g3, tt), _lerp(b2, b3, tt)
            px[x, y] = (r, g, b)
    return img.filter(ImageFilter.GaussianBlur(radius=1))


def _draw_motif(draw: ImageDraw.ImageDraw, topic: str, w: int, h: int, accent: str) -> None:
    cx, cy = int(w * 0.72), int(h * 0.38)
    fill = accent + "55"
    outline = accent
    if topic == "visa":
        draw.rounded_rectangle(
            (cx - 90, cy - 60, cx + 90, cy + 60), radius=18, outline=outline, width=4
        )
        draw.line((cx - 50, cy - 10, cx + 50, cy - 10), fill=outline, width=3)
        draw.line((cx - 50, cy + 15, cx + 30, cy + 15), fill=outline, width=3)
    elif topic == "scholarship":
        draw.polygon(
            [
                (cx, cy - 70),
                (cx + 22, cy - 20),
                (cx + 75, cy - 20),
                (cx + 32, cy + 12),
                (cx + 48, cy + 68),
                (cx, cy + 38),
                (cx - 48, cy + 68),
                (cx - 32, cy + 12),
                (cx - 75, cy - 20),
                (cx - 22, cy - 20),
            ],
            outline=outline,
            width=3,
        )
    elif topic == "food":
        draw.ellipse((cx - 75, cy - 75, cx + 75, cy + 75), outline=outline, width=4)
        draw.arc((cx - 40, cy - 40, cx + 40, cy + 40), 0, 300, fill=outline, width=3)
    elif topic == "work":
        draw.rectangle((cx - 70, cy - 45, cx + 70, cy + 45), outline=outline, width=4)
        draw.line((cx - 70, cy - 5, cx + 70, cy - 5), fill=outline, width=3)
    elif topic == "money":
        draw.ellipse((cx - 65, cy - 40, cx + 65, cy + 40), outline=outline, width=4)
        draw.text((cx - 18, cy - 22), "$", fill=outline)
    elif topic == "compare":
        draw.rectangle((cx - 80, cy - 50, cx - 10, cy + 50), outline=outline, width=3)
        draw.rectangle((cx + 10, cy - 50, cx + 80, cy + 50), outline=outline, width=3)
    elif topic == "language":
        draw.ellipse((cx - 70, cy - 50, cx + 70, cy + 50), outline=outline, width=4)
        draw.text((cx - 28, cy - 18), "Aa", fill=outline)
    else:
        draw.polygon(
            [
                (cx - 60, cy + 40),
                (cx, cy - 70),
                (cx + 60, cy + 40),
            ],
            outline=outline,
            width=4,
        )
        draw.rectangle((cx - 80, cy + 40, cx + 80, cy + 70), fill=fill, outline=outline, width=2)

    # نقطه‌های تزئینی
    for i in range(8):
        ang = i * math.pi / 4
        x = int(w * 0.15) + int(30 * math.cos(ang))
        y = int(h * 0.2) + int(20 * math.sin(ang))
        r = 6 + (i % 3) * 3
        draw.ellipse((x - r, y - r, x + r, y + r), fill=accent + "33")


def generate_blog_cover(
    slug: str,
    country_tag: str = "",
    *,
    width: int = 1200,
    height: int = 675,
) -> bytes:
    """JPEG bytes for featured image."""
    primary, secondary, accent = _palette(country_tag, slug)
    topic = _topic_from_slug(slug)
    img = _gradient((width, height), primary, secondary, accent)
    draw = ImageDraw.Draw(img, "RGBA")

    # نوار پایین
    draw.rectangle((0, int(height * 0.72), width, height), fill=(12, 46, 96, 210))
    draw.rectangle((0, int(height * 0.68), width, int(height * 0.72)), fill=(255, 102, 59, 180))

    _draw_motif(draw, topic, width, height, accent)

    # برچسب کشور (لاتین برای فونت پیش‌فرض)
    label = (country_tag or "Study Abroad")[:24]
    draw.text((48, height - 52), label, fill=(255, 255, 255, 255))

    buf = BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=88, optimize=True)
    return buf.getvalue()


def cover_theme_meta(slug: str, country_tag: str) -> dict[str, Any]:
    primary, secondary, accent = _palette(country_tag, slug)
    return {
        "slug": slug,
        "country_tag": country_tag,
        "topic": _topic_from_slug(slug),
        "primary": primary,
        "secondary": secondary,
        "accent": accent,
    }
