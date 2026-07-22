"""سرویس‌های پنل: نرمال موبایل، نقش‌ها، دسترسی، همگام‌سازی لید."""
from __future__ import annotations

import re
from datetime import timedelta

from django.contrib.auth.models import Group, User
from django.db import transaction
from django.db.models import Q, QuerySet
from django.utils import timezone

from panel.models import CaseEvent, Customer, CustomerCase

ROLE_MANAGER = "پنل — مدیر پیگیری"
ROLE_STAFF = "پنل — پرسنل پیگیری"

PANEL_GROUPS = (ROLE_MANAGER, ROLE_STAFF)


def normalize_phone(phone: str) -> str:
    raw = (phone or "").strip()
    if raw.lower().startswith("mail:"):
        return raw.lower()
    digits = re.sub(r"\D+", "", raw)
    if digits.startswith("0098"):
        digits = digits[4:]
    elif digits.startswith("98") and len(digits) >= 12:
        digits = digits[2:]
    if digits.startswith("9") and len(digits) == 10:
        digits = "0" + digits
    if len(digits) == 11 and digits.startswith("09"):
        return digits
    return digits or raw


def display_phone(phone: str) -> str:
    n = normalize_phone(phone)
    return n or (phone or "").strip()


def ensure_panel_groups() -> tuple[Group, Group]:
    manager, _ = Group.objects.get_or_create(name=ROLE_MANAGER)
    staff, _ = Group.objects.get_or_create(name=ROLE_STAFF)
    return manager, staff


def user_is_panel_manager(user: User) -> bool:
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.groups.filter(name=ROLE_MANAGER).exists()


def user_is_panel_staff(user: User) -> bool:
    if not user.is_authenticated:
        return False
    if user.is_superuser or user_is_panel_manager(user):
        return True
    return user.groups.filter(name=ROLE_STAFF).exists()


def user_can_access_panel(user: User) -> bool:
    return user_is_panel_staff(user)


def cases_queryset_for(user: User) -> QuerySet[CustomerCase]:
    qs = CustomerCase.objects.select_related(
        "customer", "assigned_to", "evaluation", "consultation"
    )
    if user_is_panel_manager(user):
        return qs
    # پرسنل: پرونده‌های خودش + تخصیص‌نشده‌های باز
    return qs.filter(
        Q(assigned_to=user)
        | Q(assigned_to__isnull=True, status__in=[CustomerCase.STATUS_OPEN, CustomerCase.STATUS_WAITING])
    )


def can_manage_case(user: User, case: CustomerCase) -> bool:
    if user_is_panel_manager(user):
        return True
    if case.assigned_to_id == user.id:
        return True
    if case.assigned_to_id is None and case.status in (
        CustomerCase.STATUS_OPEN,
        CustomerCase.STATUS_WAITING,
    ):
        return True
    return False


def next_case_code() -> str:
    year = timezone.localtime(timezone.now()).year % 100
    prefix = f"SF{year}"
    last = (
        CustomerCase.objects.filter(case_code__startswith=prefix)
        .order_by("-case_code")
        .values_list("case_code", flat=True)
        .first()
    )
    if last and last[len(prefix) :].isdigit():
        num = int(last[len(prefix) :]) + 1
    else:
        num = 1
    return f"{prefix}{num:05d}"


def get_or_create_customer(
    *, full_name: str, phone: str, email: str = ""
) -> tuple[Customer, bool]:
    normalized = normalize_phone(phone)
    if not normalized:
        normalized = f"unknown-{timezone.now().timestamp():.0f}"
    customer, created = Customer.objects.get_or_create(
        phone_normalized=normalized,
        defaults={
            "full_name": full_name or "بدون نام",
            "phone_display": display_phone(phone),
            "email": email or "",
        },
    )
    if not created:
        changed = False
        if full_name and customer.full_name != full_name:
            customer.full_name = full_name
            changed = True
        if email and not customer.email:
            customer.email = email
            changed = True
        disp = display_phone(phone)
        if disp and customer.phone_display != disp:
            customer.phone_display = disp
            changed = True
        if changed:
            customer.save(update_fields=["full_name", "email", "phone_display", "updated_at"])
    return customer, created


@transaction.atomic
def open_case_for_customer(
    customer: Customer,
    *,
    source_type: str,
    stage: str = CustomerCase.STAGE_ATTRACTION,
    assigned_to: User | None = None,
    target_country: str = "",
    target_degree: str = "",
    evaluation=None,
    consultation=None,
    actor: User | None = None,
    note: str = "",
) -> CustomerCase:
    open_case = (
        customer.cases.filter(
            status__in=[CustomerCase.STATUS_OPEN, CustomerCase.STATUS_WAITING]
        )
        .order_by("-updated_at")
        .first()
    )
    if open_case:
        changed_fields = []
        if evaluation and not open_case.evaluation_id:
            open_case.evaluation = evaluation
            changed_fields.append("evaluation")
        if consultation and not open_case.consultation_id:
            open_case.consultation = consultation
            changed_fields.append("consultation")
        if target_country and not open_case.target_country:
            open_case.target_country = target_country
            changed_fields.append("target_country")
        if target_degree and not open_case.target_degree:
            open_case.target_degree = target_degree
            changed_fields.append("target_degree")
        if changed_fields:
            changed_fields.append("updated_at")
            open_case.save(update_fields=changed_fields)
        return open_case

    case = CustomerCase(
        case_code=next_case_code(),
        customer=customer,
        stage=stage,
        source_type=source_type,
        assigned_to=assigned_to,
        target_country=target_country or "",
        target_degree=target_degree or "",
        evaluation=evaluation,
        consultation=consultation,
        next_follow_up_at=timezone.now(),
    )
    case.apply_stage_progress()
    case.save()
    CaseEvent.objects.create(
        case=case,
        event_type=CaseEvent.TYPE_SYSTEM,
        notes=note or "پرونده ایجاد شد",
        created_by=actor,
    )
    if not case.assigned_to_id:
        apply_auto_assign(case, actor=actor)
    return case


def sync_leads_to_cases(*, limit: int | None = None) -> dict[str, int]:
    from core.models import ConsultationRequest, EvaluationRequest

    stats = {"evaluations": 0, "consultations": 0, "skipped": 0}

    eval_qs = EvaluationRequest.objects.order_by("-created_at")
    if limit:
        eval_qs = eval_qs[:limit]
    for ev in eval_qs.iterator():
        if CustomerCase.objects.filter(evaluation=ev).exists():
            stats["skipped"] += 1
            continue
        customer, _ = get_or_create_customer(
            full_name=ev.full_name, phone=ev.phone, email=ev.email or ""
        )
        stage = CustomerCase.STAGE_ATTRACTION
        if ev.status in (EvaluationRequest.STATUS_FOLLOW_UP, EvaluationRequest.STATUS_IN_PROGRESS):
            stage = CustomerCase.STAGE_FOLLOW_UP
        elif ev.status == EvaluationRequest.STATUS_CONTACTED:
            stage = CustomerCase.STAGE_INITIAL
        elif ev.status == EvaluationRequest.STATUS_COMPLETED:
            stage = CustomerCase.STAGE_FILE_OPEN
        case = open_case_for_customer(
            customer,
            source_type=CustomerCase.SOURCE_EVALUATION,
            stage=stage,
            assigned_to=ev.assigned_to,
            target_country=ev.get_target_country_display() if ev.target_country else "",
            target_degree=ev.get_current_degree_display() if ev.current_degree else "",
            evaluation=ev,
            note=f"همگام از ارزیابی #{ev.pk}",
        )
        if ev.status == EvaluationRequest.STATUS_LOST:
            case.stage = CustomerCase.STAGE_LOST
            case.status = CustomerCase.STATUS_CLOSED_LOST
            case.loss_reason = CustomerCase.LOSS_NOT_INTERESTED
            case.closed_at = timezone.now()
            case.apply_stage_progress()
            case.save()
        elif ev.status == EvaluationRequest.STATUS_COMPLETED:
            case.stage = CustomerCase.STAGE_WON
            case.status = CustomerCase.STATUS_CLOSED_WON
            case.closed_at = timezone.now()
            case.apply_stage_progress()
            case.save()
        else:
            if ev.next_follow_up_at:
                case.next_follow_up_at = ev.next_follow_up_at
            if ev.contact_result:
                case.last_contact_result = ev.contact_result
            if ev.priority:
                case.priority = ev.priority
            case.save()
        stats["evaluations"] += 1

    cons_qs = ConsultationRequest.objects.order_by("-created_at")
    if limit:
        cons_qs = cons_qs[:limit]
    for cr in cons_qs.iterator():
        if CustomerCase.objects.filter(consultation=cr).exists():
            stats["skipped"] += 1
            continue
        customer, _ = get_or_create_customer(
            full_name=cr.full_name, phone=cr.phone, email=cr.email or ""
        )
        case = open_case_for_customer(
            customer,
            source_type=CustomerCase.SOURCE_CONSULTATION,
            stage=CustomerCase.STAGE_INITIAL,
            target_country=cr.get_country_display() if cr.country else "",
            consultation=cr,
            note=f"همگام از رزرو مشاوره #{cr.pk}",
        )
        if cr.status == ConsultationRequest.STATUS_DONE:
            case.status = CustomerCase.STATUS_WAITING
        case.save()
        stats["consultations"] += 1

    return stats


def setup_demo_users() -> dict[str, str]:
    manager_group, staff_group = ensure_panel_groups()
    password = "Safiran@1405"

    accounts = [
        {
            "username": "panel_manager",
            "password": password,
            "first_name": "امید",
            "email": "manager@panel.local",
            "group": manager_group,
        },
        {
            "username": "panel_staff",
            "password": password,
            "first_name": "متین",
            "email": "staff@panel.local",
            "group": staff_group,
        },
        {
            "username": "omid",
            "password": "Mwz5c2GA^ya%XX1Lhh",
            "first_name": "امید",
            "email": "omid@panel.local",
            "group": manager_group,
        },
        {
            "username": "matin",
            "password": "$E_6HQN$9JUv1v8pd!",
            "first_name": "متین",
            "email": "matin@panel.local",
            "group": staff_group,
        },
    ]

    created_flags: dict[str, str] = {}
    for acc in accounts:
        user, created = User.objects.get_or_create(
            username=acc["username"],
            defaults={
                "first_name": acc["first_name"],
                "last_name": "",
                "is_staff": True,
                "email": acc["email"],
            },
        )
        user.first_name = acc["first_name"]
        user.last_name = ""
        user.is_active = True
        user.is_staff = True
        user.set_password(acc["password"])
        user.save()
        user.groups.set([acc["group"]])
        created_flags[acc["username"]] = str(created)

    return {
        "manager_username": "omid",
        "staff_username": "matin",
        "password": "(see docs)",
        "fallback_manager": "panel_manager",
        "fallback_staff": "panel_staff",
        "fallback_password": password,
        **{f"created_{k}": v for k, v in created_flags.items()},
    }


def follow_up_preset_delta(preset: str) -> timedelta | None:
    mapping = {
        "today_evening": timedelta(hours=6),
        "tomorrow": timedelta(days=1),
        "3days": timedelta(days=3),
        "1week": timedelta(days=7),
    }
    return mapping.get(preset)


CHECKLIST_ITEMS = [
    {"key": "passport", "label": "پاسپورت معتبر", "group": "file_open", "group_label": "تشکیل پرونده"},
    {"key": "transcript", "label": "ریز نمرات / دانشنامه", "group": "file_open", "group_label": "تشکیل پرونده"},
    {"key": "language", "label": "مدرک زبان", "group": "file_open", "group_label": "تشکیل پرونده"},
    {"key": "contract", "label": "قرارداد / پیش‌قرارداد", "group": "file_open", "group_label": "تشکیل پرونده"},
    {"key": "uni_shortlist", "label": "لیست دانشگاه‌ها", "group": "admission", "group_label": "پذیرش"},
    {"key": "apply_submit", "label": "ارسال اپلای", "group": "admission", "group_label": "پذیرش"},
    {"key": "offer_letter", "label": "دریافت آفر", "group": "admission", "group_label": "پذیرش"},
    {"key": "tuition_pay", "label": "پرداخت شهریه / سپرده", "group": "admission", "group_label": "پذیرش"},
    {"key": "visa_docs", "label": "آماده‌سازی مدارک ویزا", "group": "visa", "group_label": "ویزا"},
    {"key": "embassy_appt", "label": "وقت سفارت / انگشت‌نگاری", "group": "visa", "group_label": "ویزا"},
    {"key": "visa_result", "label": "نتیجه ویزا", "group": "visa", "group_label": "ویزا"},
    {"key": "ticket", "label": "بلیت پرواز", "group": "dispatch", "group_label": "اعزام"},
    {"key": "housing", "label": "خوابگاه / اسکان", "group": "dispatch", "group_label": "اعزام"},
    {"key": "handover", "label": "تحویل و استقرار", "group": "dispatch", "group_label": "اعزام"},
]


STAGE_SCRIPTS = {
    CustomerCase.STAGE_ATTRACTION: [
        "سلام، از سفیران آینده روشن تماس می‌گیرم؛ درخواست‌تان را دیدیم.",
        "کشور و مقطع مدنظرتان چیست؟",
        "آیا الان وقت کوتاهی برای توضیح مسیر دارید؟",
    ],
    CustomerCase.STAGE_INITIAL: [
        "معدل، مدرک زبان و بودجه تقریبی را بپرسید.",
        "مسیر پذیرش + ویزا را خلاصه توضیح دهید.",
        "اگر جدی است، وقت مشاوره تخصصی پیشنهاد دهید.",
    ],
    CustomerCase.STAGE_FOLLOW_UP: [
        "یادآوری تعهد قبلی مشتری را بگویید.",
        "اگر جواب نداد: واتساپ بفرستید و موعد بعدی بگذارید.",
        "مانع اصلی چیست؟ بودجه / زبان / خانواده / تردید.",
    ],
    CustomerCase.STAGE_SPECIALIZED: [
        "قبل از جلسه مدارک اولیه‌ای که لازم است را یادآوری کنید.",
        "خروجی جلسه: کشور نهایی + گام بعدی مشخص.",
    ],
    CustomerCase.STAGE_FILE_OPEN: [
        "چک‌لیست مدارک را مرور کنید.",
        "زمان‌بندی ارسال اپلای را توافق کنید.",
    ],
    CustomerCase.STAGE_ADMISSION: [
        "وضعیت اپلای / آفر را بپرسید.",
        "اگر آفر آمد، مرحله ویزا را باز کنید.",
    ],
    CustomerCase.STAGE_VISA: [
        "تمکن، نوبت سفارت و نواقص مدارک را چک کنید.",
    ],
    CustomerCase.STAGE_DISPATCH: [
        "بلیت، اسکان و زمان پرواز را نهایی کنید.",
    ],
}


def checklist_for_case(case: CustomerCase) -> list[dict]:
    state = case.checklist or {}
    items = []
    for raw in CHECKLIST_ITEMS:
        items.append(
            {
                **raw,
                "done": bool(state.get(raw["key"])),
            }
        )
    return items


FLOW_PIPELINE = [
    CustomerCase.STAGE_ATTRACTION,
    CustomerCase.STAGE_INITIAL,
    CustomerCase.STAGE_FOLLOW_UP,
    CustomerCase.STAGE_SPECIALIZED,
    CustomerCase.STAGE_FILE_OPEN,
    CustomerCase.STAGE_ADMISSION,
    CustomerCase.STAGE_VISA,
    CustomerCase.STAGE_DISPATCH,
]

FLOW_END = [
    CustomerCase.STAGE_WON,
    CustomerCase.STAGE_LOST,
]

# چک‌لیست مرتبط با هر مرحله (برای کارت Flow)
STAGE_CHECKLIST_GROUPS = {
    CustomerCase.STAGE_FILE_OPEN: ("file_open",),
    CustomerCase.STAGE_ADMISSION: ("file_open", "admission"),
    CustomerCase.STAGE_VISA: ("file_open", "admission", "visa"),
    CustomerCase.STAGE_DISPATCH: ("file_open", "admission", "visa", "dispatch"),
    CustomerCase.STAGE_WON: ("file_open", "admission", "visa", "dispatch"),
}


def checklist_progress_for_case(case: CustomerCase) -> dict:
    items = checklist_for_case(case)
    groups = STAGE_CHECKLIST_GROUPS.get(case.stage)
    if groups:
        items = [i for i in items if i["group"] in groups]
    done_items = [i for i in items if i["done"]]
    todo_items = [i for i in items if not i["done"]]
    total = len(items)
    done = len(done_items)
    return {
        "done": done,
        "total": total,
        "pct": int(round((done / total) * 100)) if total else 0,
        "todo_labels": [i["label"] for i in todo_items[:3]],
        "done_labels": [i["label"] for i in done_items[-2:]],
        "has_checklist": total > 0,
    }


def flow_steps_for_case(case: CustomerCase) -> list[dict]:
    """مراحل مسیر برای استپر جزئیات پرونده."""
    stage_map = dict(CustomerCase.STAGE_CHOICES)
    pipeline = list(FLOW_PIPELINE)

    if case.stage == CustomerCase.STAGE_LOST:
        # تا قبل از مختومه، بر اساس progress علامت بزن
        cur_pct = case.progress or 0
        steps = []
        for key in pipeline:
            pct = CustomerCase.STAGE_PROGRESS.get(key, 0)
            if pct < max(cur_pct, 10):
                state = "done"
            else:
                state = "todo"
            steps.append(
                {
                    "key": key,
                    "label": stage_map[key],
                    "state": state,
                    "pct": pct,
                }
            )
        steps.append(
            {
                "key": CustomerCase.STAGE_LOST,
                "label": stage_map[CustomerCase.STAGE_LOST],
                "state": "lost",
                "pct": 0,
            }
        )
        return steps

    steps = []
    found = False
    for key in pipeline:
        if key == case.stage:
            state = "current"
            found = True
        elif not found:
            state = "done"
        else:
            state = "todo"
        steps.append(
            {
                "key": key,
                "label": stage_map[key],
                "state": state,
                "pct": CustomerCase.STAGE_PROGRESS.get(key, 0),
            }
        )

    if case.stage == CustomerCase.STAGE_WON:
        for s in steps:
            s["state"] = "done"
        steps.append(
            {
                "key": CustomerCase.STAGE_WON,
                "label": stage_map[CustomerCase.STAGE_WON],
                "state": "won",
                "pct": 100,
            }
        )
    elif case.stage not in pipeline:
        steps.append(
            {
                "key": case.stage,
                "label": stage_map.get(case.stage, case.stage),
                "state": "current",
                "pct": case.progress,
            }
        )
    return steps


def build_flow_board(user: User, *, scope: str = "open", mine: bool = False) -> dict:
    """برد کانبان مسیر مشتری: ستون‌ها + کارت‌ها + خلاصه چک‌لیست."""
    qs = cases_queryset_for(user).select_related("customer", "assigned_to")
    if mine:
        qs = qs.filter(assigned_to=user)

    include_closed = scope == "all"
    if scope == "open" or scope == "mine":
        qs = qs.exclude(
            status__in=[CustomerCase.STATUS_CLOSED_WON, CustomerCase.STATUS_CLOSED_LOST]
        )
    elif scope == "overdue":
        qs = qs.exclude(
            status__in=[CustomerCase.STATUS_CLOSED_WON, CustomerCase.STATUS_CLOSED_LOST]
        ).filter(next_follow_up_at__lte=timezone.now())
    elif scope == "waiting":
        qs = qs.filter(status=CustomerCase.STATUS_WAITING)

    stage_keys = list(FLOW_PIPELINE)
    if include_closed or scope == "all":
        stage_keys = stage_keys + list(FLOW_END)

    # اگر scope=all، همه پرونده‌ها (باز + بسته)
    if scope == "all":
        qs = cases_queryset_for(user).select_related("customer", "assigned_to")
        if mine:
            qs = qs.filter(assigned_to=user)

    by_stage: dict[str, list] = {k: [] for k in stage_keys}
    stage_map = dict(CustomerCase.STAGE_CHOICES)

    for case in qs.order_by("next_follow_up_at", "-updated_at")[:400]:
        key = case.stage
        if key not in by_stage:
            # مراحل بسته وقتی فقط open هستیم
            if key in FLOW_END and not include_closed and scope != "all":
                continue
            if key not in by_stage:
                by_stage[key] = []
                if key not in stage_keys:
                    stage_keys.append(key)
        check = checklist_progress_for_case(case)
        by_stage[key].append(
            {
                "case": case,
                "check": check,
                "badge": case.follow_up_badge,
                "assignee": (
                    case.assigned_to.get_full_name()
                    or case.assigned_to.get_username()
                    if case.assigned_to_id
                    else ""
                ),
            }
        )

    columns = []
    total_open = 0
    total_overdue = 0
    total_today = 0
    total_done_check = 0
    total_todo_check = 0

    for key in stage_keys:
        cards = by_stage.get(key, [])
        overdue_n = sum(1 for c in cards if c["badge"] == "overdue")
        today_n = sum(1 for c in cards if c["badge"] == "today")
        for c in cards:
            if c["check"]["has_checklist"]:
                total_done_check += c["check"]["done"]
                total_todo_check += c["check"]["total"] - c["check"]["done"]
        if key not in FLOW_END:
            total_open += len(cards)
            total_overdue += overdue_n
            total_today += today_n
        columns.append(
            {
                "key": key,
                "label": stage_map.get(key, key),
                "pct": CustomerCase.STAGE_PROGRESS.get(key, 0),
                "count": len(cards),
                "overdue": overdue_n,
                "today": today_n,
                "cards": cards[:40],
                "more": max(0, len(cards) - 40),
                "is_end": key in FLOW_END,
                "is_won": key == CustomerCase.STAGE_WON,
                "is_lost": key == CustomerCase.STAGE_LOST,
            }
        )

    return {
        "columns": columns,
        "summary": {
            "total": sum(c["count"] for c in columns),
            "open": total_open,
            "overdue": total_overdue,
            "today": total_today,
            "check_done": total_done_check,
            "check_todo": total_todo_check,
        },
        "pipeline_labels": [
            {"key": k, "label": stage_map[k], "pct": CustomerCase.STAGE_PROGRESS[k]}
            for k in FLOW_PIPELINE
        ],
    }


def set_checklist_item(case: CustomerCase, key: str, done: bool) -> None:
    state = dict(case.checklist or {})
    state[key] = bool(done)
    case.checklist = state
    case.save(update_fields=["checklist", "updated_at"])


def _slot_start_datetime(slot):
    """شروع جلسه از تاریخ + برچسب ساعت اسلات (Asia/Tehran)."""
    from datetime import datetime, time

    start_t = time(10, 0)
    label = (slot.time_label or "").translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789"))
    try:
        start_str = label.replace("–", "-").split("-")[0].strip()
        h, m = map(int, start_str.split(":")[:2])
        start_t = time(h, m)
    except (ValueError, TypeError, IndexError):
        pass
    return timezone.make_aware(datetime.combine(slot.date, start_t))


def ensure_appointment_for_consultation(
    case: CustomerCase, consultation=None
):
    """اگر رزرو مشاوره اسلات دارد، جلسه بساز یا ساعت/روز را با اسلات همگام کن."""
    from datetime import timedelta

    from panel.models import CaseAppointment

    cr = consultation or case.consultation
    if not cr or not cr.slot_id:
        return None
    slot = cr.slot
    if not slot:
        return None
    starts = _slot_start_datetime(slot)
    ends = starts + timedelta(minutes=30)
    mode = (
        CaseAppointment.MODE_IN_PERSON
        if cr.consultation_type == cr.IN_PERSON
        else CaseAppointment.MODE_ONLINE
    )
    title = f"رزرو سایت — {cr.get_consultation_type_display()}"
    existing = CaseAppointment.objects.filter(consultation=cr).first()
    if existing:
        fields = []
        if existing.starts_at != starts:
            existing.starts_at = starts
            existing.ends_at = ends
            fields.extend(["starts_at", "ends_at"])
        if existing.case_id != case.pk:
            existing.case = case
            fields.append("case")
        if not existing.title:
            existing.title = title
            fields.append("title")
        if existing.mode != mode:
            existing.mode = mode
            fields.append("mode")
        if fields:
            existing.save(update_fields=fields)
        return existing
    return CaseAppointment.objects.create(
        case=case,
        title=title,
        kind=CaseAppointment.KIND_INITIAL,
        mode=mode,
        starts_at=starts,
        ends_at=ends,
        assignee=case.assigned_to,
        consultation=cr,
        notes="ساخته‌شده خودکار از اسلات سایت",
    )


def sync_consultation_appointments() -> int:
    """همه رزروهای دارای اسلات را به جلسهٔ تقویم وصل می‌کند."""
    from core.models import ConsultationRequest
    from panel.models import CaseAppointment

    created = 0
    for cr in ConsultationRequest.objects.filter(slot__isnull=False).select_related("slot"):
        case = CustomerCase.objects.filter(consultation=cr).select_related("assigned_to").first()
        if not case:
            case = (
                CustomerCase.objects.filter(customer__phone_normalized=normalize_phone(cr.phone))
                .order_by("-updated_at")
                .select_related("assigned_to")
                .first()
            )
        if not case:
            continue
        before = CaseAppointment.objects.filter(consultation=cr).exists()
        appt = ensure_appointment_for_consultation(case, consultation=cr)
        if appt and not before:
            created += 1
    return created


def sync_contact_messages(*, limit: int | None = None) -> int:
    from core.models import ContactMessage

    count = 0
    qs = ContactMessage.objects.order_by("-created_at")
    if limit:
        qs = qs[:limit]
    for msg in qs.iterator():
        if CustomerCase.objects.filter(contact_message=msg).exists():
            continue
        phone_key = f"mail:{(msg.email or '').strip().lower()}"
        customer, _ = get_or_create_customer(
            full_name=msg.full_name,
            phone=phone_key,
            email=msg.email or "",
        )
        case = open_case_for_customer(
            customer,
            source_type=CustomerCase.SOURCE_CONTACT,
            stage=CustomerCase.STAGE_ATTRACTION,
            actor=None,
            note=f"همگام از تماس با ما #{msg.pk}: {msg.subject}",
        )
        case.contact_message = msg
        case.internal_notes = (case.internal_notes + "\n" if case.internal_notes else "") + (
            f"{msg.subject}\n{msg.message}"
        )[:2000]
        case.save(update_fields=["contact_message", "internal_notes", "updated_at"])
        count += 1
    return count


def apply_call_event(
    case: CustomerCase,
    *,
    user: User,
    contact_result: str,
    notes: str = "",
    follow_preset: str = "tomorrow",
    custom_follow_up=None,
) -> CaseEvent:
    if follow_preset == "none":
        next_at = None
    elif follow_preset == "custom":
        next_at = custom_follow_up
    else:
        delta = follow_up_preset_delta(follow_preset) or timedelta(days=1)
        next_at = timezone.now() + delta

    event = CaseEvent.objects.create(
        case=case,
        event_type=CaseEvent.TYPE_CALL,
        contact_result=contact_result,
        notes=notes,
        next_follow_up_at=next_at,
        created_by=user,
    )
    case.last_contact_result = contact_result
    case.next_follow_up_at = next_at
    if contact_result == CaseEvent.CONTACT_NOT_INTERESTED:
        case.stage = CustomerCase.STAGE_LOST
        case.status = CustomerCase.STATUS_CLOSED_LOST
        case.loss_reason = CustomerCase.LOSS_NOT_INTERESTED
        case.loss_note = notes[:300]
        case.closed_at = timezone.now()
        case.apply_stage_progress()
    elif contact_result == CaseEvent.CONTACT_CONVERTED:
        case.stage = CustomerCase.STAGE_FILE_OPEN
        case.status = CustomerCase.STATUS_OPEN
        case.apply_stage_progress()
    elif case.stage == CustomerCase.STAGE_ATTRACTION:
        case.stage = CustomerCase.STAGE_INITIAL
        case.apply_stage_progress()
    elif contact_result in (CaseEvent.CONTACT_NO_ANSWER, CaseEvent.CONTACT_BUSY, CaseEvent.CONTACT_CALLBACK):
        case.stage = CustomerCase.STAGE_FOLLOW_UP
        case.status = CustomerCase.STATUS_WAITING
        case.apply_stage_progress()
    case.save()

    # همگام ارزیابی مرتبط
    if case.evaluation_id:
        from core.models import EvaluationContactLog, EvaluationRequest

        ev = case.evaluation
        result_map = {
            CaseEvent.CONTACT_ANSWERED: EvaluationRequest.CONTACT_ANSWERED,
            CaseEvent.CONTACT_NO_ANSWER: EvaluationRequest.CONTACT_NO_ANSWER,
            CaseEvent.CONTACT_BUSY: EvaluationRequest.CONTACT_BUSY,
            CaseEvent.CONTACT_CALLBACK: EvaluationRequest.CONTACT_CALLBACK,
            CaseEvent.CONTACT_WHATSAPP: EvaluationRequest.CONTACT_WHATSAPP,
            CaseEvent.CONTACT_NOT_INTERESTED: EvaluationRequest.CONTACT_NOT_INTERESTED,
            CaseEvent.CONTACT_CONVERTED: EvaluationRequest.CONTACT_CONVERTED,
        }
        mapped = result_map.get(contact_result)
        if mapped:
            EvaluationContactLog.objects.create(
                evaluation=ev,
                contact_result=mapped,
                notes=notes,
                follow_up_required=bool(next_at),
                next_follow_up_at=next_at,
                created_by=user,
            )
            ev.contact_result = mapped
            ev.contacted_at = timezone.now()
            ev.next_follow_up_at = next_at
            if contact_result == CaseEvent.CONTACT_NOT_INTERESTED:
                ev.status = EvaluationRequest.STATUS_LOST
                ev.follow_up_required = False
            elif contact_result == CaseEvent.CONTACT_CONVERTED:
                ev.status = EvaluationRequest.STATUS_COMPLETED
            else:
                ev.status = EvaluationRequest.STATUS_FOLLOW_UP
                ev.follow_up_required = True
            if not ev.assigned_to_id:
                ev.assigned_to = user
            ev.save()
    return event


# ── تخصیص و توزیع خودکار ─────────────────────────────

def ensure_staff_profiles() -> None:
    """برای همهٔ پرسنل/مدیر پنل پروفایل بساز."""
    from panel.models import StaffAssignmentProfile

    users = User.objects.filter(
        is_active=True,
        groups__name__in=[ROLE_STAFF, ROLE_MANAGER],
    ).distinct()
    for u in users:
        StaffAssignmentProfile.objects.get_or_create(
            user=u,
            defaults={"is_active": True, "weight": 1},
        )


def active_assignee_users() -> list[User]:
    from panel.models import StaffAssignmentProfile

    ensure_staff_profiles()
    profiles = (
        StaffAssignmentProfile.objects.filter(is_active=True, user__is_active=True)
        .select_related("user")
        .order_by("sort_order", "user__username")
    )
    users: list[User] = []
    for p in profiles:
        for _ in range(max(1, int(p.weight or 1))):
            users.append(p.user)
    # unique preserve order for least_load; weighted list for RR
    return users


def unique_active_assignees() -> list[User]:
    seen = set()
    out = []
    for u in active_assignee_users():
        if u.pk in seen:
            continue
        seen.add(u.pk)
        out.append(u)
    return out


def _open_load(user: User) -> int:
    return CustomerCase.objects.filter(
        assigned_to=user,
        status__in=[CustomerCase.STATUS_OPEN, CustomerCase.STATUS_WAITING],
    ).count()


def pick_assignee(*, mode: str, fixed_user: User | None = None, rr_settings=None) -> User | None:
    from panel.models import PanelSettings

    if mode == PanelSettings.MODE_FIXED:
        if fixed_user and fixed_user.is_active:
            return fixed_user
        pool = unique_active_assignees()
        return pool[0] if pool else None

    if mode == PanelSettings.MODE_LEAST_LOAD:
        pool = unique_active_assignees()
        if not pool:
            return None
        return min(pool, key=lambda u: (_open_load(u), u.username))

    # round robin
    weighted = active_assignee_users()
    if not weighted:
        return None
    settings_obj = rr_settings
    if settings_obj is None:
        settings_obj = PanelSettings.load()
    idx = settings_obj.rr_cursor % len(weighted)
    user = weighted[idx]
    PanelSettings.objects.filter(pk=settings_obj.pk).update(rr_cursor=settings_obj.rr_cursor + 1)
    settings_obj.rr_cursor += 1
    return user


def apply_auto_assign(case: CustomerCase, *, actor: User | None = None) -> bool:
    """اگر تنظیم روشن باشد و پرونده بدون مسئول است، مسئول بگذار."""
    from panel.models import PanelSettings

    if case.assigned_to_id:
        return False
    if case.status in (CustomerCase.STATUS_CLOSED_LOST, CustomerCase.STATUS_CLOSED_WON):
        return False
    settings_obj = PanelSettings.load()
    if not settings_obj.auto_assign_enabled:
        return False
    user = pick_assignee(
        mode=settings_obj.auto_assign_mode,
        fixed_user=settings_obj.fixed_assignee,
        rr_settings=settings_obj,
    )
    if not user:
        return False
    case.assigned_to = user
    case.save(update_fields=["assigned_to", "updated_at"])
    CaseEvent.objects.create(
        case=case,
        event_type=CaseEvent.TYPE_ASSIGN,
        notes=f"تخصیص خودکار به «{user.get_username()}»",
        created_by=actor,
        meta={"auto": True, "mode": settings_obj.auto_assign_mode},
    )
    return True


def followup_distribution_queryset(scope: str):
    from datetime import datetime, time

    from panel.models import PanelSettings

    qs = CustomerCase.objects.filter(
        assigned_to__isnull=True,
        status__in=[CustomerCase.STATUS_OPEN, CustomerCase.STATUS_WAITING],
    ).order_by("next_follow_up_at", "id")
    if scope == PanelSettings.SCOPE_FOLLOWUP:
        now = timezone.now()
        today = timezone.localdate()
        start = timezone.make_aware(datetime.combine(today, time.min))
        end = timezone.make_aware(datetime.combine(today, time.max))
        qs = qs.filter(
            Q(next_follow_up_at__lte=now)
            | Q(next_follow_up_at__gte=start, next_follow_up_at__lte=end)
            | Q(next_follow_up_at__isnull=True)
        )
    return qs


def distribute_cases(*, mode: str, scope: str, actor: User | None = None) -> dict[str, int]:
    """توزیع پرونده‌های هدف بین پرسنل فعال."""
    from panel.models import PanelSettings

    cases = list(followup_distribution_queryset(scope)[:500])
    assigned = 0
    skipped = 0
    for case in cases:
        user = pick_assignee(mode=mode, rr_settings=PanelSettings.load())
        if not user:
            skipped += len(cases) - assigned
            break
        case.assigned_to = user
        case.save(update_fields=["assigned_to", "updated_at"])
        CaseEvent.objects.create(
            case=case,
            event_type=CaseEvent.TYPE_ASSIGN,
            notes=f"توزیع خودکار به «{user.get_username()}»",
            created_by=actor,
            meta={"auto_daily": True, "mode": mode, "scope": scope},
        )
        assigned += 1
    return {"assigned": assigned, "skipped": skipped, "total": len(cases)}


def maybe_run_daily_distribution(*, actor: User | None = None, force: bool = False) -> dict | None:
    """اگر توزیع روزانه روشن باشد و امروز اجرا نشده، اجرا کن."""
    from panel.models import PanelSettings

    settings_obj = PanelSettings.load()
    if not settings_obj.daily_followup_enabled and not force:
        return None
    today = timezone.localdate()
    if not force and settings_obj.last_daily_run_on == today:
        return None
    result = distribute_cases(
        mode=settings_obj.daily_followup_mode,
        scope=settings_obj.daily_followup_scope,
        actor=actor,
    )
    settings_obj.last_daily_run_on = today
    settings_obj.save(update_fields=["last_daily_run_on", "updated_at"])
    result["ran_on"] = str(today)
    return result


def build_manager_analytics(*, period: str = "30") -> dict:
    """آمار و گزارش مدیریتی پنل."""
    from datetime import datetime, time

    from django.db.models import Count
    from django.db.models.functions import TruncDate

    from panel.models import CaseAppointment

    now = timezone.now()
    today = timezone.localdate()
    if period == "7":
        since = now - timedelta(days=7)
        period_label = "۷ روز اخیر"
    elif period == "month":
        since = timezone.make_aware(datetime.combine(today.replace(day=1), time.min))
        period_label = "از اول ماه میلادی"
    elif period == "all":
        since = None
        period_label = "کل دوره"
    else:
        since = now - timedelta(days=30)
        period_label = "۳۰ روز اخیر"

    qs = CustomerCase.objects.all()
    open_qs = qs.exclude(
        status__in=[CustomerCase.STATUS_CLOSED_LOST, CustomerCase.STATUS_CLOSED_WON]
    )
    period_qs = qs.filter(created_at__gte=since) if since else qs
    closed_period = qs.filter(closed_at__gte=since) if since else qs.filter(
        status__in=[CustomerCase.STATUS_CLOSED_LOST, CustomerCase.STATUS_CLOSED_WON]
    )

    closed_won = qs.filter(status=CustomerCase.STATUS_CLOSED_WON).count()
    closed_lost = qs.filter(status=CustomerCase.STATUS_CLOSED_LOST).count()
    total = qs.count() or 1
    won_period = closed_period.filter(status=CustomerCase.STATUS_CLOSED_WON).count()
    lost_period = closed_period.filter(status=CustomerCase.STATUS_CLOSED_LOST).count()

    day_start = timezone.make_aware(datetime.combine(today, time.min))
    day_end = timezone.make_aware(datetime.combine(today, time.max))
    overdue = open_qs.filter(next_follow_up_at__lte=now).count()
    due_today = open_qs.filter(next_follow_up_at__gt=now, next_follow_up_at__lte=day_end).count()
    unassigned = open_qs.filter(assigned_to__isnull=True).count()
    new_period = period_qs.count()

    events = CaseEvent.objects.all()
    if since:
        events = events.filter(created_at__gte=since)
    calls = events.filter(event_type=CaseEvent.TYPE_CALL).count()
    assigns = events.filter(event_type=CaseEvent.TYPE_ASSIGN).count()

    stage_map = dict(CustomerCase.STAGE_CHOICES)
    open_total = open_qs.count() or 1
    stages = []
    for r in open_qs.values("stage").annotate(c=Count("id")).order_by():
        stages.append(
            {
                "key": r["stage"],
                "label": stage_map.get(r["stage"], r["stage"]),
                "count": r["c"],
                "pct": round(100 * r["c"] / open_total, 1),
            }
        )
    stages.sort(key=lambda x: -x["count"])

    source_map = dict(CustomerCase.SOURCE_CHOICES)
    sources = [
        {
            "label": source_map.get(r["source_type"], r["source_type"]),
            "count": r["c"],
        }
        for r in open_qs.values("source_type").annotate(c=Count("id")).order_by("-c")
    ]

    loss_map = dict(CustomerCase.LOSS_REASON_CHOICES)
    losses = [
        {"label": loss_map.get(r["loss_reason"], r["loss_reason"] or "—"), "count": r["c"]}
        for r in qs.filter(status=CustomerCase.STATUS_CLOSED_LOST)
        .values("loss_reason")
        .annotate(c=Count("id"))
        .order_by("-c")
    ]

    # عملکرد پرسنل
    staff_users = User.objects.filter(
        is_active=True, groups__name__in=[ROLE_STAFF, ROLE_MANAGER]
    ).distinct().order_by("username")
    staff_rows = []
    for u in staff_users:
        u_open = open_qs.filter(assigned_to=u)
        u_overdue = u_open.filter(next_follow_up_at__lte=now).count()
        u_calls = CaseEvent.objects.filter(
            event_type=CaseEvent.TYPE_CALL, created_by=u
        )
        if since:
            u_calls = u_calls.filter(created_at__gte=since)
        staff_rows.append(
            {
                "uid": u.pk,
                "name": u.get_full_name() or u.username,
                "username": u.username,
                "open": u_open.count(),
                "overdue": u_overdue,
                "today": u_open.filter(
                    next_follow_up_at__gt=now, next_follow_up_at__lte=day_end
                ).count(),
                "calls": u_calls.count(),
                "won": qs.filter(assigned_to=u, status=CustomerCase.STATUS_CLOSED_WON).count(),
                "lost": qs.filter(assigned_to=u, status=CustomerCase.STATUS_CLOSED_LOST).count(),
            }
        )
    staff_rows.sort(key=lambda r: (-r["overdue"], -r["open"]))

    # بدون مسئول به‌عنوان ردیف
    staff_rows.insert(
        0,
        {
            "uid": None,
            "name": "بدون مسئول",
            "username": "",
            "open": unassigned,
            "overdue": open_qs.filter(assigned_to__isnull=True, next_follow_up_at__lte=now).count(),
            "today": open_qs.filter(
                assigned_to__isnull=True,
                next_follow_up_at__gt=now,
                next_follow_up_at__lte=day_end,
            ).count(),
            "calls": 0,
            "won": 0,
            "lost": 0,
        },
    )

    # روند ۷ روزه ایجاد پرونده
    week_ago = now - timedelta(days=6)
    created_by_day = (
        CustomerCase.objects.filter(created_at__gte=week_ago)
        .annotate(d=TruncDate("created_at"))
        .values("d")
        .annotate(c=Count("id"))
        .order_by("d")
    )
    trend_map = {r["d"]: r["c"] for r in created_by_day}
    trend = []
    max_trend = max(trend_map.values()) if trend_map else 1
    max_trend = max(max_trend, 1)
    for i in range(7):
        d = (week_ago + timedelta(days=i)).date()
        c = trend_map.get(d, 0)
        trend.append(
            {
                "date": d,
                "count": c,
                "pct": round(100 * c / max_trend) if c else 4,
            }
        )

    appts_week = CaseAppointment.objects.filter(
        starts_at__gte=day_start,
        starts_at__lte=day_start + timedelta(days=7),
    ).count()

    return {
        "period": period,
        "period_label": period_label,
        "total": qs.count(),
        "open_total": open_qs.count(),
        "closed_won": closed_won,
        "closed_lost": closed_lost,
        "win_rate": round(100 * closed_won / total, 1),
        "loss_rate": round(100 * closed_lost / total, 1),
        "overdue": overdue,
        "due_today": due_today,
        "unassigned": unassigned,
        "new_period": new_period,
        "won_period": won_period,
        "lost_period": lost_period,
        "calls": calls,
        "assigns": assigns,
        "appts_week": appts_week,
        "stages": stages,
        "sources": sources,
        "losses": losses,
        "staff_rows": staff_rows,
        "trend": trend,
    }


def notification_payload_for(user: User, *, since=None) -> dict:
    """شمارنده‌ها و رویدادهای تازه برای بج منو و نوتیف مرورگر."""
    from datetime import datetime, time

    from panel.models import CaseAppointment, CaseEvent

    qs = cases_queryset_for(user)
    now = timezone.now()
    today = timezone.localdate()
    day_start = timezone.make_aware(datetime.combine(today, time.min))
    day_end = timezone.make_aware(datetime.combine(today, time.max))
    open_qs = qs.exclude(
        status__in=[CustomerCase.STATUS_CLOSED_LOST, CustomerCase.STATUS_CLOSED_WON]
    )

    overdue = open_qs.filter(next_follow_up_at__lte=now).count()
    due_today = open_qs.filter(
        next_follow_up_at__gt=now, next_follow_up_at__lte=day_end
    ).count()
    followup = overdue + due_today
    new_attraction = open_qs.filter(stage=CustomerCase.STAGE_ATTRACTION).count()
    unassigned = open_qs.filter(assigned_to__isnull=True).count()
    mine_open = open_qs.filter(assigned_to=user).count()

    case_ids = qs.values_list("id", flat=True)
    calendar_today = CaseAppointment.objects.filter(
        case_id__in=case_ids,
        starts_at__gte=day_start,
        starts_at__lte=day_end,
    ).count()
    if not user_is_panel_manager(user):
        calendar_today = CaseAppointment.objects.filter(
            case_id__in=case_ids,
            starts_at__gte=day_start,
            starts_at__lte=day_end,
        ).filter(Q(assignee=user) | Q(case__assigned_to=user)).count()

    counts = {
        "followup": followup,
        "overdue": overdue,
        "today": due_today,
        "cases_new": new_attraction,
        "unassigned": unassigned if user_is_panel_manager(user) else 0,
        "mine": mine_open,
        "calendar": calendar_today,
        "dashboard": followup,
    }

    events: list[dict] = []
    if since is not None:
        # پرونده‌های جدید در محدودهٔ دسترسی
        for c in (
            open_qs.filter(created_at__gt=since)
            .select_related("customer")
            .order_by("-created_at")[:12]
        ):
            events.append(
                {
                    "id": f"case-{c.pk}-{int(c.created_at.timestamp())}",
                    "kind": "new_case",
                    "title": "پرونده جدید",
                    "body": f"{c.customer.full_name} — {c.case_code}",
                    "url": f"/panel/cases/{c.pk}/",
                    "at": c.created_at.isoformat(),
                }
            )
        # تخصیص به من
        for e in (
            CaseEvent.objects.filter(
                case_id__in=case_ids,
                event_type=CaseEvent.TYPE_ASSIGN,
                created_at__gt=since,
                case__assigned_to=user,
            )
            .select_related("case", "case__customer")
            .order_by("-created_at")[:12]
        ):
            events.append(
                {
                    "id": f"assign-{e.pk}",
                    "kind": "assign",
                    "title": "تخصیص به شما",
                    "body": f"{e.case.customer.full_name} — {e.case.case_code}",
                    "url": f"/panel/cases/{e.case_id}/",
                    "at": e.created_at.isoformat(),
                }
            )
        # جلسات نزدیک (شروع در ۲ ساعت آینده، ساخته‌شده بعد از since یا شروع‌شان در بازه)
        soon = now + timedelta(hours=2)
        appt_qs = CaseAppointment.objects.filter(
            case_id__in=case_ids,
            starts_at__gte=now,
            starts_at__lte=soon,
        ).select_related("case", "case__customer")
        if not user_is_panel_manager(user):
            appt_qs = appt_qs.filter(Q(assignee=user) | Q(case__assigned_to=user))
        for a in appt_qs.order_by("starts_at")[:8]:
            local = timezone.localtime(a.starts_at)
            events.append(
                {
                    "id": f"appt-{a.pk}-{int(a.starts_at.timestamp())}",
                    "kind": "appointment",
                    "title": "جلسه نزدیک",
                    "body": f"{local.strftime('%H:%M')} — {a.case.customer.full_name}",
                    "url": f"/panel/cases/{a.case_id}/",
                    "at": a.starts_at.isoformat(),
                }
            )

    # یکتا و مرتب
    seen = set()
    uniq = []
    for ev in sorted(events, key=lambda x: x["at"], reverse=True):
        if ev["id"] in seen:
            continue
        seen.add(ev["id"])
        uniq.append(ev)

    return {
        "counts": counts,
        "events": uniq[:20],
        "server_time": now.isoformat(),
        "is_manager": user_is_panel_manager(user),
    }
