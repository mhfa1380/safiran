"""لینک نتایج جستجو با پارامتر highlight برای هایلایت در صفحه مقصد."""
from __future__ import annotations

import re
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

_ARABIC_TO_PERSIAN = str.maketrans(
    {
        "ي": "ی",
        "ى": "ی",
        "ك": "ک",
        "ة": "ه",
    }
)


def _normalize_highlight_query(q: str) -> str:
    text = (q or "").strip().translate(_ARABIC_TO_PERSIAN)
    text = text.replace("\u200c", " ").replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def append_highlight_param(url: str, query: str) -> str:
    """به URL مقصد ?highlight=... اضافه می‌کند (بدون حذف پارامترهای موجود)."""
    q = _normalize_highlight_query(query)
    if not q or not url:
        return url
    parsed = urlparse(url)
    params = [(k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True) if k != "highlight"]
    params.append(("highlight", q))
    new_query = urlencode(params)
    return urlunparse(parsed._replace(query=new_query))
