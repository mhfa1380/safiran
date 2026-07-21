"""One-off script: fetch QS top universities and build world catalog JSON."""
from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

UA = "SafiranStudyAbroadBot/1.0 (catalog builder)"
OUT = Path(__file__).resolve().parent.parent / "core" / "seed_data" / "cache" / "qs_world_top500.json"

COUNTRY_MAP = {
    "United States": "usa",
    "United Kingdom": "uk",
    "Australia": "australia",
    "Germany": "germany",
    "France": "france",
    "Netherlands": "netherlands",
    "Switzerland": "switzerland",
    "Japan": "japan",
    "South Korea": "south_korea",
    "Korea, South": "south_korea",
    "Singapore": "singapore",
    "Italy": "italy",
    "Sweden": "sweden",
    "Belgium": "belgium",
    "Denmark": "denmark",
    "Finland": "finland",
    "Norway": "norway",
    "Ireland": "ireland",
    "Austria": "austria",
    "New Zealand": "new_zealand",
    "Hong Kong": "hong_kong",
    "Hong Kong SAR": "hong_kong",
    "Taiwan": "taiwan",
    "Malaysia": "malaysia",
    "Turkey": "turkey",
    "Türkiye": "turkey",
    "United Arab Emirates": "uae",
    "UAE": "uae",
    "Saudi Arabia": "saudi_arabia",
    "Qatar": "qatar",
    "India": "india",
    "Brazil": "brazil",
    "Mexico": "mexico",
    "Argentina": "argentina",
    "Chile": "chile",
    "Poland": "poland",
    "Czech Republic": "czech",
    "Czechia": "czech",
    "Hungary": "hungary",
    "Greece": "greece",
    "Portugal": "portugal",
    "Russia": "russia",
    "Thailand": "thailand",
    "Indonesia": "indonesia",
    "Egypt": "egypt",
    "South Africa": "south_africa",
    "Israel": "israel",
    "Canada": "canada",
    "China": "china",
    "Spain": "spain",
}


def wiki_wikitext(page: str) -> str:
    qs = urllib.parse.urlencode(
        {"action": "parse", "page": page, "prop": "wikitext", "format": "json"}
    )
    req = urllib.request.Request(
        f"https://en.wikipedia.org/w/api.php?{qs}", headers={"User-Agent": UA}
    )
    with urllib.request.urlopen(req, timeout=90) as r:
        data = json.loads(r.read().decode())
    return data["parse"]["wikitext"]["*"]


def parse_qs_tables(text: str) -> list[dict]:
    rows: list[dict] = []
    in_table = False
    for line in text.splitlines():
        if "{|" in line and "wikitable" in line:
            in_table = True
            continue
        if in_table and line.strip() == "|}":
            in_table = False
            continue
        if not in_table or not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.split("|")[1:-1]]
        if len(cells) < 3:
            continue
        rank_raw = re.sub(r"[^0-9=]", "", cells[0].replace("=", ""))
        if not rank_raw or not rank_raw[0].isdigit():
            continue
        rank = rank_raw.lstrip("=").split("=")[0]
        if not rank.isdigit():
            continue
        uni_cell = cells[1] if len(cells) > 1 else ""
        country_cell = cells[2] if len(cells) > 2 else ""
        m_uni = re.search(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", uni_cell)
        m_country = re.search(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", country_cell)
        if not m_uni:
            continue
        name_en = m_uni.group(1).strip()
        country_name = (m_country.group(1).strip() if m_country else country_cell).strip()
        country_name = re.sub(r"<[^>]+>", "", country_name)
        country_name = country_name.replace("[[", "").replace("]]", "")
        rows.append(
            {
                "qs_rank": int(rank),
                "name_en": name_en,
                "country_name": country_name,
                "country_code": COUNTRY_MAP.get(country_name, ""),
            }
        )
    return rows


def dedupe(rows: list[dict]) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    for row in rows:
        key = row["name_en"].lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out


def main() -> None:
    text = wiki_wikitext("QS World University Rankings")
  # Prefer 2025 section if present
    idx = text.find("===2025===")
    if idx < 0:
        idx = text.find("2025")
    chunk = text[idx:] if idx >= 0 else text
    rows = dedupe(parse_qs_tables(chunk))
    if len(rows) < 50:
        rows = dedupe(parse_qs_tables(text))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(rows)} rows to {OUT}")
    by_country: dict[str, int] = {}
    for r in rows:
        c = r.get("country_code") or "?"
        by_country[c] = by_country.get(c, 0) + 1
    print("by country:", dict(sorted(by_country.items(), key=lambda x: -x[1])[:20]))


if __name__ == "__main__":
    main()
