"""مقاطع تحصیلی منو — لینک‌های بورسیه، کشور، رشته و دانشگاه."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from django.urls import reverse

from .models import EvaluationRequest


@dataclass(frozen=True)
class DegreeNavLevel:
    key: str
    label: str
    subtitle: str
    prefill_current: str
    scholarship_line: str


DEGREE_NAV_LEVELS: tuple[DegreeNavLevel, ...] = (
    DegreeNavLevel(
        key=EvaluationRequest.DEGREE_BACHELOR,
        label="کارشناسی",
        subtitle="لیسانس و برنامه‌های Undergraduate",
        prefill_current=EvaluationRequest.DEGREE_DIPLOMA,
        scholarship_line="پیشنهاد بورسیه و پذیرش کارشناسی بر اساس پرونده شما",
    ),
    DegreeNavLevel(
        key=EvaluationRequest.DEGREE_MASTER,
        label="کارشناسی ارشد",
        subtitle="Master و برنامه‌های تحصیلات تکمیلی",
        prefill_current=EvaluationRequest.DEGREE_BACHELOR,
        scholarship_line="بورسیه ارشد، Research Assistant و کمک‌هزینه تحصیلی",
    ),
    DegreeNavLevel(
        key=EvaluationRequest.DEGREE_PHD,
        label="دکتری",
        subtitle="PhD و برنامه‌های پژوهشی",
        prefill_current=EvaluationRequest.DEGREE_MASTER,
        scholarship_line="فاند دکتری، بورسیه تحقیقاتی و معرفی به اساتید",
    ),
)

_DEGREE_BY_KEY = {d.key: d for d in DEGREE_NAV_LEVELS}


def get_degree_level(key: str) -> DegreeNavLevel | None:
    return _DEGREE_BY_KEY.get((key or "").strip().lower())


def append_query_params(url: str, params: dict[str, str]) -> str:
    if not url:
        return url
    parsed = urlparse(url)
    existing = dict(parse_qsl(parsed.query, keep_blank_values=True))
    for k, v in params.items():
        if v:
            existing[k] = v
        elif k in existing:
            del existing[k]
    query = urlencode(existing)
    return urlunparse(parsed._replace(query=query))


def build_nav_degree_url(
    url_name: str,
    *,
    target_degree: str = "",
    intent: str = "",
    country: str = "",
    anchor: str = "",
    url_kwargs: dict[str, Any] | None = None,
) -> str:
    """ساخت URL با پارامترهای منوی مقاطع (بورسیه / کشور / رشته)."""
    kwargs = url_kwargs or {}
    base = reverse(url_name, kwargs=kwargs) if kwargs else reverse(url_name)
    q: dict[str, str] = {}
    if target_degree:
        q["target_degree"] = target_degree
    if intent:
        q["intent"] = intent
    if country:
        q["country"] = country
    url = append_query_params(base, q)
    if anchor:
        url = f"{url}#{anchor.lstrip('#')}"
    return url


def parse_nav_degree_params(get) -> dict[str, Any]:
    """خواندن پارامترهای منو از query string برای بنر و پیش‌فرض فرم."""
    raw = (get.get("target_degree") or get.get("degree") or "").strip().lower()
    intent = (get.get("intent") or "").strip().lower()
    level = get_degree_level(raw)
    query = ""
    if level:
        query = urlencode({"target_degree": raw, **({"intent": intent} if intent else {})})
    return {
        "nav_target_degree": raw if level else "",
        "nav_intent": intent,
        "nav_degree_level": level,
        "nav_show_scholarship_banner": bool(level and intent == "scholarship"),
        "nav_degree_prefill": level.prefill_current if level else "",
        "nav_degree_query": query,
    }
