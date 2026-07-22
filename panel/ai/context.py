"""Build compact case context for MiMo prompts."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from django.utils import timezone

from panel.models import CustomerCase
from panel.services import STAGE_SCRIPTS, checklist_progress_for_case


def _safe_display(obj, field: str, get_display: bool = False) -> str:
    if obj is None:
        return ""
    if get_display:
        fn = getattr(obj, f"get_{field}_display", None)
        if callable(fn):
            return str(fn() or "")
    return str(getattr(obj, field, "") or "")


def build_case_context(case: CustomerCase) -> dict[str, Any]:
    cust = case.customer
    ev = case.evaluation
    progress = checklist_progress_for_case(case)

    evaluation: dict[str, Any] = {}
    if ev is not None:
        evaluation = {
            "current_degree": _safe_display(ev, "current_degree", True),
            "field_of_study": _safe_display(ev, "field_of_study"),
            "average_grade": _safe_display(ev, "average_grade"),
            "graduation_year": _safe_display(ev, "graduation_year"),
            "target_country": _safe_display(ev, "target_country", True),
            "desired_countries": _safe_display(ev, "desired_countries"),
            "desired_major": _safe_display(ev, "desired_major"),
            "language_test": _safe_display(ev, "language_test_type", True),
            "language_score": _safe_display(ev, "language_score"),
            "has_ielts": bool(getattr(ev, "has_ielts", False)),
            "apply_timeline": _safe_display(ev, "apply_timeline", True),
            "marital_status": _safe_display(ev, "marital_status", True),
            "has_financial_capacity": bool(getattr(ev, "has_financial_capacity", False)),
            "birth_year": getattr(ev, "birth_year", None),
            "articles": {
                "journal": bool(getattr(ev, "has_journal_article", False)),
                "conference": bool(getattr(ev, "has_conference_article", False)),
                "book": bool(getattr(ev, "has_book", False)),
            },
            "result_hint": "",
        }
        try:
            evaluation["result_hint"] = str(ev.get_recommendation_top_line() or "")
        except Exception:
            evaluation["result_hint"] = ""

    events = []
    for evn in case.events.select_related("created_by").order_by("-created_at")[:6]:
        events.append(
            {
                "type": evn.get_event_type_display(),
                "contact_result": evn.get_contact_result_display() if evn.contact_result else "",
                "notes": (evn.notes or "")[:220],
                "at": timezone.localtime(evn.created_at).strftime("%Y-%m-%d %H:%M"),
            }
        )

    due = ""
    if case.next_follow_up_at:
        due = timezone.localtime(case.next_follow_up_at).strftime("%Y-%m-%d %H:%M")

    return {
        "case_code": case.case_code,
        "customer_name": cust.full_name,
        "phone": cust.phone_display or cust.phone_normalized,
        "stage": case.get_stage_display(),
        "stage_key": case.stage,
        "status": case.get_status_display(),
        "priority": case.get_priority_display(),
        "source": case.get_source_type_display(),
        "progress_pct": case.progress,
        "assignee": (
            case.assigned_to.get_full_name() or case.assigned_to.username
            if case.assigned_to_id
            else "بدون مسئول"
        ),
        "next_follow_up": due,
        "last_contact_result": case.last_contact_result or "",
        "target_country": case.target_country or "",
        "target_degree": case.target_degree or "",
        "internal_notes": (case.internal_notes or "")[:400],
        "checklist": {
            "done": progress.get("done", 0),
            "total": progress.get("total", 0),
            "todo": progress.get("todo_labels", [])[:8],
        },
        "evaluation": evaluation,
        "recent_events": events,
        "fallback_script": STAGE_SCRIPTS.get(case.stage, []),
    }


def context_hash(context: dict[str, Any]) -> str:
    raw = json.dumps(context, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:40]
