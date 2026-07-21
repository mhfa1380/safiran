"""
کاتالوگ دانشگاه‌های برتر جهان (خارج از کانادا، اسپانیا، چین).

ترکیب رتبه QS از ویکی‌پدیا + فهرست‌های ویکی‌پدیا هر کشور.
"""
from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

from core.study_destinations import WORLD_STUDY_COUNTRY_CODES, WORLD_STUDY_COUNTRY_LABELS
from core.seed_data.world_curated_top import WORLD_CURATED_TOP
from core.seed_data.wikipedia_university_fetcher import (
    _persian_name,
    _slug_for_name,
    build_catalog_entries,
    fetch_country_universities,
)

CACHE_DIR = Path(__file__).resolve().parent / "cache"
QS_CACHE = CACHE_DIR / "qs_world_institutions.json"
WORLD_MERGED_CACHE = CACHE_DIR / "world_universities_merged.json"

WIKI_USER_AGENT = "SafiranStudyAbroadBot/1.0 (world catalog)"
SKIP_COUNTRY_CODES = frozenset({"canada", "china", "spain"})

_FLAG_TO_COUNTRY: dict[str, str] = {
    "USA": "usa",
    "US": "usa",
    "UK": "uk",
    "AUS": "australia",
    "DEU": "germany",
    "DE": "germany",
    "FRA": "france",
    "FR": "france",
    "NLD": "netherlands",
    "NL": "netherlands",
    "SUI": "switzerland",
    "CH": "switzerland",
    "CHE": "switzerland",
    "JPN": "japan",
    "JP": "japan",
    "KOR": "south_korea",
    "KR": "south_korea",
    "SGP": "singapore",
    "SG": "singapore",
    "HKG": "hong_kong",
    "Hong Kong": "hong_kong",
    "CHN": "china",
    "CN": "china",
    "CAN": "canada",
    "CA": "canada",
    "ESP": "spain",
    "ES": "spain",
    "ITA": "italy",
    "IT": "italy",
    "IRL": "ireland",
    "IE": "ireland",
    "SWE": "sweden",
    "SE": "sweden",
    "BEL": "belgium",
    "BE": "belgium",
    "AUT": "austria",
    "AT": "austria",
    "NZL": "new_zealand",
    "NZ": "new_zealand",
    "DNK": "denmark",
    "DK": "denmark",
    "FIN": "finland",
    "FI": "finland",
    "NOR": "norway",
    "NO": "norway",
    "PRT": "portugal",
    "PT": "portugal",
    "POL": "poland",
    "PL": "poland",
    "CZE": "czech",
    "CZ": "czech",
    "HUN": "hungary",
    "HU": "hungary",
    "GRC": "greece",
    "GR": "greece",
    "TUR": "turkey",
    "TR": "turkey",
    "MYS": "malaysia",
    "MY": "malaysia",
    "ARE": "uae",
    "AE": "uae",
    "SAU": "saudi_arabia",
    "SA": "saudi_arabia",
    "QAT": "qatar",
    "QA": "qatar",
    "IND": "india",
    "IN": "india",
    "THA": "thailand",
    "TH": "thailand",
    "ISR": "israel",
    "IL": "israel",
    "BRA": "brazil",
    "BR": "brazil",
    "MEX": "mexico",
    "MX": "mexico",
    "ARG": "argentina",
    "AR": "argentina",
    "CHL": "chile",
    "CL": "chile",
    "ZAF": "south_africa",
    "ZA": "south_africa",
    "EGY": "egypt",
    "EG": "egypt",
    "RUS": "russia",
    "RU": "russia",
    "TWN": "taiwan",
    "TW": "taiwan",
    "Sweden": "sweden",
}

# نام فارسی برای دانشگاه‌های بسیار معروف
_FA_NAME_OVERRIDES: dict[str, str] = {
    "Massachusetts Institute of Technology": "مؤسسه فناوری ماساچوست (MIT)",
    "Harvard University": "دانشگاه هاروارد",
    "Stanford University": "دانشگاه استنفورد",
    "University of Oxford": "دانشگاه آکسفورد",
    "University of Cambridge": "دانشگاه کمbridge",
    "Imperial College London": "کالج امپریال لندن",
    "University College London": "دانشگاه کالج لندن",
    "ETH Zurich": "ETH زوریخ",
    "National University of Singapore": "دانشگاه ملی سنگاپور",
    "University of Melbourne": "دانشگاه ملبورن",
    "University of Sydney": "دانشگاه سیدنی",
    "Technical University of Munich": "دانشگاه فنی مونیخ",
    "Ludwig Maximilian University of Munich": "دانشگاه لودویگ ماکسیمیلیان مونیخ",
    "Heidelberg University": "دانشگاه هایدelberg",
    "Sorbonne University": "دانشگاه سورbon",
    "University of Amsterdam": "دانشگاه آمsterdam",
    "Delft University of Technology": "دانشگاه فنی دلفt",
    "University of Tokyo": "دانشگاه توkyo",
    "Seoul National University": "دانشگاه ملی سئول",
    "KAIST": "KAIST کره",
    "University of Hong Kong": "دانشگاه هنگ‌کنگ",
    "Tsinghua University": "دانشگاه Tsinghua",
    "Peking University": "دانشگاه پکن",
}


def _wiki_wikitext(page: str) -> str:
    qs = urllib.parse.urlencode(
        {"action": "parse", "page": page, "prop": "wikitext", "format": "json"}
    )
    req = urllib.request.Request(
        f"https://en.wikipedia.org/w/api.php?{qs}",
        headers={"User-Agent": WIKI_USER_AGENT},
    )
    with urllib.request.urlopen(req, timeout=90) as resp:
        data = json.loads(resp.read().decode())
    return data["parse"]["wikitext"]["*"]


def _parse_qs_institution_rows(text: str) -> list[dict]:
    """استخراج دانشگاه‌ها از جداول QS با الگوی {{flagicon|XX}} [[Name]]."""
    rows: list[dict] = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        i += 1
        if not line.startswith("|") or "{{flagicon|" not in line or "[[" not in line:
            continue
        flag_m = re.search(r"\{\{flagicon\|([^}|]+)", line)
        uni_m = re.search(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", line)
        if not uni_m:
            continue
        name_en = uni_m.group(1).strip()
        if len(name_en) < 5:
            continue
        if not any(
            k in name_en
            for k in ("University", "Institute", "College", "École", "Universidad", "Universidade")
        ):
            continue
        country_code = ""
        if flag_m:
            country_code = _FLAG_TO_COUNTRY.get(flag_m.group(1).strip(), "")
        if country_code in SKIP_COUNTRY_CODES or not country_code:
            continue
        qs_rank = 9999
        if i < len(lines):
            rank_line = lines[i].strip()
            if rank_line.startswith("|") and "[[" not in rank_line:
                rank_cell = rank_line.split("|")[1].strip().replace("=", "")
                if rank_cell.isdigit():
                    qs_rank = int(rank_cell)
                i += 1
        rows.append({"name_en": name_en, "country_code": country_code, "qs_rank": qs_rank})
    return rows


def fetch_qs_institutions(*, refresh: bool = False) -> list[dict]:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    if not refresh and QS_CACHE.is_file():
        try:
            data = json.loads(QS_CACHE.read_text(encoding="utf-8"))
            if isinstance(data, list) and data:
                return data
        except (json.JSONDecodeError, OSError):
            pass
    text = _wiki_wikitext("QS World University Rankings")
    rows = _parse_qs_institution_rows(text)
    dedup: dict[str, dict] = {}
    for row in rows:
        key = row["name_en"].lower()
        if key not in dedup or row["qs_rank"] < dedup[key]["qs_rank"]:
            dedup[key] = row
    result = sorted(dedup.values(), key=lambda r: (r["qs_rank"], r["name_en"]))
    QS_CACHE.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def _entry_from_qs(row: dict, *, rank: int) -> dict:
    name_en = row["name_en"]
    slug = _slug_for_name(name_en)
    qs = row.get("qs_rank", 9999)
    qs_note = str(qs) if qs < 9000 else "—"
    return {
        "slug": slug,
        "name_fa": _persian_name(name_en),
        "name_en": name_en,
        "city": "",
        "world_rank": str(rank),
        "qs_rank_note": qs_note,
        "website": "",
        "mo_science": True,
        "mo_health": any(k in name_en.lower() for k in ("medical", "health", "medicine")),
    }


def build_world_country_catalog(
    country_code: str,
    *,
    existing_slugs: set[str] | None = None,
    use_cache: bool = True,
    max_wiki_extras: int = 80,
) -> list[dict]:
    """کاتالوگ یک کشور جهانی: اول QS، سپس ویکی‌پدیا."""
    if country_code in SKIP_COUNTRY_CODES:
        return []
    existing_slugs = set(existing_slugs or set())
    qs_rows = [r for r in fetch_qs_institutions() if r["country_code"] == country_code]
    entries: list[dict] = []
    seen_slugs = set(existing_slugs)
    rank = 1
    for row in sorted(qs_rows, key=lambda r: r["qs_rank"]):
        entry = _entry_from_qs(row, rank=rank)
        slug = entry["slug"]
        if slug in seen_slugs:
            continue
        seen_slugs.add(slug)
        entries.append(entry)
        rank += 1

    wiki_extras = build_catalog_entries(
        country_code,
        existing_slugs=seen_slugs,
        start_rank=max(rank, 31),
        use_cache=use_cache,
    )
    entries.extend(wiki_extras[:max_wiki_extras])

    if len(entries) < 5:
        for row in WORLD_CURATED_TOP.get(country_code, []):
            name_en = row["name_en"]
            slug = _slug_for_name(name_en)
            if slug in seen_slugs:
                continue
            seen_slugs.add(slug)
            qs = row.get("qs_rank", 9999)
            entries.append(
                _entry_from_qs(
                    {"name_en": name_en, "country_code": country_code, "qs_rank": qs},
                    rank=len(entries) + 1,
                )
            )

    return entries


def get_all_world_catalogs(
    *,
    use_cache: bool = True,
    refresh_qs: bool = False,
    max_wiki_extras: int = 60,
) -> dict[str, list[dict]]:
    if refresh_qs:
        fetch_qs_institutions(refresh=True)
    all_slugs: set[str] = set()
    catalogs: dict[str, list[dict]] = {}
    for code in WORLD_STUDY_COUNTRY_CODES:
        cat = build_world_country_catalog(
            code,
            existing_slugs=all_slugs,
            use_cache=use_cache,
            max_wiki_extras=max_wiki_extras,
        )
        for u in cat:
            all_slugs.add(u["slug"])
        catalogs[code] = cat
    return catalogs


def get_world_country_label(country_code: str) -> str:
    return WORLD_STUDY_COUNTRY_LABELS.get(country_code, country_code)
