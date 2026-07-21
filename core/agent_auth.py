"""Bearer token verification for MHFA Live agent endpoints."""

from __future__ import annotations

import hmac

from django.conf import settings
from django.http import HttpRequest


def get_bearer_token(request: HttpRequest) -> str:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:].strip()
    return ""


def verify_agent_token(request: HttpRequest) -> bool:
    expected = str(getattr(settings, "MHFA_AGENT_TOKEN", "")).strip()
    if not expected:
        return False
    token = get_bearer_token(request)
    if not token:
        return False
    return hmac.compare_digest(token, expected)
