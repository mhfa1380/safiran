"""
پیشنهاد اصلاح غلط املایی در جستجوی سراسری — «آیا منظورتان … است؟»
"""
from __future__ import annotations

import difflib
import re
from functools import lru_cache

from django.core.cache import cache

from .faq_search import (
    _SYNONYM_GROUPS,
    _fuzzy_ratio,
    _normalize_persian,
    _normalize_query,
    _words,
    tokenize_query,
)
from .models import BlogPost, FAQ, Major, Service, StudyCountry, University
from .site_navigation import get_searchable_page_defs
from .site_search import SearchHit

_VOCAB_CACHE_KEY = "site_search_vocab:v2"
_VOCAB_PHRASES_CACHE_KEY = "site_search_phrases:v2"
_VOCAB_CACHE_TIMEOUT = 60 * 60

_MIN_QUERY_LEN = 3
_MIN_WORD_CORRECTION_LEN = 4
# آستانهٔ پایین‌تر برای غلط‌های شدیدتر (عبارت کامل)
_MIN_PHRASE_RATIO = 0.58
_MIN_WORD_RATIO = 0.62
_STRONG_WORD_RATIO = 0.76
_MAX_SUGGEST_RATIO = 0.98

# واژه‌های پرکاربرد که به‌تنهایی پیشنهاد اشتباه می‌دهند (مثل «تخصصی» از عنوان‌ها)
_CORRECTION_STOPWORDS = frozenset(
    {
        "تخصصی",
        "رایگان",
        "اولیه",
        "تحصیلی",
        "موسسه",
        "دانشگاه",
        "کشور",
        "خدمات",
        "خدمت",
        "صفحه",
        "سایت",
        "مقاله",
        "وبلاگ",
        "سوال",
        "پاسخ",
        "دوره",
        "رشته",
        "تحصیل",
        "پذیرش",
        "ویزا",
        "بورسیه",
        "حضوری",
        "غیرحضوری",
        "طبق",
        "قرارداد",
        "ارزیابی",
        "فرم",
        "تماس",
        "جلسه",
        "هزینه",
        "قیمت",
        "مدرک",
        "مدارک",
        "زبان",
        "انگلیسی",
        "خارجی",
        "ایران",
        "دانشجو",
        "دانشجویی",
        "اپلای",
        "apply",
    }
)


def _enhanced_fuzzy_ratio(a: str, b: str) -> float:
    """تطابق تقریبی با پنجرهٔ جزئی — برای غلط املای شدیدتر."""
    if not a or not b:
        return 0.0
    a = a.lower()
    b = b.lower()
    if a == b:
        return 1.0
    if a in b or b in a:
        shorter, longer = (a, b) if len(a) <= len(b) else (b, a)
        return 0.88 + 0.12 * (len(shorter) / max(len(longer), 1))

    base = difflib.SequenceMatcher(None, a, b).ratio()
    if len(a) > len(b):
        a, b = b, a
    partial = 0.0
    if len(b) >= len(a):
        win = len(a)
        for i in range(0, len(b) - win + 1):
            chunk = b[i : i + win]
            partial = max(partial, difflib.SequenceMatcher(None, a, chunk).ratio())
    return max(base, partial * 0.96)


def _add_term(bucket: set[str], raw: str) -> None:
    text = _normalize_persian(raw or "").strip().lower()
    if len(text) < 2:
        return
    bucket.add(text)
    for word in _words(text):
        if len(word) >= 2:
            bucket.add(word)


def _add_phrase(bucket: set[str], raw: str, *, max_len: int = 80) -> None:
    text = _normalize_persian(raw or "").strip().lower()
    if len(text) < 4:
        return
    text = re.sub(r"\s+", " ", text)
    if len(text) > max_len:
        text = text[:max_len].rsplit(" ", 1)[0].strip()
    if len(text) >= 4:
        bucket.add(text)


def _build_vocabulary() -> frozenset[str]:
    terms: set[str] = set()

    for group in _SYNONYM_GROUPS:
        for word in group:
            _add_term(terms, word)

    for defn in get_searchable_page_defs():
        _add_term(terms, defn.label)
        _add_term(terms, defn.search_subtitle)
        _add_term(terms, defn.search_keywords)

    for title in Service.objects.filter(is_active=True).values_list("title", flat=True)[:400]:
        _add_term(terms, title)
    for row in Service.objects.filter(is_active=True).values_list("search_keywords", flat=True)[:400]:
        _add_term(terms, row or "")

    for question in FAQ.objects.filter(is_active=True).values_list("question", flat=True)[:500]:
        _add_term(terms, question)
    for row in FAQ.objects.filter(is_active=True).values_list("search_keywords", flat=True)[:500]:
        _add_term(terms, row or "")

    for name in StudyCountry.objects.filter(is_active=True).values_list("name", flat=True):
        _add_term(terms, name)

    for title in Major.objects.filter(is_active=True).values_list("title", flat=True)[:600]:
        _add_term(terms, title)

    for name in University.objects.values_list("name_fa", flat=True)[:400]:
        _add_term(terms, name)

    for title in BlogPost.objects.filter(is_published=True).values_list("title", flat=True)[:200]:
        _add_term(terms, title)

    return frozenset(terms)


def _build_phrase_vocabulary() -> frozenset[str]:
    """عبارت‌های کامل برای اصلاح هوشمندتر (نه تک‌واژه‌های عمومی)."""
    phrases: set[str] = set()

    for defn in get_searchable_page_defs():
        _add_phrase(phrases, defn.label)

    for title in Service.objects.filter(is_active=True).values_list("title", flat=True)[:400]:
        _add_phrase(phrases, title)

    for question in FAQ.objects.filter(is_active=True).values_list("question", flat=True)[:500]:
        _add_phrase(phrases, question, max_len=90)

    for name in StudyCountry.objects.filter(is_active=True).values_list("name", flat=True):
        _add_phrase(phrases, f"تحصیل در {name}")

    for title in Major.objects.filter(is_active=True).values_list("title", flat=True)[:400]:
        _add_phrase(phrases, title)

    for name in University.objects.values_list("name_fa", flat=True)[:300]:
        _add_phrase(phrases, name)

    for title in BlogPost.objects.filter(is_published=True).values_list("title", flat=True)[:150]:
        _add_phrase(phrases, title)

    return frozenset(phrases)


def get_search_vocabulary() -> frozenset[str]:
    cached = cache.get(_VOCAB_CACHE_KEY)
    if cached is not None:
        return cached
    vocab = _build_vocabulary()
    cache.set(_VOCAB_CACHE_KEY, vocab, _VOCAB_CACHE_TIMEOUT)
    return vocab


def get_search_phrases() -> frozenset[str]:
    cached = cache.get(_VOCAB_PHRASES_CACHE_KEY)
    if cached is not None:
        return cached
    phrases = _build_phrase_vocabulary()
    cache.set(_VOCAB_PHRASES_CACHE_KEY, phrases, _VOCAB_CACHE_TIMEOUT)
    return phrases


def invalidate_search_vocabulary_cache() -> None:
    cache.delete(_VOCAB_CACHE_KEY)
    cache.delete(_VOCAB_PHRASES_CACHE_KEY)


def _is_stopword_correction(term: str, ratio: float) -> bool:
    if term not in _CORRECTION_STOPWORDS:
        return False
    return ratio < 0.9


def _normalize_suggestion(text: str) -> str:
    text = _normalize_persian(text or "").strip().lower()
    text = re.sub(r"\([^)]*\)", "", text)
    text = re.sub(r"[؟?!.،,;:]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _should_skip_correction(
    q_lower: str,
    correction: str | None,
    *,
    hits: list[SearchHit] | None = None,
) -> bool:
    """فقط وقتی پیشنهاد نده که جستجو از قبل همان چیزی است که کاربر می‌خواهد."""
    if not correction:
        return True
    correction = _normalize_suggestion(correction)
    if not correction or correction == q_lower:
        return True
    if q_lower in get_search_phrases():
        return True
    ratio = _enhanced_fuzzy_ratio(q_lower, correction)
    if ratio >= 0.995:
        return True
    if ratio >= 0.93 and not _needs_typo_fix(q_lower, correction):
        return True
    tokens = tokenize_query(q_lower)
    if len(tokens) == 1 and hits:
        exact = tokens[0]
        if exact in _words(correction) and correction != exact:
            if _query_in_hits(exact, hits) or exact in get_search_vocabulary():
                return True
    return False


def _trim_suggestion(q_lower: str, correction: str) -> str:
    correction = _normalize_suggestion(correction)
    if not correction:
        return correction
    max_len = max(36, int(len(q_lower) * 1.8))
    if len(correction) <= max_len:
        return correction
    aligned = _align_tokens_to_phrase(q_lower, correction)
    if aligned:
        return aligned
    return correction[:max_len].rsplit(" ", 1)[0].strip() or correction[:max_len]


def _needs_typo_fix(a: str, b: str) -> bool:
    return _normalize_persian(a).lower() != _normalize_persian(b).lower()


def _word_correction_allowed(term: str, q_lower: str, ratio: float) -> bool:
    if len(term) < _MIN_WORD_CORRECTION_LEN:
        return False
    if _is_stopword_correction(term, ratio):
        return False
    if term == q_lower:
        return False
    if ratio < _MIN_WORD_RATIO:
        return False
    if ratio >= _MAX_SUGGEST_RATIO and not _needs_typo_fix(q_lower, term):
        return False
    # واژهٔ خیلی کوتاه‌تر از عبارت جستجو معمولاً اشتباه است
    if len(q_lower) >= 6 and len(term) <= len(q_lower) - 3 and ratio < 0.82:
        return False
    return True


@lru_cache(maxsize=512)
def _best_vocab_match(q_lower: str) -> tuple[str | None, float]:
    if len(q_lower) < _MIN_QUERY_LEN:
        return None, 0.0

    vocab = get_search_vocabulary()
    if q_lower in vocab:
        return None, 1.0

    best_term: str | None = None
    best_ratio = 0.0
    q_len = len(q_lower)

    for term in vocab:
        if len(term) < _MIN_WORD_CORRECTION_LEN or term == q_lower:
            continue
        ratio = _enhanced_fuzzy_ratio(q_lower, term)
        len_diff = abs(len(term) - q_len)
        if len_diff > max(4, int(q_len * 0.5)):
            ratio *= 0.78
        if not _word_correction_allowed(term, q_lower, ratio):
            continue
        if ratio > best_ratio:
            best_ratio = ratio
            best_term = term

    return best_term, best_ratio


@lru_cache(maxsize=256)
def _best_phrase_match(q_lower: str) -> tuple[str | None, float]:
    if len(q_lower) < 4:
        return None, 0.0

    best_phrase: str | None = None
    best_ratio = 0.0
    q_len = len(q_lower)

    candidates = get_search_phrases()
    # عناوین نتایج در زمان اجرا اضافه می‌شوند؛ اینجا فقط واژگان پایگاه
    for phrase in candidates:
        if phrase == q_lower or len(phrase) < 4:
            continue
        ratio = _enhanced_fuzzy_ratio(q_lower, phrase)
        if abs(len(phrase) - q_len) > max(8, int(q_len * 0.65)):
            ratio *= 0.85
        if ratio < _MIN_PHRASE_RATIO:
            continue
        if ratio >= _MAX_SUGGEST_RATIO and not _needs_typo_fix(q_lower, phrase):
            continue
        if ratio > best_ratio:
            best_ratio = ratio
            best_phrase = phrase

    return best_phrase, best_ratio


def _query_in_hits(q_lower: str, hits: list[SearchHit]) -> bool:
    for hit in hits[:10]:
        title = _normalize_persian(hit.title).lower()
        if q_lower in title:
            return True
    return False


def _prefer_synonym_canonical(q_lower: str, term: str) -> str:
    for group in _SYNONYM_GROUPS:
        if term not in group:
            continue
        best_alt = term
        for alt in group:
            if len(alt) < 3 or alt.isascii() or len(alt) <= len(term):
                continue
            if _enhanced_fuzzy_ratio(q_lower, alt) >= 0.62:
                best_alt = alt
        return best_alt
    return term


def _align_tokens_to_phrase(q_lower: str, phrase: str) -> str | None:
    """توکن‌های جستجو را به نزدیک‌ترین واژه‌های عبارت هدف نگاشت کن."""
    q_tokens = tokenize_query(q_lower)
    if not q_tokens:
        return None
    phrase_words = _words(phrase)
    if not phrase_words:
        return None

    mapped: list[str] = []
    changed = False
    for qt in q_tokens:
        if len(qt) < _MIN_QUERY_LEN:
            mapped.append(qt)
            continue
        best_w = qt
        best_r = 0.0
        for pw in phrase_words:
            if len(pw) < _MIN_WORD_CORRECTION_LEN:
                continue
            r = _enhanced_fuzzy_ratio(qt, pw)
            if r > best_r and _word_correction_allowed(pw, qt, r):
                best_r = r
                best_w = pw
        if best_w != qt:
            changed = True
        mapped.append(best_w)

    if not changed:
        return None
    return " ".join(mapped)


def _suggest_phrase_from_hits(q_lower: str, hits: list[SearchHit]) -> str | None:
    best_phrase: str | None = None
    best_score = 0.0

    for hit in hits[:12]:
        for source, weight in ((hit.title, 3.0), (hit.subtitle, 1.2)):
            phrase = _normalize_persian(source or "").strip().lower()
            if len(phrase) < 4:
                continue
            ratio = _enhanced_fuzzy_ratio(q_lower, phrase)
            if ratio < _MIN_PHRASE_RATIO:
                continue
            if ratio >= _MAX_SUGGEST_RATIO and not _needs_typo_fix(q_lower, phrase):
                continue
            score = ratio * weight
            if score > best_score:
                best_score = score
                best_phrase = phrase

    if not best_phrase:
        return None

    aligned = _align_tokens_to_phrase(q_lower, best_phrase)
    if aligned and aligned != q_lower:
        return aligned

    trimmed = _trim_suggestion(q_lower, best_phrase)
    if trimmed and trimmed != q_lower:
        return trimmed
    return None


def _suggest_from_hits(q_lower: str, hits: list[SearchHit]) -> str | None:
    phrase = _suggest_phrase_from_hits(q_lower, hits)
    if phrase:
        return phrase

    scores: dict[str, float] = {}
    for hit in hits[:15]:
        for source, weight in ((hit.title, 2.2), (hit.subtitle, 1.0)):
            for word in _words(source or ""):
                if len(word) < _MIN_WORD_CORRECTION_LEN or word == q_lower:
                    continue
                ratio = _enhanced_fuzzy_ratio(q_lower, word)
                if not _word_correction_allowed(word, q_lower, ratio):
                    continue
                scores[word] = scores.get(word, 0.0) + ratio * weight

    if not scores:
        return None

    best_word = max(
        scores.keys(),
        key=lambda word: (scores[word], len(word), _enhanced_fuzzy_ratio(q_lower, word)),
    )
    return _prefer_synonym_canonical(q_lower, best_word)


def _correction_in_hits(term: str, hits: list[SearchHit]) -> bool:
    term_l = term.lower()
    for hit in hits[:12]:
        haystack = f"{hit.title} {hit.subtitle}".lower()
        if term_l in haystack:
            return True
        if _enhanced_fuzzy_ratio(term_l, haystack) >= 0.72:
            return True
    return False


def _pick_best_candidate(
    q_lower: str,
    *,
    hits: list[SearchHit] | None,
) -> str | None:
    candidates: list[tuple[float, str]] = []

    if hits:
        from_hits = _suggest_from_hits(q_lower, hits)
        if from_hits and from_hits != q_lower:
            candidates.append(
                (_enhanced_fuzzy_ratio(q_lower, from_hits) + 0.12, from_hits)
            )

    phrase, phrase_ratio = _best_phrase_match(q_lower)
    if phrase:
        candidates.append((phrase_ratio + 0.08, phrase))

    term, word_ratio = _best_vocab_match(q_lower)
    if term:
        term = _prefer_synonym_canonical(q_lower, term)
        candidates.append((word_ratio, term))

    if not candidates:
        return None

    candidates.sort(key=lambda item: (-item[0], -len(item[1])))
    best_score, best = candidates[0]

    if hits and _query_in_hits(q_lower, hits):
        if not _correction_in_hits(best, hits) and best_score < 0.78:
            return None

    min_score = _MIN_PHRASE_RATIO if " " in best else _MIN_WORD_RATIO
    if best_score < min_score - 0.04:
        return None

    return best


def suggest_query_correction(
    q: str,
    *,
    hits: list[SearchHit] | None = None,
) -> str | None:
    q_norm = _normalize_query(q)
    if len(q_norm) < _MIN_QUERY_LEN:
        return None

    q_lower = q_norm.lower()
    tokens = tokenize_query(q_norm)

    if len(tokens) > 1:
        corrected_tokens: list[str] = []
        any_change = False
        for token in tokens:
            if len(token) < _MIN_QUERY_LEN:
                corrected_tokens.append(token)
                continue
            term, ratio = _best_vocab_match(token)
            if term and _word_correction_allowed(term, token, ratio):
                corrected_tokens.append(_prefer_synonym_canonical(token, term))
                any_change = True
            else:
                corrected_tokens.append(token)
        if any_change:
            phrase = _trim_suggestion(q_lower, " ".join(corrected_tokens))
            if not _should_skip_correction(q_lower, phrase, hits=hits):
                return phrase
        if hits:
            phrase = _suggest_phrase_from_hits(q_lower, hits)
            if phrase and not _should_skip_correction(q_lower, phrase, hits=hits):
                return phrase
        phrase, phrase_ratio = _best_phrase_match(q_lower)
        if phrase and phrase_ratio >= _MIN_PHRASE_RATIO:
            phrase = _trim_suggestion(q_lower, phrase)
            if not _should_skip_correction(q_lower, phrase, hits=hits):
                return phrase
        return None

    if q_lower in _CORRECTION_STOPWORDS:
        return None

    correction = _pick_best_candidate(q_lower, hits=hits)
    if not correction:
        return None

    correction = _trim_suggestion(q_lower, correction)
    if _should_skip_correction(q_lower, correction, hits=hits):
        return None
    return correction
