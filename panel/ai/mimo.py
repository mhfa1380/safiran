"""Xiaomi MiMo chat client (OpenAI-compatible). No hardcoded secrets."""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from typing import Any

from django.conf import settings

logger = logging.getLogger(__name__)


class MimoError(RuntimeError):
    """MiMo API failure."""


def chat_completion(
    messages: list[dict[str, str]],
    *,
    model: str | None = None,
    temperature: float = 0.4,
    max_tokens: int = 1200,
    timeout: int | None = None,
) -> str:
    key = (getattr(settings, "MIMO_API_KEY", "") or "").strip()
    if not key:
        raise MimoError("MIMO_API_KEY تنظیم نشده است.")

    root = (getattr(settings, "MIMO_BASE_URL", "") or "https://api.xiaomimimo.com/v1").rstrip("/")
    model_id = model or getattr(settings, "MIMO_MODEL", "mimo-v2.5-pro")
    timeout_s = timeout or int(getattr(settings, "MIMO_TIMEOUT_SECONDS", 30))

    payload: dict[str, Any] = {
        "model": model_id,
        "messages": messages,
        "max_completion_tokens": max_tokens,
        "temperature": temperature,
        "top_p": 0.9,
        "stream": False,
        "thinking": {"type": "disabled"},
    }

    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        f"{root}/chat/completions",
        data=body,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout_s) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        logger.warning("MiMo HTTP %s: %s", exc.code, detail[:300])
        raise MimoError(f"خطای MiMo ({exc.code})") from exc
    except urllib.error.URLError as exc:
        logger.warning("MiMo connection failed: %s", exc.reason)
        raise MimoError("اتصال به سرویس هوش مصنوعی برقرار نشد.") from exc

    choices = data.get("choices") or []
    if not choices:
        raise MimoError("پاسخ خالی از سرویس AI.")
    content = choices[0].get("message", {}).get("content")
    if not content:
        raise MimoError("متن پاسخ AI خالی بود.")
    return str(content).strip()
