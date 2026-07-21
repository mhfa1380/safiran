"""
امتیازدهی و استخراج بینش از وبلاگ برای گزارش ارزیابی.
"""
from __future__ import annotations

import re
from typing import Any

from django.urls import reverse

from .faq_search import _expand_tokens, _fuzzy_ratio, _normalize_persian, tokenize_query
from .models import BlogPost, EvaluationRequest

_BLOG_SCHOLARSHIP_KW = frozenset(
    {
        "بورسیه",
        "اسکالرشیپ",
        "scholarship",
        "fund",
        "فاند",
        "کمک هزینه",
        "کمک‌هزینه",
        "financial aid",
        "tuition waiver",
        "fellowship",
    }
)

_BLOG_VISA_KW = frozenset({"ویزا", "visa", "اقامت", "permis", "permit"})
_BLOG_ADMISSION_KW = frozenset({"پذیرش", "admission", "apply", "اپلای", "deadline", "ددلاین"})

_BLOG_DEGREE_KW: dict[str, frozenset[str]] = {
    EvaluationRequest.DEGREE_BACHELOR: frozenset(
        {"کارشناسی", "لیسانس", "bachelor", "undergraduate", "لیسانس"}
    ),
    EvaluationRequest.DEGREE_MASTER: frozenset(
        {"ارشد", "فوق", "master", "mba", "msc", "ma "}
    ),
    EvaluationRequest.DEGREE_PHD: frozenset(
        {"دکتری", "phd", "دکترا", "فاند", "research", "پژوهش"}
    ),
}

_TOURISM_KW = frozenset({"گردشگری", "سفر", "جاذبه", "دیدنی", "تور", "گردشگر", "تفریح"})

_COUNTRY_TAG_MAP = {
    "china": frozenset({"china", "چین", "chinese"}),
    "canada": frozenset({"canada", "کانادا"}),
    "spain": frozenset({"spain", "اسپانیا", "spanish"}),
    "germany": frozenset({"germany", "آلمان", "german"}),
    "italy": frozenset({"italy", "ایتالیا", "italian"}),
}


def load_blog_catalog(limit: int = 80) -> list[dict[str, Any]]:
    return list(
        BlogPost.objects.filter(is_published=True)
        .values(
            "id",
            "title",
            "slug",
            "excerpt",
            "content",
            "country_tag",
            "meta_keywords",
            "image",
            "created_at",
        )
        .order_by("-created_at")[:limit]
    )


def _blog_blob(row: dict[str, Any]) -> str:
    parts = [
        row.get("title") or "",
        row.get("excerpt") or "",
        (row.get("content") or "")[:1600],
        row.get("meta_keywords") or "",
        row.get("country_tag") or "",
    ]
    return _normalize_persian(" ".join(parts)).lower()


def _country_in_blog(row: dict[str, Any], country_code: str, country_name: str) -> bool:
    blob = _blog_blob(row)
    tag = _normalize_persian(row.get("country_tag") or "").lower()
    if country_code in tag or (country_name and country_name in tag):
        return True
    for hint in _COUNTRY_TAG_MAP.get(country_code, frozenset()):
        if hint in blob or hint in tag:
            return True
    return False


def _text_match_score(query: str, hay: str) -> float:
    if not query.strip() or not hay:
        return 0.0
    tokens = _expand_tokens(tokenize_query(query))
    if not tokens:
        tokens = [_normalize_persian(query).lower()]
    scores: list[float] = []
    for token in tokens:
        if token in hay:
            scores.append(1.0)
            continue
        best = 0.0
        for word in re.split(r"[\s,،؛/]+", hay):
            if len(word) < 2:
                continue
            best = max(best, _fuzzy_ratio(token, word))
        scores.append(best)
    if not scores:
        return 0.0
    avg = sum(scores) / len(scores)
    hit_ratio = sum(1 for s in scores if s >= 0.55) / len(scores)
    return min(1.0, avg * 0.75 + hit_ratio * 0.25)


def score_blog_post(
    profile,
    row: dict[str, Any],
    *,
    country_code: str,
    country_name: str,
    scholarship_target: str = "",
) -> tuple[float, list[str], list[str]]:
    """امتیاز، دلایل، برچسب‌های نمایشی."""
    blob = _blog_blob(row)
    title_l = _normalize_persian(row.get("title") or "").lower()
    if any(k in title_l for k in _TOURISM_KW):
        return 0.0, [], []

    score = 0.0
    reasons: list[str] = []
    badges: list[str] = []

    if _country_in_blog(row, country_code, country_name):
        score += 24.0
        reasons.append(f"مرتبط با {country_name or country_code}")
        badges.append("کشور")

    field_match = _text_match_score(profile.study_text, blob)
    if field_match >= 0.45:
        score += field_match * 32.0
        reasons.append("هم‌خوان با رشته/علاقه تحصیلی شما")
        badges.append("رشته")

    if profile.desired_text:
        dm = _text_match_score(profile.desired_text, blob)
        if dm >= 0.5:
            score += dm * 14.0
            reasons.append("نزدیک به رشته مورد علاقه")

    for cluster in profile.clusters:
        if cluster in blob or cluster.replace("_", " ") in blob:
            score += 5.0
            if "حوزه تحصیلی" not in " ".join(reasons):
                reasons.append("مربوط به حوزه تحصیلی شما")
            break

    if profile.is_graduate_track:
        if any(k in blob for k in _BLOG_DEGREE_KW[EvaluationRequest.DEGREE_MASTER]):
            score += 8.0
            reasons.append("مناسب مسیر ارشد/تحصیلات تکمیلی")
        if any(k in blob for k in _BLOG_DEGREE_KW[EvaluationRequest.DEGREE_PHD]):
            score += 6.0

    target_level = scholarship_target or ""
    if not target_level and profile.target_degree_level >= 3:
        target_level = EvaluationRequest.DEGREE_MASTER
    elif not target_level and profile.target_degree_level == 2:
        target_level = EvaluationRequest.DEGREE_BACHELOR

    degree_kws = _BLOG_DEGREE_KW.get(target_level, frozenset())
    if degree_kws and any(k in blob for k in degree_kws):
        score += 10.0
        reasons.append("متناسب با مقطع هدف شما")

    if any(k in blob for k in _BLOG_SCHOLARSHIP_KW):
        score += 14.0
        reasons.append("شامل نکات بورسیه و کمک‌هزینه")
        badges.append("بورسیه")
        if scholarship_target or profile.eval_req.has_financial_capacity:
            score += 6.0

    if any(k in blob for k in _BLOG_VISA_KW):
        score += 5.0
    if any(k in blob for k in _BLOG_ADMISSION_KW):
        score += 5.0

    if profile.research_score >= 2 and any(
        k in blob for k in ("پژوهش", "research", "thesis", "رساله", "مقاله")
    ):
        score += 8.0
        reasons.append("مفید برای سوابق پژوهشی")

    # تازگی — مطالب جدیدتر کمی اولویت دارند
    score += 2.0

    reasons = list(dict.fromkeys(reasons))[:4]
    badges = list(dict.fromkeys(badges))[:3]
    return score, reasons, badges


def blog_country_hints(
    blogs: list[dict[str, Any]],
    profile,
    country_labels: dict[str, str],
    active_codes: frozenset[str],
) -> dict[str, float]:
    hints: dict[str, float] = {}
    for code in active_codes:
        if code == "other":
            continue
        name = country_labels.get(code, "")
        total = 0.0
        for row in blogs:
            s, _, _ = score_blog_post(
                profile, row, country_code=code, country_name=name
            )
            if s >= 12:
                total += min(s * 0.15, 4.0)
        if total:
            hints[code] = total
    return hints


def serialize_blog(
    row: dict[str, Any],
    *,
    score: float,
    reasons: list[str],
    badges: list[str],
) -> dict[str, Any]:
    image_url = ""
    image_name = row.get("image") or ""
    if image_name:
        try:
            from django.core.files.storage import default_storage

            image_url = default_storage.url(image_name)
        except Exception:
            image_url = ""
    excerpt = (row.get("excerpt") or "").strip()
    if not excerpt:
        plain = re.sub(r"<[^>]+>", " ", row.get("content") or "")
        excerpt = " ".join(plain.split())[:200]
    return {
        "title": row["title"],
        "slug": row["slug"],
        "excerpt": excerpt[:200],
        "image_url": image_url,
        "score": round(score, 1),
        "reasons": reasons,
        "badges": badges,
        "url": reverse("blog_detail", kwargs={"slug": row["slug"]}),
    }


def pick_scored_blogs(
    blogs: list[dict[str, Any]],
    profile,
    *,
    country_code: str,
    country_name: str,
    scholarship_target: str = "",
    limit: int = 6,
    min_score: float = 10.0,
) -> list[dict[str, Any]]:
    scored: list[tuple[float, dict[str, Any], list[str], list[str]]] = []
    for row in blogs:
        s, reasons, badges = score_blog_post(
            profile,
            row,
            country_code=country_code,
            country_name=country_name,
            scholarship_target=scholarship_target,
        )
        if s >= min_score:
            scored.append((s, row, reasons, badges))
    scored.sort(key=lambda x: -x[0])
    return [
        serialize_blog(r, score=s, reasons=rs, badges=bd)
        for s, r, rs, bd in scored[:limit]
    ]


def _trim_excerpt(text: str, max_len: int = 240) -> str:
    text = " ".join((text or "").split())
    if len(text) <= max_len:
        return text
    cut = text[:max_len]
    for sep in (" ", "،", ".", "؛", "؟"):
        idx = cut.rfind(sep)
        if idx > max_len // 2:
            return cut[:idx].rstrip() + "…"
    return cut.rstrip() + "…"


def blog_insights(
    blogs: list[dict[str, Any]],
    profile,
    *,
    country_code: str,
    country_name: str,
    scholarship_target: str = "",
    limit: int = 3,
    excerpt_max_len: int = 110,
) -> list[dict[str, Any]]:
    """پیشنهادهای وبلاگ برای بلوک «نکات کلیدی» — با عنوان، خلاصه و لینک."""
    picks = pick_scored_blogs(
        blogs,
        profile,
        country_code=country_code,
        country_name=country_name,
        scholarship_target=scholarship_target,
        limit=limit + 2,
        min_score=14.0,
    )
    out: list[dict[str, Any]] = []
    for post in picks:
        title = (post.get("title") or "").strip()
        excerpt = _trim_excerpt((post.get("excerpt") or "").strip(), max_len=excerpt_max_len)
        url = (post.get("url") or "").strip()
        if not title or not excerpt or not url:
            continue
        reason = (post.get("reasons") or [""])[0]
        badges = post.get("badges") or []
        is_scholarship = "بورسیه" in reason or "بورسیه" in badges
        out.append(
            {
                "title": title,
                "excerpt": excerpt,
                "url": url,
                "slug": post.get("slug") or "",
                "reason": reason,
                "is_scholarship": is_scholarship,
            }
        )
        if len(out) >= limit:
            break
    return out
