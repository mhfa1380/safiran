"""View functions for سفیران آینده روشن website."""
from django.db.models import Q, Sum, Case, When, FloatField
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.core.cache import cache
from django.views.decorators.cache import cache_page

from .forms import ContactForm, ConsultationRequestForm, EvaluationRequestForm, QuickConsultationForm
from .models import (
    BlogPost,
    ConsultationRequest,
    ConsultationSlot,
    Course,
    Institute,
    Major,
    Service,
    TeamMember,
    University,
)
from .context_processors import get_institute_cached
from .utils import format_jalali_date, format_jalali_display, slot_has_started


def page_not_found(request, exception=None):
    """صفحه ۴۰۴ برای آدرس‌های نامعتبر."""
    return render(request, "404.html", status=404)


def permission_denied(request, exception=None):
    """صفحه ۴۰۳؛ ریدایرکت به صفحه اصلی."""
    return redirect("index")


def csrf_failure(request, reason=""):
    """خطای CSRF؛ ریدایرکت به صفحه اصلی."""
    return redirect("index")


def index(request):
    """صفحه اصلی؛ آخرین ۶ پست وبلاگ (کاروسل ۳ تایی) و خدمات را نمایش می‌دهد."""
    posts_qs = BlogPost.objects.filter(is_published=True)[:6]
    latest_posts = [
        {"post": p, "created_at_jalali": format_jalali_display(p.created_at)}
        for p in posts_qs
    ]
    services = Service.objects.filter(is_active=True)[:6]
    university_count = University.objects.count()
    institute = get_institute_cached()
    # هر اسلات رزرو‌شده نیم‌ساعت محسوب می‌شود
    booked_slots_count = ConsultationSlot.objects.filter(is_booked=True).count()
    consultation_hours = int(round(booked_slots_count * 0.5))
    return render(
        request,
        "core/index.html",
        {
            "latest_posts": latest_posts,
            "services": services,
            "university_count": university_count,
            "countries_count": getattr(institute, "countries_count", 0),
            "consultation_hours": consultation_hours,
            "students_sent": getattr(institute, "students_sent", 0),
        },
    )


def about(request):
    """صفحه درباره ما؛ محتوای مشابه صفحه اول + شمارشگر + اعضای تیم."""
    institute = get_institute_cached()
    team_members = TeamMember.objects.filter(is_active=True)
    university_count = University.objects.count()
    # هر اسلات رزرو‌شده نیم‌ساعت محسوب می‌شود
    booked_slots_count = ConsultationSlot.objects.filter(is_booked=True).count()
    consultation_hours = int(round(booked_slots_count * 0.5))
    return render(
        request,
        "core/about.html",
        {
            "team_members": team_members,
            "university_count": university_count,
            "countries_count": getattr(institute, "countries_count", 0),
            "consultation_hours": consultation_hours,
            "students_sent": getattr(institute, "students_sent", 0),
        },
    )


def team_member_detail(request, pk):
    """صفحه تک‌عضو تیم."""
    member = get_object_or_404(TeamMember, pk=pk, is_active=True)
    return render(request, "core/team_member_detail.html", {"member": member})


@cache_page(60 * 3)
def blog_list(request):
    """لیست پست‌های وبلاگ با جستجو، فیلتر و صفحه‌بندی."""
    qs = BlogPost.objects.filter(is_published=True)

    q = request.GET.get("q", "").strip()
    tag = request.GET.get("tag", "").strip()

    if q:
        qs = qs.filter(
            Q(title__icontains=q)
            | Q(excerpt__icontains=q)
            | Q(content__icontains=q)
        )
    if tag:
        qs = qs.filter(country_tag__icontains=tag)

    paginator = Paginator(qs, 6)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    tags = cache.get("blog_tags")
    if tags is None:
        tags = list(
            BlogPost.objects.filter(is_published=True)
            .exclude(country_tag="")
            .values_list("country_tag", flat=True)
            .distinct()
        )
        cache.set("blog_tags", tags, 300)

    return render(
        request,
        "blog/list.html",
        {
            "page_obj": page_obj,
            "posts": page_obj.object_list,
            "filter_q": q,
            "filter_tag": tag,
            "tags": tags,
        },
    )


def blog_detail(request, slug):
    """صفحه جزئیات یک پست وبلاگ."""
    post = get_object_or_404(BlogPost, slug=slug, is_published=True)
    return render(request, "blog/single.html", {"post": post})


def contact(request):
    """صفحه تماس با ما؛ فرم POST را ذخیره می‌کند."""
    from .forms import generate_math_captcha

    session_key = "contact_captcha_answer"

    if request.method == "POST":
        captcha_expected = request.session.pop(session_key, None)
        form = ContactForm(request.POST, captcha_expected=captcha_expected)
        if form.is_valid():
            form.save()
            return redirect(f"{reverse('contact')}?success=1")
    else:
        form = ContactForm(captcha_expected=None)

    # همیشه کپچای جدید برای نمایش (GET یا خطای POST)
    _, _, captcha_question, captcha_answer = generate_math_captcha()
    request.session[session_key] = captcha_answer

    success = request.GET.get("success") == "1"
    return render(
        request,
        "core/contact.html",
        {"form": form, "success": success, "captcha_question": captcha_question},
    )


def universities(request):
    """برای سازگاری قبلی؛ به صفحه لیست دانشگاه‌ها ریدایرکت می‌کند."""
    return redirect("schools_list")


def majors(request):
    """صفحه رشته‌های تحصیلی؛ محتوا از دیتابیس با فیلتر کشور."""
    qs = Major.objects.filter(is_active=True)
    country = request.GET.get("country", "").strip()
    if country:
        qs = qs.filter(country=country)
    countries = Major.COUNTRY_CHOICES
    return render(
        request,
        "content/majors.html",
        {"majors": qs, "countries": countries, "filter_country": country},
    )


def services(request):
    """صفحه خدمات موسسه؛ محتوا از دیتابیس."""
    services_list = Service.objects.filter(is_active=True)
    return render(request, "content/services.html", {"services": services_list})


def courses_list(request):
    """لیست دوره‌ها با فیلتر کشور."""
    qs = Course.objects.filter(is_active=True)
    country = request.GET.get("country", "").strip()
    if country:
        qs = qs.filter(country=country)
    countries = Course.COUNTRY_CHOICES
    return render(
        request,
        "content/courses_list.html",
        {"courses": qs, "countries": countries, "filter_country": country},
    )


def elements(request):
    return render(request, "core/elements.html")


@cache_page(60 * 5)
def course_details(request, slug):
    """صفحه جزئیات یک دوره."""
    course = get_object_or_404(
        Course.objects.prefetch_related("syllabus_items", "faqs"),
        slug=slug,
        is_active=True,
    )
    course_faqs = list(course.faqs.filter(is_active=True))
    return render(
        request,
        "content/course_details.html",
        {"course": course, "course_faqs": course_faqs},
    )


def major_details(request, slug):
    """صفحه جزئیات یک رشته."""
    major = get_object_or_404(
        Major.objects.prefetch_related("faqs"),
        slug=slug,
        is_active=True,
    )
    major_faqs = list(major.faqs.filter(is_active=True))
    return render(
        request,
        "content/major_details.html",
        {"major": major, "major_faqs": major_faqs},
    )


def quick_consultation(request):
    """ثبت سریع درخواست مشاوره از صفحه لیست دانشگاه‌ها (AJAX)."""
    if request.method != "POST" or not request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({"ok": False, "error": "درخواست نامعتبر"}, status=400)

    form = QuickConsultationForm(request.POST)
    if not form.is_valid():
        err = form.errors.as_json()
        return JsonResponse({"ok": False, "errors": form.errors}, status=400)

    data = form.cleaned_data
    university = None
    if data.get("university_id"):
        try:
            university = University.objects.get(pk=data["university_id"])
        except University.DoesNotExist:
            pass

    ConsultationRequest.objects.create(
        full_name=data["full_name"],
        phone=data["phone"],
        email="",
        consultation_type=ConsultationRequest.ONLINE,
        country=university.country if university else ConsultationRequest.COUNTRY_CANADA,
        interest_university=university,
        description=f"درخواست از صفحه دانشگاه‌ها" + (f" — دانشگاه: {university.name_fa}" if university else ""),
    )
    return JsonResponse({"ok": True, "message": "درخواست شما ثبت شد. کارشناسان به زودی با شما تماس می‌گیرند."})


def appointment(request):
    """صفحه رزرو وقت مشاوره با زمان‌های از پیش تعیین‌شده (انتخاب تاریخ سپس زمان)."""
    from django.utils import timezone

    today = timezone.localdate()
    now = timezone.now()

    # همه اسلات‌های آینده
    base_qs = ConsultationSlot.objects.filter(date__gte=today).order_by("date", "order")
    available_qs = base_qs.filter(is_booked=False)

    # روزهای قابل رزرو: حداقل یک اسلات خالی که هنوز شروع نشده
    raw_days = list(available_qs.values_list("date", flat=True).distinct().order_by("date"))
    available_days = []
    for d in raw_days:
        day_slots = list(available_qs.filter(date=d))
        future_slots = [s for s in day_slots if not slot_has_started(s, now)]
        if future_slots:
            available_days.append(d)

    selected_date = None

    if request.method == "POST":
        # در POST، سعی می‌کنیم تاریخ را از اسلات انتخاب‌شده استخراج کنیم
        slot_id = request.POST.get("slot")
        if slot_id:
            try:
                slot_obj = ConsultationSlot.objects.get(pk=slot_id)
                selected_date = slot_obj.date
            except ConsultationSlot.DoesNotExist:
                selected_date = None
        # اگر تاریخ از اسلات به‌دست نیامد، از پارامتر GET استفاده می‌کنیم
        if not selected_date:
            day_param = request.GET.get("day")
            if day_param:
                try:
                    from datetime import date as _date

                    selected_date = _date.fromisoformat(day_param)
                except ValueError:
                    selected_date = None
    else:
        # در GET، ابتدا از پارامتر day استفاده می‌کنیم
        day_param = request.GET.get("day")
        if day_param:
            try:
                from datetime import date as _date

                selected_date = _date.fromisoformat(day_param)
            except ValueError:
                selected_date = None

    # اگر هنوز تاریخی انتخاب نشده، اولین روز قابل رزرو را استفاده می‌کنیم
    if not selected_date and available_days:
        selected_date = available_days[0]

    # اسلات‌های همان روز (فقط آن‌هایی که هنوز شروع نشده‌اند)
    if selected_date:
        day_all_raw = list(base_qs.filter(date=selected_date))
        day_all_slots = [s for s in day_all_raw if not slot_has_started(s, now)]
        day_available_raw = list(available_qs.filter(date=selected_date))
        day_available_filtered = [s for s in day_available_raw if not slot_has_started(s, now)]
        pks = [s.pk for s in day_available_filtered]
        day_available_slots = ConsultationSlot.objects.filter(pk__in=pks).order_by("order") if pks else ConsultationSlot.objects.none()
    else:
        day_all_slots = []
        day_available_slots = ConsultationSlot.objects.none()

    # پیش‌پر کردن توضیحات بر اساس منبع درخواست (رشته‌ها، صفحه دانشگاه‌ها و ...)
    initial_description = ""
    if request.method == "GET":
        about = request.GET.get("about")
        title_param = request.GET.get("title", "")
        if about == "majors":
            initial_description = "اینجانب در مورد رشته‌های تحصیلی سوال دارم؛ ممنون می‌شوم در این زمینه راهنمایی‌ام کنید."
        elif about == "major" and title_param:
            initial_description = f"اینجانب در مورد رشته «{title_param}» سوال دارم؛ ممنون می‌شوم در این زمینه راهنمایی‌ام کنید."
        elif about == "universities":
            initial_description = "اینجانب در مورد دانشگاه‌ها و موسسات تحصیلی سوال دارم؛ ممنون می‌شوم در این زمینه راهنمایی‌ام کنید."
        elif about == "university" and title_param:
            initial_description = f"اینجانب در مورد دانشگاه «{title_param}» سوال دارم؛ ممنون می‌شوم در این زمینه راهنمایی‌ام کنید."
        elif about == "courses":
            initial_description = "اینجانب در مورد دوره‌ها و برنامه‌های تحصیلی سوال دارم؛ ممنون می‌شوم در این زمینه راهنمایی‌ام کنید."
        elif about == "course" and title_param:
            initial_description = f"اینجانب در مورد دوره «{title_param}» سوال دارم؛ ممنون می‌شوم در این زمینه راهنمایی‌ام کنید."

    if request.method == "POST":
        form = ConsultationRequestForm(request.POST, slot_queryset=day_available_slots)
        if form.is_valid():
            form.save()
            return redirect(f"{reverse('appointment')}?success=1")
    else:
        form = ConsultationRequestForm(
            slot_queryset=day_available_slots,
            initial={"description": initial_description} if initial_description else {},
        )

    # اسلات انتخاب‌شده فعلی برای هایلایت در HTML
    selected_slot_id = None
    if request.method == "POST":
        selected_slot_id = request.POST.get("slot") or None
    else:
        first_slot = day_available_slots.first()
        if first_slot:
            selected_slot_id = str(first_slot.pk)

    country_flags = {"china": "🇨🇳", "canada": "🇨🇦", "spain": "🇪🇸", "other": "🌍"}
    country_options = [
        (v, label, country_flags.get(v, "🌍"))
        for v, label in ConsultationRequest.COUNTRY_CHOICES
    ]
    # کانتکست روزها همراه با برچسب شمسی/میلادی
    available_days_ctx = [
        {
            "date": d,
            "value": d.isoformat(),
            "label_g": d.strftime("%Y-%m-%d"),
            "label_j": format_jalali_date(d),
        }
        for d in available_days
    ]
    selected_date_jalali = format_jalali_date(selected_date) if selected_date else ""
    success = request.GET.get("success") == "1"
    return render(
        request,
        "core/appointment.html",
        {
            "form": form,
            "success": success,
            "selected_date": selected_date,
            "selected_date_jalali": selected_date_jalali,
            "available_days": available_days_ctx,
            "day_slots": day_all_slots,
            "selected_slot_id": selected_slot_id,
            "country_options": country_options,
        },
    )


def appointment_slots(request):
    """برگشت HTML اسلات‌های یک روز خاص برای استفاده در AJAX."""
    day_param = request.GET.get("day")
    if not day_param:
        return JsonResponse({"ok": False, "error": "day param required"}, status=400)

    try:
        from datetime import date as _date

        selected_date = _date.fromisoformat(day_param)
    except ValueError:
        return JsonResponse({"ok": False, "error": "invalid day"}, status=400)

    today = timezone.localdate()
    now = timezone.now()
    if selected_date < today:
        return JsonResponse({"ok": False, "error": "past day"}, status=400)

    base_qs = ConsultationSlot.objects.filter(date__gte=today).order_by("date", "order")
    available_qs = base_qs.filter(is_booked=False)

    day_all_raw = list(base_qs.filter(date=selected_date))
    day_all_slots = [s for s in day_all_raw if not slot_has_started(s, now)]

    day_available_raw = list(available_qs.filter(date=selected_date))
    day_available_filtered = [s for s in day_available_raw if not slot_has_started(s, now)]

    selected_slot_id = None
    if day_available_filtered:
        selected_slot_id = str(day_available_filtered[0].pk)

    html = render_to_string(
        "core/_appointment_slots.html",
        {
            "selected_date": selected_date,
            "selected_date_jalali": format_jalali_date(selected_date),
            "day_slots": day_all_slots,
            "selected_slot_id": selected_slot_id,
        },
        request=request,
    )

    return JsonResponse({"ok": True, "html": html})


def evaluation(request):
    """فرم ارزیابی اولیه شرایط متقاضی."""
    if request.method == "POST":
        form = EvaluationRequestForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect(f"{reverse('evaluation')}?success=1")
    else:
        form = EvaluationRequestForm()

    success = request.GET.get("success") == "1"
    return render(
        request,
        "core/evaluation.html",
        {
            "form": form,
            "success": success,
        },
    )


def faq(request):
    """سوالات متداول؛ جستجو به صورت لایو از طریق AJAX انجام می‌شود."""
    from .models import FAQ

    faqs = list(FAQ.objects.filter(is_active=True))
    return render(
        request,
        "core/faq.html",
        {"faqs": faqs},
    )


def faq_search(request):
    """جستجوی لایو FAQ؛ برگشت HTML برای جایگزینی در صفحه."""
    from .models import FAQ

    q = request.GET.get("q", "").strip()
    qs = FAQ.objects.filter(is_active=True)
    if q:
        qs = qs.filter(
            Q(question__icontains=q) | Q(answer__icontains=q)
        )
    faqs = list(qs)
    html = render_to_string(
        "core/_faq_content.html",
        {"faqs": faqs, "search_q": q},
        request=request,
    )
    return JsonResponse({"ok": True, "html": html})


@cache_page(60 * 5)
def schools_list(request):
    """لیست دانشگاه‌ها و موسسات مناسب پذیرش تحصیلی (الگو از صفحه schools Elmino)."""
    qs = University.objects.only(
        "slug",
        "image",
        "name_fa",
        "name_en",
        "city",
        "country",
        "world_rank",
        "short_description",
        "is_approved_by_mo_science",
        "is_approved_by_mo_health",
    )

    q = request.GET.get("q", "").strip()
    country = request.GET.get("country", "").strip()
    utype = request.GET.get("type", "").strip()

    if q:
        qs = qs.filter(
            Q(name_fa__icontains=q)
            | Q(name_en__icontains=q)
            | Q(city__icontains=q)
        )
    if country:
        qs = qs.filter(country=country)
    if utype:
        qs = qs.filter(type=utype)

    paginator = Paginator(qs, 12)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    countries = University.COUNTRY_CHOICES
    types = University.TYPE_CHOICES

    return render(
        request,
        "schools/list.html",
        {
            "page_obj": page_obj,
            "universities": page_obj.object_list,
            "filter_q": q,
            "filter_country": country,
            "filter_type": utype,
            "countries": countries,
            "types": types,
        },
    )


@cache_page(60 * 5)
def school_detail(request, slug):
    """صفحه جزئیات یک دانشگاه / موسسه."""
    university = get_object_or_404(
        University.objects.prefetch_related("gallery_images", "faqs"),
        slug=slug,
    )
    related = (
        University.objects.filter(country=university.country)
        .exclude(pk=university.pk)[:4]
    )
    return render(
        request,
        "schools/detail.html",
        {
            "university": university,
            "related_universities": related,
            "university_faqs": list(university.faqs.filter(is_active=True)),
        },
    )

