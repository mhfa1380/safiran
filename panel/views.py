from __future__ import annotations

from datetime import date, datetime, time, timedelta

from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.views import LoginView
from django.db.models import Count, Q
from django.http import Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.decorators.http import require_POST

from panel.decorators import panel_login_required, panel_manager_required
from panel.forms import (
    AppointmentForm,
    AssignForm,
    CaseFilterForm,
    CloseCaseForm,
    DocumentUploadForm,
    ManualCaseForm,
    PanelLoginForm,
    QuickCallForm,
    StageChangeForm,
)
from panel.models import CaseAppointment, CaseDocument, CaseEvent, CustomerCase
from panel.services import (
    STAGE_SCRIPTS,
    apply_call_event,
    build_flow_board,
    can_manage_case,
    cases_queryset_for,
    checklist_for_case,
    flow_steps_for_case,
    FLOW_PIPELINE,
    get_or_create_customer,
    normalize_phone,
    open_case_for_customer,
    checklist_progress_for_case,
    set_checklist_item,
    user_is_panel_manager,
)
from panel.calendar_utils import (
    build_month_cells,
    combine_local,
    jalali_month_bounds,
    jalali_today,
    month_title,
    parse_jalali_date,
    parse_time_hm,
    shift_jalali_month,
)


class PanelLoginView(LoginView):
    template_name = "panel/login.html"
    authentication_form = PanelLoginForm
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse_lazy("panel:dashboard")

    def form_valid(self, form):
        user = form.get_user()
        from panel.services import user_can_access_panel

        if not user_can_access_panel(user):
            form.add_error(None, "این کاربر به پنل پیگیری دسترسی ندارد.")
            return self.form_invalid(form)
        return super().form_valid(form)


def panel_logout(request):
    logout(request)
    return redirect("panel:login")


@panel_login_required
def dashboard(request):
    if user_is_panel_manager(request.user):
        from panel.services import maybe_run_daily_distribution

        daily = maybe_run_daily_distribution(actor=request.user)
        if daily and daily.get("assigned"):
            messages.info(
                request,
                f"توزیع روزانه انجام شد: {daily['assigned']} پرونده تخصیص یافت.",
            )

    qs = cases_queryset_for(request.user)
    now = timezone.now()
    today = timezone.localtime(now).date()
    day_start = timezone.make_aware(datetime.combine(today, time.min))
    day_end = day_start + timedelta(days=1)
    open_qs = qs.exclude(
        status__in=[CustomerCase.STATUS_CLOSED_LOST, CustomerCase.STATUS_CLOSED_WON]
    )
    counts = {
        "overdue": open_qs.filter(next_follow_up_at__lte=now).count(),
        "today": open_qs.filter(
            next_follow_up_at__gte=now, next_follow_up_at__lt=day_end
        ).count(),
        "new": open_qs.filter(stage=CustomerCase.STAGE_ATTRACTION).count(),
        "open_total": open_qs.count(),
        "mine": open_qs.filter(assigned_to=request.user).count(),
        "unassigned": open_qs.filter(assigned_to__isnull=True).count()
        if user_is_panel_manager(request.user)
        else open_qs.filter(assigned_to__isnull=True).count(),
    }
    overdue_list = open_qs.filter(next_follow_up_at__lte=now).order_by("next_follow_up_at")[:8]
    today_list = open_qs.filter(
        next_follow_up_at__gt=now, next_follow_up_at__lt=day_end
    ).order_by("next_follow_up_at")[:8]
    recent = qs.order_by("-updated_at")[:8]
    stage_map = dict(CustomerCase.STAGE_CHOICES)
    count_by_stage = {s["stage"]: s["c"] for s in open_qs.values("stage").annotate(c=Count("id"))}
    stages = []
    for key in FLOW_PIPELINE:
        c = int(count_by_stage.get(key, 0))
        stages.append({"key": key, "label": stage_map.get(key, key), "count": c})
    stage_max = max((s["count"] for s in stages), default=1) or 1
    for s in stages:
        s["pct"] = int(round((s["count"] / stage_max) * 100)) if stage_max else 0

    first_name = (
        (request.user.first_name or "").strip()
        or (request.user.get_full_name() or "").strip().split(" ")[0]
        or request.user.username
    )

    return render(
        request,
        "panel/dashboard.html",
        {
            "counts": counts,
            "overdue_list": overdue_list,
            "today_list": today_list,
            "recent": recent,
            "stages": stages,
            "stage_max": stage_max,
            "greeting_name": first_name,
            "today_date": today,
            "is_manager": user_is_panel_manager(request.user),
            "call_form": QuickCallForm(),
        },
    )


def _filtered_cases(request):
    form = CaseFilterForm(request.GET or None, user=request.user)
    qs = cases_queryset_for(request.user)
    now = timezone.now()
    today = timezone.localtime(now).date()
    day_start = timezone.make_aware(datetime.combine(today, time.min))
    day_end = day_start + timedelta(days=1)

    if form.is_valid():
        q = (form.cleaned_data.get("q") or "").strip()
        scope = form.cleaned_data.get("scope") or ""
        source = form.cleaned_data.get("source") or ""
        stage = form.cleaned_data.get("stage") or ""
        assignee = form.cleaned_data.get("assignee") if "assignee" in form.fields else None

        if q:
            phone_q = normalize_phone(q)
            qs = qs.filter(
                Q(customer__full_name__icontains=q)
                | Q(case_code__icontains=q)
                | Q(customer__phone_normalized__icontains=phone_q or q)
                | Q(customer__phone_display__icontains=q)
                | Q(target_country__icontains=q)
            )
        if source:
            qs = qs.filter(source_type=source)
        if stage:
            qs = qs.filter(stage=stage)
        if assignee:
            qs = qs.filter(assigned_to=assignee)

        if scope == "mine":
            qs = qs.filter(assigned_to=request.user)
        elif scope == "unassigned":
            qs = qs.filter(assigned_to__isnull=True).exclude(
                status__in=[CustomerCase.STATUS_CLOSED_LOST, CustomerCase.STATUS_CLOSED_WON]
            )
        elif scope == "overdue":
            qs = qs.exclude(
                status__in=[CustomerCase.STATUS_CLOSED_LOST, CustomerCase.STATUS_CLOSED_WON]
            ).filter(next_follow_up_at__lte=now)
        elif scope == "today":
            qs = qs.exclude(
                status__in=[CustomerCase.STATUS_CLOSED_LOST, CustomerCase.STATUS_CLOSED_WON]
            ).filter(next_follow_up_at__gte=day_start, next_follow_up_at__lt=day_end)
        elif scope == "new":
            qs = qs.filter(stage=CustomerCase.STAGE_ATTRACTION).exclude(
                status__in=[CustomerCase.STATUS_CLOSED_LOST, CustomerCase.STATUS_CLOSED_WON]
            )
        elif scope == "closed":
            qs = qs.filter(
                status__in=[CustomerCase.STATUS_CLOSED_LOST, CustomerCase.STATUS_CLOSED_WON]
            )
        else:
            qs = qs.exclude(
                status__in=[CustomerCase.STATUS_CLOSED_LOST, CustomerCase.STATUS_CLOSED_WON]
            )
    else:
        qs = qs.exclude(
            status__in=[CustomerCase.STATUS_CLOSED_LOST, CustomerCase.STATUS_CLOSED_WON]
        )

    return form, qs.order_by("next_follow_up_at", "-updated_at")


@panel_login_required
def case_list(request):
    form, qs = _filtered_cases(request)
    scope = ""
    if form.is_valid():
        scope = form.cleaned_data.get("scope") or ""
    else:
        scope = (request.GET.get("scope") or "").strip()

    scope_labels = {
        "": "همه باز",
        "mine": "مال من",
        "unassigned": "بدون مسئول",
        "overdue": "عقب‌افتاده",
        "today": "پیگیری امروز",
        "new": "جدید / جذب",
        "closed": "مختومه / موفق",
    }
    cases = list(qs[:200])
    return render(
        request,
        "panel/case_list.html",
        {
            "form": form,
            "cases": cases,
            "cases_count": len(cases),
            "scope": scope,
            "scope_label": scope_labels.get(scope, "پرونده‌ها"),
            "is_manager": user_is_panel_manager(request.user),
            "call_form": QuickCallForm(),
        },
    )


@panel_login_required
def followup_queue(request):
    """صف پیگیری اختصاصی: امروز + عقب‌افتاده."""
    qs = cases_queryset_for(request.user).exclude(
        status__in=[CustomerCase.STATUS_CLOSED_LOST, CustomerCase.STATUS_CLOSED_WON]
    )
    mine = request.GET.get("mine") == "1"
    if mine:
        qs = qs.filter(assigned_to=request.user)

    now = timezone.now()
    today = timezone.localtime(now).date()
    day_end = timezone.make_aware(datetime.combine(today, time.min)) + timedelta(days=1)
    overdue_qs = qs.filter(next_follow_up_at__lte=now).order_by("next_follow_up_at")
    due_today_qs = qs.filter(next_follow_up_at__gt=now, next_follow_up_at__lt=day_end).order_by(
        "next_follow_up_at"
    )
    overdue_count = overdue_qs.count()
    today_count = due_today_qs.count()

    first_name = (
        (request.user.first_name or "").strip()
        or (request.user.get_full_name() or "").strip().split(" ")[0]
        or request.user.username
    )

    return render(
        request,
        "panel/followup.html",
        {
            "overdue": overdue_qs[:100],
            "due_today": due_today_qs[:100],
            "overdue_count": overdue_count,
            "today_count": today_count,
            "total_queue": overdue_count + today_count,
            "mine": mine,
            "greeting_name": first_name,
            "today_date": today,
            "is_manager": user_is_panel_manager(request.user),
            "call_form": QuickCallForm(),
        },
    )


@panel_login_required
def case_detail(request, pk: int):
    case = get_object_or_404(
        CustomerCase.objects.select_related("customer", "assigned_to", "evaluation", "consultation"),
        pk=pk,
    )
    if not cases_queryset_for(request.user).filter(pk=case.pk).exists():
        raise Http404()

    call_form = QuickCallForm()
    close_form = CloseCaseForm()
    stage_form = StageChangeForm(initial={"stage": case.stage})
    assign_form = AssignForm(user=request.user, initial={"assigned_to": case.assigned_to_id})
    appointment_form = AppointmentForm()
    doc_form = DocumentUploadForm()
    events = case.events.select_related("created_by")[:50]
    appointments = case.appointments.select_related("assignee").order_by("starts_at")[:20]
    documents = case.documents.select_related("uploaded_by")[:30]
    checklist = checklist_for_case(case)
    scripts = STAGE_SCRIPTS.get(case.stage, [])

    phone = case.customer.phone_display or case.customer.phone_normalized
    wa = normalize_phone(phone)
    if wa.startswith("0"):
        wa_link = "98" + wa[1:]
    elif wa.startswith("mail:"):
        wa_link = ""
    else:
        wa_link = wa

    return render(
        request,
        "panel/case_detail.html",
        {
            "case": case,
            "events": events,
            "appointments": appointments,
            "documents": documents,
            "checklist": checklist,
            "scripts": scripts,
            "call_form": call_form,
            "close_form": close_form,
            "stage_form": stage_form,
            "assign_form": assign_form,
            "appointment_form": appointment_form,
            "doc_form": doc_form,
            "is_manager": user_is_panel_manager(request.user),
            "can_edit": can_manage_case(request.user, case),
            "tel_href": f"tel:{phone}" if phone and not str(phone).startswith("mail:") else "",
            "wa_href": f"https://wa.me/{wa_link}" if wa_link else "",
            "hide_global_quick_call": True,
            "flow_steps": flow_steps_for_case(case),
            "check_progress": checklist_progress_for_case(case),
        },
    )


@panel_login_required
@require_POST
def case_call(request, pk: int):
    case = get_object_or_404(CustomerCase, pk=pk)
    if not can_manage_case(request.user, case):
        return HttpResponseForbidden("اجازه ویرایش این پرونده را ندارید.")
    form = QuickCallForm(request.POST)
    if not form.is_valid():
        messages.error(request, "فرم تماس ناقص است.")
        return redirect("panel:case_detail", pk=pk)
    custom_dt = None
    if form.cleaned_data["follow_preset"] == "custom":
        d = parse_jalali_date(form.cleaned_data.get("custom_jalali_date") or "")
        if not d:
            messages.error(request, "برای موعد دلخواه تاریخ شمسی معتبر وارد کنید.")
            return redirect(request.POST.get("next") or f"/panel/cases/{pk}/")
        custom_dt = combine_local(d, time(10, 0))
    if case.assigned_to_id is None:
        case.assigned_to = request.user
        case.save(update_fields=["assigned_to", "updated_at"])
        CaseEvent.objects.create(
            case=case,
            event_type=CaseEvent.TYPE_ASSIGN,
            notes=f"تخصیص خودکار به {request.user.get_username()}",
            created_by=request.user,
        )
    apply_call_event(
        case,
        user=request.user,
        contact_result=form.cleaned_data["contact_result"],
        notes=form.cleaned_data.get("notes") or "",
        follow_preset=form.cleaned_data["follow_preset"],
        custom_follow_up=custom_dt,
    )
    messages.success(request, "تماس ثبت شد.")
    next_url = (form.cleaned_data.get("next") or "").strip()
    if next_url.startswith("/panel/"):
        return redirect(next_url)
    return redirect("panel:case_detail", pk=pk)


@panel_login_required
@require_POST
def case_close(request, pk: int):
    case = get_object_or_404(CustomerCase, pk=pk)
    if not can_manage_case(request.user, case):
        return HttpResponseForbidden("اجازه بستن این پرونده را ندارید.")
    form = CloseCaseForm(request.POST)
    if not form.is_valid():
        messages.error(request, "دلیل مختومه را کامل کنید.")
        return redirect("panel:case_detail", pk=pk)
    case.stage = CustomerCase.STAGE_LOST
    case.status = CustomerCase.STATUS_CLOSED_LOST
    case.loss_reason = form.cleaned_data["loss_reason"]
    case.loss_note = form.cleaned_data["loss_note"]
    case.closed_at = timezone.now()
    case.next_follow_up_at = None
    case.apply_stage_progress()
    case.save()
    CaseEvent.objects.create(
        case=case,
        event_type=CaseEvent.TYPE_CLOSE,
        notes=f"{case.get_loss_reason_display()}: {case.loss_note}",
        created_by=request.user,
    )
    messages.success(request, "پرونده مختومه شد.")
    return redirect("panel:case_detail", pk=pk)


@panel_login_required
@require_POST
def case_stage(request, pk: int):
    case = get_object_or_404(CustomerCase, pk=pk)
    if not can_manage_case(request.user, case):
        return HttpResponseForbidden("اجازه تغییر مرحله ندارید.")
    form = StageChangeForm(request.POST)
    if not form.is_valid():
        messages.error(request, "مرحله نامعتبر است.")
        return redirect("panel:case_detail", pk=pk)
    old = case.get_stage_display()
    case.stage = form.cleaned_data["stage"]
    if case.status in (CustomerCase.STATUS_CLOSED_LOST, CustomerCase.STATUS_CLOSED_WON):
        case.status = CustomerCase.STATUS_OPEN
        case.closed_at = None
        case.loss_reason = ""
        case.loss_note = ""
    if case.stage == CustomerCase.STAGE_WON:
        case.status = CustomerCase.STATUS_CLOSED_WON
        case.closed_at = timezone.now()
    case.apply_stage_progress()
    case.save()
    CaseEvent.objects.create(
        case=case,
        event_type=CaseEvent.TYPE_STAGE,
        notes=f"از «{old}» به «{case.get_stage_display()}»",
        created_by=request.user,
        meta={"from": old, "to": case.stage},
    )
    messages.success(request, "مرحله به‌روز شد.")
    return redirect("panel:case_detail", pk=pk)


@panel_login_required
@require_POST
def case_assign(request, pk: int):
    case = get_object_or_404(CustomerCase, pk=pk)
    is_manager = user_is_panel_manager(request.user)
    # پرسنل فقط می‌تواند به خودش بگیرد
    form = AssignForm(request.POST, user=request.user)
    if not form.is_valid():
        messages.error(request, "تخصیص نامعتبر است.")
        return redirect("panel:case_detail", pk=pk)
    new_owner = form.cleaned_data["assigned_to"]
    if not is_manager:
        if new_owner and new_owner.id != request.user.id:
            return HttpResponseForbidden("پرسنل فقط می‌تواند پرونده را به خودش بگیرد.")
        if case.assigned_to_id and case.assigned_to_id != request.user.id:
            return HttpResponseForbidden("این پرونده متعلق به شخص دیگری است.")
    old = case.assigned_to.get_username() if case.assigned_to_id else "—"
    case.assigned_to = new_owner
    case.save(update_fields=["assigned_to", "updated_at"])
    new_name = new_owner.get_username() if new_owner else "—"
    CaseEvent.objects.create(
        case=case,
        event_type=CaseEvent.TYPE_ASSIGN,
        notes=f"تخصیص از {old} به {new_name}",
        created_by=request.user,
    )
    messages.success(request, "مسئول پرونده به‌روز شد.")
    return redirect("panel:case_detail", pk=pk)


@panel_login_required
@require_POST
def case_claim(request, pk: int):
    case = get_object_or_404(CustomerCase, pk=pk)
    if case.assigned_to_id and case.assigned_to_id != request.user.id:
        if not user_is_panel_manager(request.user):
            return HttpResponseForbidden("پرونده قبلاً تخصیص داده شده.")
    case.assigned_to = request.user
    case.save(update_fields=["assigned_to", "updated_at"])
    CaseEvent.objects.create(
        case=case,
        event_type=CaseEvent.TYPE_ASSIGN,
        notes=f"برداشت توسط {request.user.get_username()}",
        created_by=request.user,
    )
    messages.success(request, "پرونده به شما تخصیص داده شد.")
    return redirect("panel:case_detail", pk=pk)


@panel_login_required
def search(request):
    q = (request.GET.get("q") or "").strip()
    results = []
    if q:
        phone_q = normalize_phone(q)
        results = (
            cases_queryset_for(request.user)
            .filter(
                Q(customer__full_name__icontains=q)
                | Q(case_code__icontains=q)
                | Q(customer__phone_normalized__icontains=phone_q or q)
                | Q(customer__phone_display__icontains=q)
                | Q(internal_notes__icontains=q)
                | Q(target_country__icontains=q)
            )
            .order_by("-updated_at")[:40]
        )
    return render(
        request,
        "panel/search.html",
        {
            "q": q,
            "results": results,
            "results_count": len(results),
            "is_manager": user_is_panel_manager(request.user),
            "call_form": QuickCallForm(),
        },
    )


@panel_login_required
def case_create(request):
    form = ManualCaseForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        customer, _ = get_or_create_customer(
            full_name=form.cleaned_data["full_name"],
            phone=form.cleaned_data["phone"],
            email=form.cleaned_data.get("email") or "",
        )
        assignee = request.user if form.cleaned_data.get("assign_to_me") else None
        case = open_case_for_customer(
            customer,
            source_type=CustomerCase.SOURCE_MANUAL,
            stage=form.cleaned_data["stage"],
            assigned_to=assignee,
            target_country=form.cleaned_data.get("target_country") or "",
            target_degree=form.cleaned_data.get("target_degree") or "",
            actor=request.user,
            note=form.cleaned_data.get("notes") or "ورود دستی از پنل",
        )
        if form.cleaned_data.get("notes"):
            case.internal_notes = form.cleaned_data["notes"]
            case.save(update_fields=["internal_notes", "updated_at"])
        messages.success(request, f"پرونده {case.case_code} ساخته شد.")
        return redirect("panel:case_detail", pk=case.pk)
    return render(
        request,
        "panel/case_create.html",
        {"form": form, "is_manager": user_is_panel_manager(request.user)},
    )


@panel_login_required
@require_POST
def case_appointment(request, pk: int):
    case = get_object_or_404(CustomerCase, pk=pk)
    if not can_manage_case(request.user, case):
        return HttpResponseForbidden("اجازه ثبت جلسه ندارید.")
    form = AppointmentForm(request.POST)
    if not form.is_valid():
        messages.error(request, "تاریخ/ساعت جلسه را درست وارد کنید (مثلاً 1405/04/31 و 10:30).")
        return redirect("panel:case_detail", pk=pk)
    d = parse_jalali_date(form.cleaned_data["jalali_date"])
    t = parse_time_hm(form.cleaned_data["time_hm"])
    if not d or not t:
        messages.error(request, "فرمت تاریخ یا ساعت نامعتبر است.")
        return redirect("panel:case_detail", pk=pk)
    starts = combine_local(d, t)
    ends = starts + timedelta(minutes=30)
    kind = form.cleaned_data["kind"]
    title = form.cleaned_data.get("title") or dict(CaseAppointment.KIND_CHOICES).get(kind, "جلسه")
    appt = CaseAppointment.objects.create(
        case=case,
        title=title,
        kind=kind,
        mode=form.cleaned_data["mode"],
        starts_at=starts,
        ends_at=ends,
        assignee=case.assigned_to or request.user,
        notes=form.cleaned_data.get("notes") or "",
    )
    if kind == CaseAppointment.KIND_SPECIALIZED and case.stage in (
        CustomerCase.STAGE_ATTRACTION,
        CustomerCase.STAGE_INITIAL,
        CustomerCase.STAGE_FOLLOW_UP,
    ):
        old = case.get_stage_display()
        case.stage = CustomerCase.STAGE_SPECIALIZED
        case.apply_stage_progress()
        case.save(update_fields=["stage", "progress", "updated_at"])
        CaseEvent.objects.create(
            case=case,
            event_type=CaseEvent.TYPE_STAGE,
            notes=f"به‌خاطر جلسه تخصصی: از «{old}» به «{case.get_stage_display()}»",
            created_by=request.user,
        )
    CaseEvent.objects.create(
        case=case,
        event_type=CaseEvent.TYPE_NOTE,
        notes=f"جلسه ثبت شد: {appt.get_kind_display()} — {form.cleaned_data['jalali_date']} {form.cleaned_data['time_hm']}",
        created_by=request.user,
        meta={"appointment_id": appt.pk},
    )
    messages.success(request, "جلسه در تقویم شمسی ثبت شد.")
    return redirect("panel:case_detail", pk=pk)


@panel_login_required
def calendar_view(request):
    from panel.services import sync_consultation_appointments

    # همگام‌سازی سبک: رزروهای سایت با اسلات روی تقویم دیده شوند
    try:
        sync_consultation_appointments()
    except Exception:
        pass

    jy_s = request.GET.get("jy")
    jm_s = request.GET.get("jm")
    ty, tm, td = jalali_today()
    try:
        jy = int(jy_s) if jy_s else ty
        jm = int(jm_s) if jm_s else tm
        if not (1 <= jm <= 12):
            raise ValueError
    except (TypeError, ValueError):
        jy, jm = ty, tm

    prev_y, prev_m = shift_jalali_month(jy, jm, -1)
    next_y, next_m = shift_jalali_month(jy, jm, 1)
    start_g, end_g = jalali_month_bounds(jy, jm)
    start_dt = timezone.make_aware(datetime.combine(start_g, time.min))
    end_dt = timezone.make_aware(datetime.combine(end_g, time.max))

    is_manager = user_is_panel_manager(request.user)
    case_ids = cases_queryset_for(request.user).values_list("id", flat=True)
    # مدیر: پیش‌فرض همه؛ با mine=1 فقط خودش. پرسنل: همهٔ جلسات پرونده‌های قابل‌مشاهده
    mine_only = is_manager and request.GET.get("mine") == "1"
    appts = CaseAppointment.objects.filter(
        case_id__in=case_ids,
        starts_at__gte=start_dt,
        starts_at__lte=end_dt,
    ).select_related("case", "case__customer", "assignee", "consultation", "consultation__slot")
    if mine_only:
        appts = appts.filter(Q(assignee=request.user) | Q(case__assigned_to=request.user))

    ordered = list(appts.order_by("starts_at"))
    by_day: dict[date, list] = {}
    for a in ordered:
        d = timezone.localtime(a.starts_at).date()
        by_day.setdefault(d, []).append(a)

    cells = build_month_cells(jy, jm)
    for cell in cells:
        if cell.get("empty"):
            continue
        cell["appointments"] = by_day.get(cell["gdate"], [])

    selected = (request.GET.get("day") or "").strip()
    if not selected and jy == ty and jm == tm:
        selected = str(td)

    day_list = []
    selected_label = ""
    selected_day = ""
    if selected:
        d = parse_jalali_date(f"{jy}/{jm}/{selected}")
        if d:
            day_list = by_day.get(d, [])
            from core.utils import format_jalali_display

            selected_label = format_jalali_display(d)
            try:
                selected_day = int(selected)
            except (TypeError, ValueError):
                selected_day = ""

    return render(
        request,
        "panel/calendar.html",
        {
            "is_manager": is_manager,
            "jy": jy,
            "jm": jm,
            "title": month_title(jy, jm),
            "prev_y": prev_y,
            "prev_m": prev_m,
            "next_y": next_y,
            "next_m": next_m,
            "cells": cells,
            "weekdays": ["ش", "ی", "د", "س", "چ", "پ", "ج"],
            "mine_only": mine_only,
            "day_list": day_list,
            "selected_label": selected_label,
            "selected_day": selected_day,
            "month_list": ordered,
            "month_count": len(ordered),
            "today_jy": ty,
            "today_jm": tm,
            "today_jd": td,
        },
    )


@panel_manager_required
def report_view(request):
    from panel.services import build_manager_analytics

    period = (request.GET.get("period") or "30").strip()
    if period not in {"7", "30", "month", "all"}:
        period = "30"
    data = build_manager_analytics(period=period)
    data["is_manager"] = True
    data["period"] = period
    return render(request, "panel/report.html", data)


@panel_manager_required
def manage_view(request):
    """ابزارهای مدیریت تیم: تخصیص گروهی، همگام‌سازی، برد پرسنل."""
    from django.contrib.auth.models import User

    from panel.services import (
        ROLE_MANAGER,
        ROLE_STAFF,
        build_manager_analytics,
        distribute_cases,
        ensure_staff_profiles,
        sync_consultation_appointments,
        sync_contact_messages,
        sync_leads_to_cases,
    )
    from panel.models import PanelSettings

    ensure_staff_profiles()
    staff_qs = User.objects.filter(
        is_active=True, groups__name__in=[ROLE_STAFF, ROLE_MANAGER]
    ).distinct().order_by("username")

    if request.method == "POST":
        action = request.POST.get("action") or ""
        if action == "bulk_assign":
            assignee_id = request.POST.get("assignee")
            limit = request.POST.get("limit") or "50"
            try:
                limit_n = max(1, min(300, int(limit)))
            except (TypeError, ValueError):
                limit_n = 50
            assignee = staff_qs.filter(pk=assignee_id).first()
            if not assignee:
                messages.error(request, "مسئول را انتخاب کنید.")
            else:
                cases = list(
                    CustomerCase.objects.filter(
                        assigned_to__isnull=True,
                        status__in=[CustomerCase.STATUS_OPEN, CustomerCase.STATUS_WAITING],
                    ).order_by("next_follow_up_at", "id")[:limit_n]
                )
                n = 0
                for case in cases:
                    case.assigned_to = assignee
                    case.save(update_fields=["assigned_to", "updated_at"])
                    CaseEvent.objects.create(
                        case=case,
                        event_type=CaseEvent.TYPE_ASSIGN,
                        notes=f"تخصیص گروهی مدیر به «{assignee.get_username()}»",
                        created_by=request.user,
                        meta={"bulk": True},
                    )
                    n += 1
                messages.success(request, f"{n} پرونده به {assignee.get_username()} تخصیص یافت.")
            return redirect("panel:manage")

        if action == "rebalance":
            settings_obj = PanelSettings.load()
            result = distribute_cases(
                mode=settings_obj.daily_followup_mode or PanelSettings.MODE_LEAST_LOAD,
                scope=PanelSettings.SCOPE_UNASSIGNED,
                actor=request.user,
            )
            messages.success(request, f"توزیع انجام شد: {result['assigned']} پرونده.")
            return redirect("panel:manage")

        if action == "sync_leads":
            stats = sync_leads_to_cases()
            contacts = sync_contact_messages()
            appts = sync_consultation_appointments()
            messages.success(
                request,
                f"همگام‌سازی: ارزیابی {stats.get('evaluations', 0)} · مشاوره {stats.get('consultations', 0)} · تماس {contacts} · جلسه {appts}",
            )
            return redirect("panel:manage")

        if action == "reassign_staff":
            from_id = request.POST.get("from_user")
            to_id = request.POST.get("to_user")
            limit = request.POST.get("re_limit") or "30"
            try:
                limit_n = max(1, min(200, int(limit)))
            except (TypeError, ValueError):
                limit_n = 30
            src = staff_qs.filter(pk=from_id).first()
            dst = staff_qs.filter(pk=to_id).first()
            if not src or not dst or src.pk == dst.pk:
                messages.error(request, "مبدأ و مقصد را درست انتخاب کنید.")
            else:
                cases = list(
                    CustomerCase.objects.filter(
                        assigned_to=src,
                        status__in=[CustomerCase.STATUS_OPEN, CustomerCase.STATUS_WAITING],
                    ).order_by("next_follow_up_at")[:limit_n]
                )
                for case in cases:
                    case.assigned_to = dst
                    case.save(update_fields=["assigned_to", "updated_at"])
                    CaseEvent.objects.create(
                        case=case,
                        event_type=CaseEvent.TYPE_ASSIGN,
                        notes=f"انتقال مدیر از «{src.get_username()}» به «{dst.get_username()}»",
                        created_by=request.user,
                        meta={"reassign": True},
                    )
                messages.success(
                    request,
                    f"{len(cases)} پرونده از {src.get_username()} به {dst.get_username()} منتقل شد.",
                )
            return redirect("panel:manage")

    analytics = build_manager_analytics(period="30")
    return render(
        request,
        "panel/manage.html",
        {
            "is_manager": True,
            "staff_users": staff_qs,
            "staff_rows": analytics["staff_rows"],
            "unassigned": analytics["unassigned"],
            "overdue": analytics["overdue"],
            "open_total": analytics["open_total"],
        },
    )


@panel_manager_required
def report_export_csv(request):
    import csv

    from django.http import HttpResponse

    from core.utils import format_jalali_display

    response = HttpResponse(content_type="text/csv; charset=utf-8-sig")
    response["Content-Disposition"] = 'attachment; filename="panel-cases.csv"'
    writer = csv.writer(response)
    writer.writerow(
        ["کد", "نام", "موبایل", "مرحله", "وضعیت", "مسئول", "منبع", "موعد پیگیری", "کشور"]
    )
    qs = (
        CustomerCase.objects.select_related("customer", "assigned_to")
        .exclude(status__in=[CustomerCase.STATUS_CLOSED_LOST, CustomerCase.STATUS_CLOSED_WON])
        .order_by("next_follow_up_at")[:2000]
    )
    for c in qs:
        due = ""
        if c.next_follow_up_at:
            due = format_jalali_display(timezone.localtime(c.next_follow_up_at).date())
        writer.writerow(
            [
                c.case_code,
                c.customer.full_name,
                c.customer.phone_display or c.customer.phone_normalized,
                c.get_stage_display(),
                c.get_status_display(),
                c.assigned_to.get_username() if c.assigned_to_id else "",
                c.get_source_type_display(),
                due,
                c.target_country,
            ]
        )
    return response


@panel_login_required
@require_POST
def case_checklist_toggle(request, pk: int):
    case = get_object_or_404(CustomerCase, pk=pk)
    if not can_manage_case(request.user, case):
        return HttpResponseForbidden("اجازه ویرایش ندارید.")
    key = (request.POST.get("key") or "").strip()
    done = request.POST.get("done") == "1"
    valid = {i["key"] for i in checklist_for_case(case)}
    if key not in valid:
        messages.error(request, "آیتم چک‌لیست نامعتبر است.")
    else:
        set_checklist_item(case, key, done)
        messages.success(request, "چک‌لیست به‌روز شد.")
    return redirect("panel:case_detail", pk=pk)


@panel_login_required
@require_POST
def case_document_upload(request, pk: int):
    case = get_object_or_404(CustomerCase, pk=pk)
    if not can_manage_case(request.user, case):
        return HttpResponseForbidden("اجازه آپلود ندارید.")
    form = DocumentUploadForm(request.POST, request.FILES)
    if not form.is_valid():
        messages.error(request, "فایل را انتخاب کنید.")
        return redirect("panel:case_detail", pk=pk)
    title = form.cleaned_data.get("title") or form.cleaned_data["file"].name
    CaseDocument.objects.create(
        case=case,
        title=title[:150],
        file=form.cleaned_data["file"],
        uploaded_by=request.user,
    )
    CaseEvent.objects.create(
        case=case,
        event_type=CaseEvent.TYPE_NOTE,
        notes=f"مدرک آپلود شد: {title}",
        created_by=request.user,
    )
    messages.success(request, "مدرک ذخیره شد.")
    return redirect("panel:case_detail", pk=pk)


@panel_login_required
@require_POST
def case_reopen(request, pk: int):
    case = get_object_or_404(CustomerCase, pk=pk)
    if not can_manage_case(request.user, case):
        return HttpResponseForbidden("اجازه بازگشایی ندارید.")
    case.status = CustomerCase.STATUS_OPEN
    case.stage = CustomerCase.STAGE_FOLLOW_UP
    case.loss_reason = ""
    case.loss_note = ""
    case.closed_at = None
    case.next_follow_up_at = timezone.now()
    case.apply_stage_progress()
    case.save()
    CaseEvent.objects.create(
        case=case,
        event_type=CaseEvent.TYPE_REOPEN,
        notes="پرونده دوباره باز شد",
        created_by=request.user,
    )
    messages.success(request, "پرونده باز شد.")
    return redirect("panel:case_detail", pk=pk)


@panel_login_required
def search_suggest(request):
    from django.http import JsonResponse

    q = (request.GET.get("q") or "").strip()
    if len(q) < 2:
        return JsonResponse({"results": []})
    phone_q = normalize_phone(q)
    qs = (
        cases_queryset_for(request.user)
        .filter(
            Q(customer__full_name__icontains=q)
            | Q(case_code__icontains=q)
            | Q(customer__phone_normalized__icontains=phone_q or q)
            | Q(customer__phone_display__icontains=q)
        )
        .select_related("customer")
        .order_by("-updated_at")[:8]
    )
    results = [
        {
            "id": c.pk,
            "code": c.case_code,
            "name": c.customer.full_name,
            "phone": c.customer.phone_display or c.customer.phone_normalized,
            "stage": c.get_stage_display(),
            "url": f"/panel/cases/{c.pk}/",
        }
        for c in qs
    ]
    return JsonResponse({"results": results})


@panel_login_required
def notifications_api(request):
    from django.http import JsonResponse
    from django.utils.dateparse import parse_datetime

    from panel.services import notification_payload_for

    since_raw = (request.GET.get("since") or "").strip()
    since = parse_datetime(since_raw) if since_raw else None
    if since and timezone.is_naive(since):
        since = timezone.make_aware(since)
    payload = notification_payload_for(request.user, since=since)
    return JsonResponse(payload)


@panel_login_required
def flow_view(request):
    scope = (request.GET.get("scope") or "open").strip()
    if scope not in {"open", "all", "overdue", "waiting", "mine"}:
        scope = "open"
    mine = scope == "mine" or request.GET.get("mine") == "1"
    board = build_flow_board(request.user, scope=scope, mine=mine)
    return render(
        request,
        "panel/flow.html",
        {
            "board": board,
            "scope": scope,
            "mine": mine,
            "is_manager": user_is_panel_manager(request.user),
            "call_form": QuickCallForm(),
        },
    )


@panel_login_required
def help_page(request):
    return render(
        request,
        "panel/help.html",
        {"is_manager": user_is_panel_manager(request.user)},
    )


@panel_manager_required
def settings_view(request):
    from panel.forms import PanelSettingsForm
    from panel.models import PanelSettings, StaffAssignmentProfile
    from panel.services import (
        distribute_cases,
        ensure_staff_profiles,
        maybe_run_daily_distribution,
        unique_active_assignees,
    )

    ensure_staff_profiles()
    settings_obj = PanelSettings.load()

    if request.method == "POST":
        action = request.POST.get("action") or "save"
        if action == "run_daily":
            result = maybe_run_daily_distribution(actor=request.user, force=True) or {
                "assigned": 0
            }
            messages.success(
                request,
                f"توزیع اجرا شد: {result.get('assigned', 0)} پرونده تخصیص یافت.",
            )
            return redirect("panel:settings")
        if action == "assign_unassigned":
            result = distribute_cases(
                mode=settings_obj.daily_followup_mode or PanelSettings.MODE_LEAST_LOAD,
                scope=PanelSettings.SCOPE_UNASSIGNED,
                actor=request.user,
            )
            messages.success(
                request,
                f"همهٔ بدون‌مسئول: {result['assigned']} پرونده تخصیص یافت.",
            )
            return redirect("panel:settings")

        form = PanelSettingsForm(request.POST)
        if form.is_valid():
            settings_obj.auto_assign_enabled = form.cleaned_data["auto_assign_enabled"]
            settings_obj.auto_assign_mode = form.cleaned_data["auto_assign_mode"]
            settings_obj.fixed_assignee = form.cleaned_data.get("fixed_assignee")
            settings_obj.daily_followup_enabled = form.cleaned_data["daily_followup_enabled"]
            settings_obj.daily_followup_mode = form.cleaned_data["daily_followup_mode"]
            settings_obj.daily_followup_scope = form.cleaned_data["daily_followup_scope"]
            settings_obj.updated_by = request.user
            settings_obj.save()

            # staff toggles: staff_<id>=on, weight_<id>, order_<id>
            for profile in StaffAssignmentProfile.objects.select_related("user"):
                profile.is_active = request.POST.get(f"staff_{profile.user_id}") == "on"
                try:
                    profile.weight = max(1, min(10, int(request.POST.get(f"weight_{profile.user_id}", 1))))
                except (TypeError, ValueError):
                    profile.weight = 1
                try:
                    profile.sort_order = max(0, int(request.POST.get(f"order_{profile.user_id}", 0)))
                except (TypeError, ValueError):
                    profile.sort_order = 0
                profile.save(update_fields=["is_active", "weight", "sort_order", "updated_at"])

            messages.success(request, "تنظیمات ذخیره شد.")
            return redirect("panel:settings")
        messages.error(request, "فرم تنظیمات را بررسی کنید.")
    else:
        form = PanelSettingsForm(
            initial={
                "auto_assign_enabled": settings_obj.auto_assign_enabled,
                "auto_assign_mode": settings_obj.auto_assign_mode,
                "fixed_assignee": settings_obj.fixed_assignee_id,
                "daily_followup_enabled": settings_obj.daily_followup_enabled,
                "daily_followup_mode": settings_obj.daily_followup_mode,
                "daily_followup_scope": settings_obj.daily_followup_scope,
            }
        )

    profiles = list(
        StaffAssignmentProfile.objects.select_related("user").order_by(
            "sort_order", "user__username"
        )
    )
    for p in profiles:
        p.open_load = CustomerCase.objects.filter(
            assigned_to=p.user,
            status__in=[CustomerCase.STATUS_OPEN, CustomerCase.STATUS_WAITING],
        ).count()
    unassigned_n = CustomerCase.objects.filter(
        assigned_to__isnull=True,
        status__in=[CustomerCase.STATUS_OPEN, CustomerCase.STATUS_WAITING],
    ).count()

    return render(
        request,
        "panel/settings.html",
        {
            "is_manager": True,
            "form": form,
            "settings_obj": settings_obj,
            "profiles": profiles,
            "unassigned_n": unassigned_n,
            "active_count": len(unique_active_assignees()),
        },
    )
