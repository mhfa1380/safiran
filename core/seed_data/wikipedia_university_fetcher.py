"""
دریافت فهرست دانشگاه‌ها از ویکی‌پدیا و تبدیل به ورودی کاتالوگ seed.

خروجی در کش JSON ذخیره می‌شود تا درخواست‌های مکرر به API نزند.
"""
from __future__ import annotations

import json
import logging
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from django.utils.text import slugify

logger = logging.getLogger(__name__)

WIKI_USER_AGENT = "SafiranStudyAbroadBot/1.0 (https://saroshan.ir; university catalog seed)"
CACHE_DIR = Path(__file__).resolve().parent / "cache"

WIKI_LIST_PAGES: dict[str, list[str]] = {
    "canada": ["List of universities in Canada"],
    "spain": ["List of universities in Spain"],
    "china": [
        "Project 985",
        "Project 211",
        "C9 League",
        "List of universities and colleges in Beijing",
        "List of universities and colleges in Shanghai",
        "List of universities and colleges in Guangdong",
        "List of universities and colleges in Jiangsu",
        "List of universities and colleges in Zhejiang",
        "List of universities and colleges in Shandong",
        "List of universities and colleges in Hubei",
        "List of universities and colleges in Sichuan",
        "List of universities and colleges in Hunan",
        "List of universities and colleges in Fujian",
        "List of universities and colleges in Anhui",
        "List of universities and colleges in Liaoning",
        "List of universities and colleges in Shaanxi",
        "List of universities and colleges in Chongqing",
        "List of universities and colleges in Tianjin",
        "List of universities and colleges in Heilongjiang",
        "List of universities and colleges in Jilin",
    ],
    "uk": [
        "List of universities in the United Kingdom",
        "Russell Group",
    ],
    "usa": [
        "List of research universities in the United States",
        "Association of American Universities",
    ],
    "australia": ["List of universities in Australia", "Group of Eight (Australian universities)"],
    "germany": ["List of universities in Germany", "TU9"],
    "italy": ["List of universities in Italy"],
    "france": ["List of public universities in France", "Grandes écoles"],
    "netherlands": ["List of universities in the Netherlands"],
    "switzerland": ["List of universities in Switzerland"],
    "japan": ["List of universities in Japan"],
    "south_korea": ["List of universities in South Korea", "SKY (universities)"],
    "singapore": ["List of universities in Singapore"],
    "hong_kong": ["List of universities in Hong Kong"],
    "ireland": ["List of universities in the Republic of Ireland"],
    "sweden": ["List of universities in Sweden"],
    "belgium": ["List of universities in Belgium"],
    "austria": ["List of universities in Austria"],
    "new_zealand": ["List of universities in New Zealand"],
    "denmark": ["List of universities in Denmark"],
    "finland": ["List of universities in Finland"],
    "norway": ["List of universities in Norway"],
    "portugal": ["List of universities in Portugal"],
    "poland": ["List of universities in Poland"],
    "czech": ["List of universities in the Czech Republic"],
    "hungary": ["List of universities in Hungary"],
    "greece": ["List of universities in Greece"],
    "turkey": ["List of universities in Turkey"],
    "malaysia": ["List of universities in Malaysia"],
    "uae": ["List of universities in the United Arab Emirates"],
    "saudi_arabia": ["List of universities in Saudi Arabia"],
    "qatar": ["List of universities in Qatar"],
    "india": ["List of universities in India"],
    "thailand": ["List of universities in Thailand"],
    "israel": ["List of universities in Israel"],
    "brazil": ["List of universities in Brazil"],
    "mexico": ["List of universities in Mexico"],
    "argentina": ["List of universities in Argentina"],
    "chile": ["List of universities in Chile"],
    "south_africa": ["List of universities in South Africa"],
    "egypt": ["List of universities in Egypt"],
    "russia": ["List of universities in Russia"],
    "taiwan": ["List of universities in Taiwan"],
}

_COUNTRY_UNI_PATTERNS: dict[str, re.Pattern[str]] = {
    "canada": re.compile(r"(University|Université|College)", re.I),
    "spain": re.compile(r"(Universidad|Universitat|University|Polytechnic)", re.I),
    "china": re.compile(r"(University|College|Institute of Technology)", re.I),
    "uk": re.compile(r"(University|College|Institute)", re.I),
    "usa": re.compile(r"(University|College|Institute)", re.I),
    "australia": re.compile(r"(University|College)", re.I),
    "germany": re.compile(r"(Universität|University|Hochschule|Institute)", re.I),
    "italy": re.compile(r"(Università|University|Politecnico)", re.I),
    "france": re.compile(r"(Université|University|École|Institut)", re.I),
    "netherlands": re.compile(r"(University|Universiteit|College)", re.I),
    "switzerland": re.compile(r"(University|Universität|École|ETH|EPFL)", re.I),
    "japan": re.compile(r"(University|College|Institute)", re.I),
    "south_korea": re.compile(r"(University|College|Institute)", re.I),
    "singapore": re.compile(r"(University|College|Institute)", re.I),
    "hong_kong": re.compile(r"(University|College|Institute)", re.I),
    "ireland": re.compile(r"(University|College|Institute)", re.I),
    "sweden": re.compile(r"(University|Universitet|Institute)", re.I),
    "belgium": re.compile(r"(University|Université|Universiteit)", re.I),
    "austria": re.compile(r"(University|Universität)", re.I),
    "new_zealand": re.compile(r"(University|College|Institute)", re.I),
    "denmark": re.compile(r"(University|Universitet)", re.I),
    "finland": re.compile(r"(University|Yliopisto)", re.I),
    "norway": re.compile(r"(University|Universitet)", re.I),
    "portugal": re.compile(r"(Universidade|University)", re.I),
    "poland": re.compile(r"(University|Uniwersytet|Politechnika)", re.I),
    "czech": re.compile(r"(University|Univerzita)", re.I),
    "hungary": re.compile(r"(University|Egyetem)", re.I),
    "greece": re.compile(r"(University|Πανεπιστήμιο)", re.I),
    "turkey": re.compile(r"(University|Üniversitesi)", re.I),
    "malaysia": re.compile(r"(University|Universiti)", re.I),
    "uae": re.compile(r"(University|College|Institute)", re.I),
    "saudi_arabia": re.compile(r"(University|College|King)", re.I),
    "qatar": re.compile(r"(University|College)", re.I),
    "india": re.compile(r"(University|Institute of Technology|IIT)", re.I),
    "thailand": re.compile(r"(University|Institute)", re.I),
    "israel": re.compile(r"(University|Institute|College)", re.I),
    "brazil": re.compile(r"(Universidade|University)", re.I),
    "mexico": re.compile(r"(Universidad|University|Instituto)", re.I),
    "argentina": re.compile(r"(Universidad|University)", re.I),
    "chile": re.compile(r"(Universidad|University)", re.I),
    "south_africa": re.compile(r"(University|College)", re.I),
    "egypt": re.compile(r"(University|جامعة)", re.I),
    "russia": re.compile(r"(University|Institute|Universitet)", re.I),
    "taiwan": re.compile(r"(University|College)", re.I),
}

_SKIP_NAME_FRAGMENTS = (
    "list of",
    "category:",
    "template:",
    "file:",
    "portal:",
    "see also",
    "notes",
    "references",
    "external links",
    "rankings",
    "comparison",
    "alliance",
    "association",
    "federation",
    "stub",
    "faculty deans",
    "buildings and structures",
    "campuses in",
)

_COUNTRY_NAME_EXCLUDES: dict[str, tuple[str, ...]] = {
    "china": (
        "vocational",
        "police college",
        "graduate school",
        " law school",
        "city college",
        "business college",
        "financial college",
        "polytechnic college",
        "college of commerce",
        "college of technology",
        "information engineering school",
        "engineering school",
        "normal university qianjiang",
    ),
    "spain": ("category:",),
    "canada": ("category:",),
}


def _is_valid_university_name(name_en: str, country_code: str) -> bool:
    low = (name_en or "").lower().strip()
    if not low or len(name_en) < 6:
        return False
    if any(skip in low for skip in _SKIP_NAME_FRAGMENTS):
        return False
    if country_code == "canada":
        if not any(k in name_en for k in ("University", "Université")):
            return False
    elif country_code == "spain":
        if not any(k in name_en for k in ("Universidad", "Universitat", "University", "Polytechnic")):
            return False
    elif country_code == "china":
        if "University" not in name_en:
            return False
        if "College" in name_en:
            return False
    elif country_code in ("uk", "usa", "australia", "new_zealand", "ireland", "canada"):
        if not any(k in name_en for k in ("University", "College", "Institute")):
            return False
    elif country_code in ("germany", "austria", "switzerland"):
        if not any(k in name_en for k in ("Universität", "University", "ETH", "EPFL", "Hochschule")):
            return False
    elif country_code in ("france", "italy", "spain", "portugal", "brazil", "mexico", "argentina", "chile"):
        if not any(
            k in name_en
            for k in ("Université", "Universidad", "Universidade", "University", "Politecnico", "École")
        ):
            return False
    for frag in _COUNTRY_NAME_EXCLUDES.get(country_code, ()):
        if frag in low:
            return False
    if "access-date=" in low or "title=" in low:
        return False
    return True


def _fetch_wiki_json(params: dict[str, str], *, retries: int = 4) -> dict | None:
    qs = urllib.parse.urlencode({**params, "format": "json"})
    url = f"https://en.wikipedia.org/w/api.php?{qs}"
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": WIKI_USER_AGENT})
            with urllib.request.urlopen(req, timeout=45) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code == 429 and attempt < retries - 1:
                time.sleep(2 ** (attempt + 1))
                continue
            logger.warning("Wikipedia API HTTP %s: %s", exc.code, params.get("page", params))
            return None
        except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            logger.warning("Wikipedia API failed: %s", exc)
            return None
    return None


def _parse_wikitext_universities(wikitext: str, country_code: str) -> list[dict[str, str]]:
    pattern = _COUNTRY_UNI_PATTERNS.get(country_code, _COUNTRY_UNI_PATTERNS["canada"])
    found: dict[str, dict[str, str]] = {}

    for line in wikitext.splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.split("|")[1:-1]]
        if not cells:
            continue
        name_cell = cells[0]
        if "[[" not in name_cell:
            continue
        m = re.search(r"\[\[([^\]|#]+)(?:\|([^\]]+))?\]\]", name_cell)
        if not m:
            continue
        name_en = (m.group(1) or "").strip()
        if not name_en or not pattern.search(name_en):
            continue
        if not _is_valid_university_name(name_en, country_code):
            continue
        low = name_en.lower()
        if any(skip in low for skip in _SKIP_NAME_FRAGMENTS):
            continue
        if name_en.endswith(")") and "(" in name_en:
            # disambiguation e.g. Concordia University (Montreal) — keep
            pass
        city = ""
        if len(cells) > 1:
            city = re.sub(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", r"\1", cells[1]).strip()
            city = re.sub(r"<[^>]+>", "", city).strip()
        if name_en not in found:
            found[name_en] = {"name_en": name_en, "city": city}

    # bullet / inline links
    for m in re.finditer(r"\[\[([^\]|#]+?)\s*University(?:\s+of\s+[^\]|#]+)?(?:\|[^\]]+)?\]\]", wikitext):
        name_en = m.group(1).strip() + " University"
        if name_en.count("University") > 1:
            name_en = m.group(0).strip("[]").split("|")[0].strip()
        if not pattern.search(name_en):
            continue
        if not _is_valid_university_name(name_en, country_code):
            continue
        low = name_en.lower()
        if any(skip in low for skip in _SKIP_NAME_FRAGMENTS):
            continue
        if name_en not in found:
            found[name_en] = {"name_en": name_en, "city": ""}

    for m in re.finditer(r"\[\[([^\]|]+University[^\]|]*)\]\]", wikitext):
        name_en = m.group(1).strip()
        if not pattern.search(name_en):
            continue
        if not _is_valid_university_name(name_en, country_code):
            continue
        if name_en not in found:
            found[name_en] = {"name_en": name_en, "city": ""}

    return list(found.values())


def _slug_for_name(name_en: str) -> str:
    base = slugify(name_en, allow_unicode=False)
    if not base:
        base = slugify(name_en.replace("(", " ").replace(")", " "), allow_unicode=False)
    base = re.sub(r"-+", "-", base).strip("-")
    return base[:150] or "university"


def _persian_name(name_en: str) -> str:
    """نام فارسی تقریبی — در صورت نبود ترجمه در کاتالوگ اصلی."""
    if name_en.startswith("Universidad "):
        return f"دانشگاه {name_en.replace('Universidad ', '')}"
    if name_en.startswith("Université "):
        return f"دانشگاه {name_en.replace('Université ', '')}"
    if name_en.startswith("University of "):
        return f"دانشگاه {name_en.replace('University of ', '')}"
    if name_en.endswith(" University"):
        return f"دانشگاه {name_en.replace(' University', '')}"
    return f"دانشگاه {name_en}"


def _normalize_city(city: str, country_code: str) -> str:
    c = (city or "").strip()
    if not c or "access-date=" in c or "title=" in c or c.startswith("{{"):
        c = ""
    if c and len(c) < 80:
        return c
    defaults = {
        "canada": "کانادا",
        "spain": "اسپانیا",
        "china": "چین",
        "uk": "انگلستان",
        "usa": "آمریکا",
        "australia": "استرالیا",
        "germany": "آلمان",
        "italy": "ایتالیا",
        "france": "فرانسه",
    }
    return defaults.get(country_code, "")


def fetch_country_universities(country_code: str, *, use_cache: bool = True) -> list[dict]:
    """لیست خام دانشگاه‌های یک کشور از ویکی‌پدیا."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = CACHE_DIR / f"wikipedia_{country_code}.json"
    if use_cache and cache_path.is_file():
        try:
            data = json.loads(cache_path.read_text(encoding="utf-8"))
            if isinstance(data, list) and data:
                return data
        except (json.JSONDecodeError, OSError):
            pass

    pages = WIKI_LIST_PAGES.get(country_code, [])
    merged: dict[str, dict[str, str]] = {}
    for page in pages:
        data = _fetch_wiki_json({"action": "parse", "page": page, "prop": "wikitext"})
        time.sleep(1.2)
        if not data or "parse" not in data:
            continue
        wikitext = data["parse"].get("wikitext", {}).get("*", "")
        for row in _parse_wikitext_universities(wikitext, country_code):
            merged[row["name_en"]] = row

    result = list(merged.values())
    try:
        cache_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError as exc:
        logger.warning("Could not write wiki cache %s: %s", cache_path, exc)
    return result


def build_catalog_entries(
    country_code: str,
    *,
    existing_slugs: set[str] | None = None,
    start_rank: int = 31,
    use_cache: bool = True,
) -> list[dict]:
    """تبدیل داده ویکی‌پدیا به فرمت university_catalog."""
    existing_slugs = existing_slugs or set()
    raw = fetch_country_universities(country_code, use_cache=use_cache)
    entries: list[dict] = []
    rank = start_rank
    seen_slugs: set[str] = set(existing_slugs)

    for row in sorted(raw, key=lambda r: r["name_en"].lower()):
        name_en = row["name_en"]
        slug = _slug_for_name(name_en)
        if slug in seen_slugs:
            suffix = 2
            candidate = f"{slug}-{suffix}"
            while candidate in seen_slugs:
                suffix += 1
                candidate = f"{slug}-{suffix}"
            slug = candidate[:150]
        seen_slugs.add(slug)

        city = _normalize_city(row.get("city", ""), country_code)
        entries.append(
            {
                "slug": slug,
                "name_fa": _persian_name(name_en),
                "name_en": name_en,
                "city": city,
                "world_rank": str(rank),
                "qs_rank_note": "—",
                "website": "",
                "mo_science": True,
                "mo_health": "medical" in name_en.lower() or "health" in name_en.lower(),
            }
        )
        rank += 1
    return entries
