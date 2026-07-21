"""Find GSC performance gaps vs existing SEO overrides."""
from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / "scripts" / "gsc_analysis_output.json").read_text(encoding="utf-8"))

# import overrides without django
overrides_path = ROOT / "core" / "gsc_seo_overrides.py"
text = overrides_path.read_text(encoding="utf-8")
uni_slugs = set(re.findall(r'"([a-z0-9-]+)":\s*\{\s*\n\s*"meta_title"', text.split("MAJOR_OVERRIDES")[0]))
major_section = text.split("MAJOR_OVERRIDES", 1)[1].split("BLOG_OVERRIDES", 1)[0]
major_slugs = set(re.findall(r'"([a-z0-9\u0600-\u06ff-]+)":\s*\{\s*\n\s*"meta_title"', major_section))

pages = DATA["saroshan.ir-Performance-on-Search-2026-05-26.xlsx"]["sheets"]["Pages"]["rows"]

def slug_from_url(url: str) -> tuple[str, str] | None:
    p = urlparse(url)
    path = unquote(p.path.strip("/"))
    if path.startswith("دانشگاه/"):
        return "university", path.split("/", 1)[1]
    if path.startswith("رشته/"):
        return "major", path.split("/", 1)[1]
    if "/blog/" in path:
        m = re.search(r"/blog/([^/]+)/", url)
        return ("blog", m.group(1)) if m else None
    return None

low_ctr = []
missing_uni = []
missing_major = []
for url, clicks, imp, ctr, pos in pages:
    if imp < 8:
        continue
    parsed = slug_from_url(url)
    if not parsed:
        continue
    kind, slug = parsed
    ctr_v = ctr if ctr != "" else 0
    if ctr_v < 0.04:
        low_ctr.append((imp, clicks, ctr_v, pos, kind, slug, url))
    if kind == "university" and slug not in uni_slugs:
        missing_uni.append((imp, slug, url))
    if kind == "major" and slug not in major_slugs:
        missing_major.append((imp, slug, url))

low_ctr.sort(reverse=True)
missing_uni.sort(reverse=True)
missing_major.sort(reverse=True)

out = ROOT / "scripts" / "gsc_gaps.txt"
lines = ["=== TOP LOW CTR (imp>=8, CTR<4%) ==="]
lines += [repr(row) for row in low_ctr[:30]]
lines += ["\n=== UNIVERSITIES IN GSC NOT IN OVERRIDES (imp>=8) ==="]
lines += [repr(row) for row in missing_uni]
lines += ["\n=== MAJORS IN GSC NOT IN OVERRIDES (imp>=8) ==="]
lines += [repr(row) for row in missing_major[:25]]
out.write_text("\n".join(lines), encoding="utf-8")
print("wrote", out)
