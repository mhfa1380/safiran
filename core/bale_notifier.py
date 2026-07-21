"""Simple Bale notifier with safe error handling and retries."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Optional

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def _bale_retry_attempts() -> int:
    return max(1, int(getattr(settings, "BALE_RETRY_MAX_ATTEMPTS", 3)))


def _bale_retry_base_delay() -> float:
    return max(0.5, float(getattr(settings, "BALE_RETRY_DELAY_SECONDS", 2)))


class BaleNotifier:
    """Notifier for sending text, photo, and file to Bale."""

    def __init__(self, bot_token: str, chat_id: str, timeout: int = 8):
        self.bot_token = (bot_token or "").strip()
        self.chat_id = str(chat_id or "").strip()
        self.timeout = timeout
        self.base_url = f"https://tapi.bale.ai/bot{self.bot_token}"

    @property
    def is_configured(self) -> bool:
        return bool(self.bot_token and self.chat_id)

    def _post(self, endpoint: str, *, data=None, files=None, json_data=None) -> bool:
        if not self.is_configured:
            logger.info("Bale notifier skipped: token/chat_id not configured.")
            return False

        url = f"{self.base_url}/{endpoint}"
        try:
            response = requests.post(
                url,
                data=data,
                files=files,
                json=json_data,
                timeout=self.timeout,
            )
            response.raise_for_status()
            payload = response.json()
            if payload.get("ok"):
                return True
            logger.warning("Bale API returned non-ok response: %s", payload)
            return False
        except Exception as exc:  # noqa: BLE001 - do not break app flow
            logger.exception("Bale send failed (%s): %s", endpoint, exc)
            return False

    def send_text(self, text: str) -> bool:
        payload = {"chat_id": self.chat_id, "text": text}
        return self._post_with_retry("sendMessage", json_data=payload)

    def _post_with_retry(
        self,
        endpoint: str,
        *,
        data=None,
        files=None,
        json_data=None,
    ) -> bool:
        attempts = _bale_retry_attempts()
        base_delay = _bale_retry_base_delay()
        for attempt in range(1, attempts + 1):
            if self._post(endpoint, data=data, files=files, json_data=json_data):
                if attempt > 1:
                    logger.info("Bale %s succeeded on attempt %s/%s", endpoint, attempt, attempts)
                return True
            if attempt < attempts:
                wait = base_delay * attempt
                logger.warning(
                    "Bale %s failed (attempt %s/%s), retry in %.1fs",
                    endpoint,
                    attempt,
                    attempts,
                    wait,
                )
                time.sleep(wait)
        return False

    def send_photo(self, photo_path: str, caption: str = "") -> bool:
        path = Path(photo_path)
        if not path.exists() or not path.is_file():
            logger.warning("Bale photo not found: %s", photo_path)
            return False

        data = {"chat_id": self.chat_id}
        if caption:
            data["caption"] = caption
        try:
            with path.open("rb") as file_obj:
                files = {"photo": file_obj}
                return self._post_with_retry("sendPhoto", data=data, files=files)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Bale photo read failed: %s", exc)
            return False

    def send_file(self, file_path: str, caption: str = "") -> bool:
        path = Path(file_path)
        if not path.exists() or not path.is_file():
            logger.warning("Bale file not found: %s", file_path)
            return False

        data = {"chat_id": self.chat_id}
        if caption:
            data["caption"] = caption
        try:
            with path.open("rb") as file_obj:
                files = {"document": file_obj}
                return self._post_with_retry("sendDocument", data=data, files=files)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Bale file read failed: %s", exc)
            return False


def get_bale_notifier(*, chat_id: str | None = None) -> BaleNotifier:
    """Create notifier from Django settings."""
    token = getattr(settings, "BALE_BOT_TOKEN", "")
    resolved_chat_id = chat_id if chat_id is not None else getattr(settings, "BALE_CHAT_ID", "")
    timeout = int(getattr(settings, "BALE_TIMEOUT_SECONDS", 8))
    return BaleNotifier(bot_token=token, chat_id=resolved_chat_id, timeout=timeout)


def send_bale_text_if_configured(text: str, *, chat_id: str | None = None) -> bool:
    notifier = get_bale_notifier(chat_id=chat_id)
    if not notifier.is_configured:
        return False
    return notifier.send_text(text=text)


def send_bale_blog_text_if_configured(text: str) -> bool:
    blog_chat_id = str(getattr(settings, "BALE_BLOG_CHAT_ID", "") or "").strip()
    if not blog_chat_id:
        return send_bale_text_if_configured(text)
    return send_bale_text_if_configured(text, chat_id=blog_chat_id)


def build_admin_link(path: str) -> str:
    """Build absolute admin link from configured SITE_URL."""
    return build_site_link(path)


def build_site_link(path_or_url: str) -> str:
    """Build absolute public site link from SITE_URL or return full URL as-is."""
    value = (path_or_url or "").strip()
    if not value:
        return ""
    if value.startswith("http://") or value.startswith("https://"):
        return value
    site_url = str(getattr(settings, "SITE_URL", "")).rstrip("/")
    if not value.startswith("/"):
        value = f"/{value}"
    return f"{site_url}{value}" if site_url else value


def truncate_text(value: Optional[str], max_len: int = 120) -> str:
    text = (value or "").strip().replace("\n", " ")
    if len(text) <= max_len:
        return text
    return f"{text[: max_len - 3]}..."
