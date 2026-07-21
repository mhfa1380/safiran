"""
لیست رشته‌های تحصیلی برای فرم ارزیابی (جستجو / پیشنهاد خودکار).

منبع ترکیبی: ISCED-F 2013 (UNESCO) و گروه‌های رایج رشته در دانشگاه‌های ایران.
"""

from __future__ import annotations

EVALUATION_MAJOR_SUGGESTIONS: tuple[str, ...] = (
    "آمار",
    "آمار زیستی",
    "آموزش ابتدایی",
    "آموزش ریاضی",
    "آموزش زبان انگلیسی",
    "آموزش علوم تجربی",
    "آموزش هنر",
    "آموزش کودکان استثنایی",
    "آموزش و پرورش ابتدایی",
    "آموزش و پرورش پیش‌دبستانی",
    "آهنگسازی",
    "اتاق عمل",
    "ادبیات انگلیسی",
    "ادبیات فارسی",
    "ادبیات عرب",
    "ارتوز و پروتز",
    "ارگونومی",
    "اقتصاد",
    "اقتصاد بین‌الملل",
    "اقتصاد کشاورزی",
    "امنیت ملی",
    "امور بانکی",
    "امور بین‌الملل",
    "امنیت سایبری",
    "امور تربیتی",
    "امور شهری و محیط زیست",
    "انرژی",
    "اپیدمیولوژی",
    "ایمنی‌شناسی",
    "باستان‌شناسی",
    "بازاریابی",
    "بهداشت عمومی",
    "برنامه‌ریزی شهری",
    "برنامه‌ریزی سیستم‌های اقتصادی",
    "بیمارستان‌داری",
    "بیوتکنولوژی",
    "بیولوژی",
    "بیولوژی سلولی مولکولی",
    "بیومکانیک",
    "بیومدیکال",
    "بیومهندسی",
    "بیوانفورماتیک",
    "پرستاری",
    "پزشکی",
    "پزشکی اجتماعی",
    "پزشکی ورزشی",
    "پلیمر",
    "تاریخ",
    "تاریخ اسلام",
    "تربیت بدنی",
    "تربیت بدنی و علوم ورزشی",
    "ترجمه",
    "تغذیه",
    "تکنولوژی آموزشی",
    "تکنولوژی اطلاعات",
    "تکنولوژی غذایی",
    "تکنولوژی نفت",
    "تکنولوژی‌های نوین پزشکی",
    "جامعه‌شناسی",
    "جغرافیا",
    "جغرافیا و برنامه‌ریزی شهری",
    "جغرافیا و برنامه‌ریزی روستایی",
    "جمعیت‌شناسی",
    "حسابداری",
    "حقوق",
    "حقوق بین‌الملل",
    "حقوق جزا و جرم‌شناسی",
    "حقوق تجارت بین‌الملل",
    "حفاظت محیط زیست",
    "حفاظت و مرمت آثار تاریخی",
    "خبرنگاری",
    "خاک‌شناسی",
    "داروسازی",
    "دامپزشکی",
    "دبیری زیست‌شناسی",
    "دبیری فیزیک",
    "دبیری شیمی",
    "دبیری ریاضی",
    "دبیری زبان انگلیسی",
    "دبیری علوم تجربی",
    "دندانپزشکی",
    "راه و ساختمان",
    "روان‌شناسی",
    "روان‌شناسی بالینی",
    "روان‌شناسی تربیتی",
    "روان‌شناسی صنعتی و سازمانی",
    "روان‌شناسی شناختی",
    "روابط عمومی",
    "ریاضی",
    "ریاضی کاربردی",
    "زبان و ادبیات انگلیسی",
    "زبان و ادبیات آلمانی",
    "زبان و ادبیات فرانسه",
    "زبان‌شناسی",
    "زبان‌شناسی کاربردی",
    "زمین‌شناسی",
    "زیست‌شناسی",
    "زیست‌شناسی دریا",
    "زیست‌فناوری",
    "زیست‌فناوری پزشکی",
    "علوم اعصاب",
    "علوم داده",
    "علوم شناختی",
    "ساختمان",
    "ساختمان‌های آبی",
    "سنجش از دور و GIS",
    "سیاست‌گذاری عمومی",
    "سینما",
    "شهرسازی",
    "شیلات",
    "شیمی",
    "شیمی آلی",
    "شیمی تجزیه",
    "شیمی فیزیک",
    "شیمی کاربردی",
    "صنایع",
    "صنایع غذایی",
    "صنایع نفت",
    "طراحی صنعتی",
    "طراحی شهری",
    "طراحی لباس",
    "طراحی گرافیک",
    "طراحی محیط",
    "طراحی بازی و رسانه‌های تعاملی",
    "علوم اجتماعی",
    "علوم اقتصادی",
    "علوم تربیتی",
    "علوم تربیتی — برنامه‌ریزی آموزشی",
    "علوم تربیتی — مدیریت آموزشی",
    "علوم تربیتی — مشاوره",
    "علوم سیاسی",
    "علوم قرآن و حدیث",
    "علوم قضایی",
    "علوم کتابداری و اطلاع‌رسانی",
    "علوم کامپیوتر",
    "علوم کامپیوتر — نرم‌افزار",
    "علوم کامپیوتر — سخت‌افزار",
    "علوم کامپیوتر — هوش مصنوعی",
    "علوم کامپیوتر — امنیت اطلاعات",
    "علوم کامپیوتر — شبکه",
    "علوم کشاورزی",
    "علوم دامی",
    "علوم زیستی",
    "علوم ارتباطات",
    "فقه و مبانی حقوق اسلامی",
    "فلسفه",
    "فلسفه و حکمت اسلامی",
    "فناوری اطلاعات",
    "فناوری اطلاعات سلامت",
    "فناوری نانو",
    "فیزیوتراپی",
    "فیزیک",
    "فیزیک کاربردی",
    "فیزیک مهندسی",
    "فیزیک هسته‌ای",
    "قضاوت",
    "کاردرمانی",
    "کامپیوتر",
    "کامپیوتر — نرم‌افزار",
    "کامپیوتر — سخت‌افزار",
    "کامپیوتر — شبکه",
    "کامپیوتر — هوش مصنوعی",
    "کامپیوتر — امنیت",
    "کامپیوتر — مهندسی نرم‌افزار",
    "کشاورزی",
    "کشاورزی — زراعت",
    "کشاورزی — باغبانی",
    "کشاورزی — علوم دامی",
    "کشاورزی — منابع طبیعی",
    "گرافیک",
    "مددکاری اجتماعی",
    "مدیریت",
    "مدیریت بازرگانی",
    "مدیریت بیمه",
    "مدیریت صنعتی",
    "مدیریت مالی",
    "مدیریت گردشگری",
    "مدیریت دولتی",
    "مدیریت کشاورزی",
    "مدیریت بیمارستان",
    "مدیریت زنجیره تأمین",
    "مدیریت منابع انسانی",
    "MBA و مدیریت کسب‌وکار",
    "مطالعات بین‌فرهنگی",
    "معماری",
    "معماری داخلی",
    "معماری منظر",
    "مهندسی آب",
    "مهندسی اپتیک و لیزر",
    "مهندسی پزشکی",
    "مهندسی پلیمر",
    "مهندسی پتروشیمی",
    "مهندسی نفت",
    "مهندسی نساجی",
    "مهندسی معدن",
    "مهندسی شهرسازی",
    "مهندسی عمران",
    "مهندسی راه و ساختمان",
    "مهندسی رباتیک",
    "مهندسی هوافضا",
    "مهندسی خودرو",
    "مهندسی مکانیک",
    "مهندسی مکاترونیک",
    "مهندسی مواد و متالورژی",
    "مهندسی شیمی",
    "مهندسی صنایع",
    "مهندسی صنایع غذایی",
    "مهندسی کشاورزی",
    "مهندسی منابع طبیعی",
    "مهندسی محیط زیست",
    "مهندسی انرژی",
    "مهندسی برق",
    "مهندسی برق — قدرت",
    "مهندسی برق — الکترونیک",
    "مهندسی برق — مخابرات",
    "مهندسی برق — کنترل",
    "مهندسی کامپیوتر",
    "مهندسی کامپیوتر — نرم‌افزار",
    "مهندسی کامپیوتر — سخت‌افزار",
    "مهندسی کامپیوتر — شبکه",
    "مهندسی کامپیوتر — هوش مصنوعی",
    "مهندسی کامپیوتر — امنیت",
    "مهندسی دریا",
    "مهندسی نرم‌افزار",
    "مهندسی فناوری اطلاعات",
    "مهندسی حمل و نقل",
    "مهندسی ایمنی",
    "مهندسی بهداشت حرفه‌ای",
    "مهندسی بهداشت محیط",
    "مهندسی شیلات",
    "مهندسی جنگل",
    "مهندسی باغبانی",
    "مهندسی ماشین‌های کشاورزی",
    "هنرهای تجسمی",
    "هنرهای نمایشی",
    "هنرهای سنتی",
    "هنر اسلامی",
    "هنرهای دیجیتال",
    "هوانوردی",
    "هوش مصنوعی",
    "عکاسی",
    "موسیقی",
    "نمایش",
    "چاپ",
    "صنایع دستی",
    "فرش",
    "علوم ورزشی",
    "علوم قضایی و خدمات حقوقی",
    "مشاوره",
)


def get_evaluation_major_suggestions() -> list[str]:
    """رشته‌های فعال دیتابیس + لیست مرجع، بدون تکرار."""
    return [item["title"] for item in get_evaluation_major_options()]


def get_evaluation_major_options() -> list[dict[str, object]]:
    """گزینه‌های رشته برای فرم ارزیابی — با کش برای کاهش فشار SQLite هنگام خزش."""
    from django.conf import settings
    from django.core.cache import cache

    from .cache_utils import evaluation_catalog_cache_key

    cache_key = f"{evaluation_catalog_cache_key()}:major_options"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    result = _build_evaluation_major_options()
    ttl = int(getattr(settings, "EVAL_CATALOG_CACHE_SECONDS", 300))
    cache.set(cache_key, result, ttl)
    return result


def _build_evaluation_major_options() -> list[dict[str, object]]:
    """
    گزینه‌های رشته برای فرم ارزیابی: عنوان یکتا + کشورهای مرتبط.
    """
    from .models import Major

    merged: dict[str, set[str]] = {}
    for title, country in Major.objects.filter(is_active=True).values_list("title", "country"):
        t = (title or "").strip()
        if not t:
            continue
        merged.setdefault(t, set())
        if country:
            merged[t].add(country)

    for title in EVALUATION_MAJOR_SUGGESTIONS:
        t = (title or "").strip()
        if t:
            merged.setdefault(t, set())

    country_labels = {"canada": "کانادا", "spain": "اسپانیا", "china": "چین", "other": "سایر"}
    result: list[dict[str, object]] = []
    for title in sorted(merged.keys(), key=lambda s: s.strip()):
        codes = sorted(merged[title])
        result.append(
            {
                "title": title,
                "countries": codes,
                "country_labels": [country_labels.get(c, c) for c in codes],
            }
        )
    return result


# --- جستجوی هوشمند (تطابق تقریبی + مترادف، مشابه صفحه رشته‌ها) ---

_EVAL_SUGGEST_LIMIT = 10
_FUZZY_TYPO_MIN = 0.42
_FUZZY_TYPO_STRONG = 0.62


def _evaluation_option_fields(option: dict[str, object]) -> tuple[str, str]:
    from .faq_search import _normalize_persian

    title = _normalize_persian(str(option.get("title") or "")).lower()
    labels = " ".join(option.get("country_labels") or [])
    haystack = f"{title} {_normalize_persian(labels).lower()}"
    return title, haystack


def _score_evaluation_option(
    option: dict[str, object],
    tokens: list[str],
    full_q: str,
    *,
    selected_countries: list[str] | None = None,
) -> float:
    from .faq_search import _normalize_query, _token_matches, tokenize_query
    from .major_search import _best_query_match, _expand_major_tokens

    if not tokens and not full_q:
        return 0.0

    title, haystack = _evaluation_option_fields(option)
    score = 0.0
    full_lower = _normalize_query(full_q).lower()

    if full_lower:
        if title.startswith(full_lower):
            score += 24.0
        elif full_lower == title:
            score += 22.0
        elif full_lower in title:
            score += 18.0
        elif full_lower in haystack:
            score += 8.0
        else:
            fuzzy = _best_query_match(full_lower, title)
            if fuzzy >= _FUZZY_TYPO_STRONG:
                score += fuzzy * 14.0
            elif fuzzy >= _FUZZY_TYPO_MIN:
                score += fuzzy * 9.8

    core_tokens = tokens or tokenize_query(full_q)
    expanded = _expand_major_tokens(core_tokens)

    if core_tokens and all(
        _token_matches(title, token) >= 0.72 or token in title for token in core_tokens
    ):
        score += 7.0

    core_matched = 0
    for token in core_tokens:
        t_title = max(_token_matches(title, token), _best_query_match(token, title) * 0.95)
        if t_title >= 0.78:
            score += 6.5 * t_title
            core_matched += 1
        elif _token_matches(haystack, token) >= 0.72:
            score += 1.4
        elif _token_matches(haystack, token) >= 0.55:
            score += 0.5

    for token in expanded:
        if token in core_tokens:
            continue
        if _token_matches(title, token) >= 0.78:
            score += 2.0
        elif _token_matches(haystack, token) >= 0.72:
            score += 0.9

    if core_tokens and core_matched == len(core_tokens):
        score += 5.0
    elif core_tokens and core_matched > 0:
        score += core_matched * 0.8

    if selected_countries:
        opt_countries = option.get("countries") or []
        for code in selected_countries:
            if code in opt_countries:
                score += 8.0

    return score


def _fuzzy_fallback_evaluation_options(
    options: list[dict[str, object]],
    q: str,
) -> list[tuple[float, dict[str, object]]]:
    from .faq_search import _normalize_query
    from .major_search import _best_query_match

    q_norm = _normalize_query(q).lower()
    if len(q_norm) < 2:
        return []
    scored: list[tuple[float, dict[str, object]]] = []
    for opt in options:
        title, _haystack = _evaluation_option_fields(opt)
        fuzzy = _best_query_match(q_norm, title)
        if fuzzy >= _FUZZY_TYPO_MIN:
            scored.append((fuzzy * 16.0, opt))
    scored.sort(key=lambda x: (-x[0], str(x[1].get("title") or "")))
    return scored


def suggest_evaluation_majors_ranked(
    q: str = "",
    *,
    country_codes: list[str] | None = None,
    limit: int = _EVAL_SUGGEST_LIMIT,
) -> list[tuple[dict[str, object], float]]:
    """پیشنهاد رشته برای combobox فرم ارزیابی — لیست یکتا از DB + مرجع."""
    from .faq_search import _normalize_query, tokenize_query

    options = get_evaluation_major_options()
    limit = max(1, min(int(limit or _EVAL_SUGGEST_LIMIT), 20))
    countries = [c.strip() for c in (country_codes or []) if c and c not in ("undecided", "other")]

    q_norm = _normalize_query(q)
    if not q_norm or len(q_norm) < 2:
        if countries:
            matched = [
                o
                for o in options
                if not o.get("countries") or any(c in (o.get("countries") or []) for c in countries)
            ]
            pool = matched if matched else options
        else:
            pool = options
        return [(o, 1.0) for o in pool[:limit]]

    tokens = tokenize_query(q_norm)
    scored = [
        (_score_evaluation_option(o, tokens, q_norm, selected_countries=countries), o)
        for o in options
    ]
    scored = [(s, o) for s, o in scored if s > 0]

    if not scored:
        scored = _fuzzy_fallback_evaluation_options(options, q_norm)

    if not scored:
        return []

    scored.sort(
        key=lambda x: (
            -x[0],
            str(x[1].get("title") or ""),
        )
    )
    return [(o, s) for s, o in scored[:limit]]


def suggest_evaluation_majors(
    q: str = "",
    *,
    country_codes: list[str] | None = None,
    limit: int = _EVAL_SUGGEST_LIMIT,
) -> list[dict[str, object]]:
    return [o for o, _ in suggest_evaluation_majors_ranked(q, country_codes=country_codes, limit=limit)]
