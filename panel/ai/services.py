"""Case AI analyze + personalized stage script via MiMo."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from django.conf import settings
from django.utils import timezone

from panel.ai.context import build_case_context, context_hash
from panel.ai.mimo import MimoError, chat_completion
from panel.models import CustomerCase
from panel.services import STAGE_SCRIPTS

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """تو دستیار کال‌سنتر موسسه اعزام دانشجوی «سفیران آینده روشن» هستی.
مخاطب خروجی: اپراتور فارسی‌زبان که الان می‌خواهد تلفنی صحبت کند (نه مشتری).
قواعد:
- فقط از داده‌های داده‌شده استفاده کن؛ حدس نزن. اگر چیزی نیست بنویس «نامشخص».
- کوتاه، عملی، محترمانه.
- خروجی را فقط JSON معتبر بده، بدون markdown و بدون توضیح اضافه.
ساختار JSON:
{
  "profile": "یک جمله پروفایل مشتری",
  "strengths": ["..."],
  "risks": ["..."],
  "next_action": "یک اقدام مشخص برای همین تماس/امروز",
  "tone": "کوتاه|صمیمی|رسمی",
  "script_lines": ["سوال1", "سوال2", "..."]
}
script_lines باید ۶ تا ۱۰ مورد باشد: دقیقاً سوال‌ها و چیزهایی که اپراتور در این تماس باید بپرسد یا چک کند.
مثال سبک: «معدل آخرین مدرک‌تان چند است؟» / «مدرک زبان دارید یا در حال آماده‌اید؟» / «بودجه تقریبی‌تان چقدر است؟»
جملات تبلیغاتی واتساپ ننویس. پیام آماده برای ارسال به مشتری ننویس. فقط چک‌لیست سوال تماس برای اپراتور.
سوال‌ها را با توجه به مرحله فعلی و جاهای خالی فرم شخصی‌سازی کن (چیزی که از قبل معلوم است را دوباره نپرس؛ به‌جایش تایید یا جزئیات بعدی بپرس).
"""


def _extract_json(text: str) -> dict[str, Any]:
    text = (text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        data = json.loads(match.group(0))
        if isinstance(data, dict):
            return data
    raise ValueError("JSON parse failed")


def _normalize_payload(raw: dict[str, Any], case: CustomerCase) -> dict[str, Any]:
    strengths = raw.get("strengths") or []
    risks = raw.get("risks") or []
    scripts = raw.get("script_lines") or []
    if not isinstance(strengths, list):
        strengths = [str(strengths)]
    if not isinstance(risks, list):
        risks = [str(risks)]
    if not isinstance(scripts, list):
        scripts = [str(scripts)]

    strengths = [str(x).strip() for x in strengths if str(x).strip()][:5]
    risks = [str(x).strip() for x in risks if str(x).strip()][:5]
    scripts = [str(x).strip() for x in scripts if str(x).strip()][:8]
    if not scripts:
        scripts = list(STAGE_SCRIPTS.get(case.stage, []))

    return {
        "profile": str(raw.get("profile") or "").strip() or "اطلاعات کافی برای پروفایل نیست.",
        "strengths": strengths,
        "risks": risks,
        "next_action": str(raw.get("next_action") or "").strip() or "با مشتری تماس بگیرید و نیاز را روشن کنید.",
        "tone": str(raw.get("tone") or "کوتاه").strip(),
        "script_lines": scripts,
        "fallback": False,
    }


def _fallback_payload(case: CustomerCase, reason: str = "") -> dict[str, Any]:
    return {
        "profile": f"{case.customer.full_name} — مرحله {case.get_stage_display()}",
        "strengths": [],
        "risks": [reason] if reason else [],
        "next_action": "طبق اسکریپت ثابت مرحله پیش بروید.",
        "tone": "کوتاه",
        "script_lines": list(STAGE_SCRIPTS.get(case.stage, [])),
        "fallback": True,
        "error": reason,
    }


def ai_enabled() -> bool:
    if not getattr(settings, "PANEL_AI_ENABLED", True):
        return False
    return bool((getattr(settings, "MIMO_API_KEY", "") or "").strip())


def get_cached_ai(case: CustomerCase, *, ctx_hash: str | None = None) -> dict[str, Any] | None:
    payload = case.ai_payload if isinstance(case.ai_payload, dict) else {}
    if not payload or not payload.get("script_lines"):
        return None
    if ctx_hash and case.ai_context_hash and case.ai_context_hash != ctx_hash:
        return None
    return payload


def analyze_case(case: CustomerCase, *, force: bool = False) -> dict[str, Any]:
    context = build_case_context(case)
    ctx_hash = context_hash(context)

    if not force:
        cached = get_cached_ai(case, ctx_hash=ctx_hash)
        if cached:
            return {**cached, "cached": True, "generated_at": case.ai_generated_at}

    if not ai_enabled():
        payload = _fallback_payload(case, "هوش مصنوعی غیرفعال است یا کلید تنظیم نشده.")
        return {**payload, "cached": False}

    user_prompt = (
        "این پرونده را تحلیل کن و لیست سوال‌هایی بنویس که اپراتور باید در تماس بپرسد.\n"
        f"داده پرونده (JSON):\n{json.dumps(context, ensure_ascii=False)}"
    )

    try:
        raw_text = chat_completion(
            [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.35,
            max_tokens=1100,
        )
        parsed = _extract_json(raw_text)
        payload = _normalize_payload(parsed, case)
    except (MimoError, ValueError, json.JSONDecodeError) as exc:
        logger.warning("case AI failed case=%s: %s", case.pk, exc)
        payload = _fallback_payload(case, str(exc))
        return {**payload, "cached": False}

    case.ai_payload = payload
    case.ai_context_hash = ctx_hash
    case.ai_generated_at = timezone.now()
    case.save(update_fields=["ai_payload", "ai_context_hash", "ai_generated_at", "updated_at"])
    return {**payload, "cached": False, "generated_at": case.ai_generated_at}


CALL_ASSIST_PROMPT = """تو دستیار اپراتور کال‌سنتر سفیران هستی.
خروجی فقط JSON معتبر:
{
  "notes": "۲ تا ۴ جمله فارسی برای لاگ تماس (چی گفته شد / چی قرار شد)",
  "follow_preset": "today_evening|tomorrow|3days|1week|none",
  "follow_reason": "یک جمله کوتاه چرا این موعد",
  "tips": ["نکته کوتاه برای اپراتور"]
}
قواعد: عملی، کوتاه، بر اساس داده پرونده و نتیجه تماس انتخاب‌شده. حدس بی‌پایه نزن.
"""


def _fallback_call_assist(case: CustomerCase, contact_result: str) -> dict[str, Any]:
    name = case.customer.full_name
    presets = {
        "answered": ("tomorrow", f"با {name} صحبت شد؛ جزئیات را در یادداشت تکمیل کنید."),
        "no_answer": ("today_evening", f"عدم پاسخ از {name}؛ عصر دوباره تماس/واتساپ."),
        "busy": ("tomorrow", f"{name} مشغول بود؛ فردا پیگیری."),
        "whatsapp": ("3days", f"پیام واتساپ برای {name} ارسال شد."),
        "not_interested": ("none", f"{name} علاقه‌ای نشان نداد."),
        "converted": ("3days", f"{name} جدی است؛ مدارک/قدم بعد را پیگیری کنید."),
        "callback": ("today_evening", f"{name} خواست بعداً تماس گرفته شود."),
    }
    follow, notes = presets.get(contact_result, ("tomorrow", f"تماس با {name} ثبت شد."))
    return {
        "notes": notes,
        "follow_preset": follow,
        "follow_reason": "پیشنهاد پیش‌فرض بدون AI",
        "tips": ["یادداشت را با جزئیات واقعی تماس کامل کنید."],
        "fallback": True,
    }


def assist_call_log(
    case: CustomerCase,
    *,
    contact_result: str = "",
    draft_notes: str = "",
) -> dict[str, Any]:
    contact_result = (contact_result or "answered").strip()
    if not ai_enabled():
        return _fallback_call_assist(case, contact_result)

    context = build_case_context(case)
    user_prompt = json.dumps(
        {
            "contact_result": contact_result,
            "operator_draft_notes": (draft_notes or "")[:500],
            "case": context,
        },
        ensure_ascii=False,
    )
    try:
        raw = chat_completion(
            [
                {"role": "system", "content": CALL_ASSIST_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.4,
            max_tokens=700,
        )
        data = _extract_json(raw)
        follow = str(data.get("follow_preset") or "tomorrow").strip()
        allowed = {"today_evening", "tomorrow", "3days", "1week", "none"}
        if follow not in allowed:
            follow = "tomorrow"
        tips = data.get("tips") or []
        if not isinstance(tips, list):
            tips = [str(tips)]
        return {
            "notes": str(data.get("notes") or "").strip()
            or _fallback_call_assist(case, contact_result)["notes"],
            "follow_preset": follow,
            "follow_reason": str(data.get("follow_reason") or "").strip(),
            "tips": [str(t).strip() for t in tips if str(t).strip()][:3],
            "fallback": False,
        }
    except (MimoError, ValueError, json.JSONDecodeError) as exc:
        logger.warning("call assist failed case=%s: %s", case.pk, exc)
        out = _fallback_call_assist(case, contact_result)
        out["error"] = str(exc)
        return out
