"""View functions for سفیران آینده روشن website."""
import json
import logging

from django.conf import settings
from django.db.models import Q, Sum, Case, When, FloatField, Prefetch
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.core.cache import cache
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_POST

from .forms import ContactForm, ConsultationRequestForm, EvaluationRequestForm, QuickConsultationForm
from .models import (
    BlogPost,
    ConsultationRequest,
    ConsultationSlot,
    Course,
    Institute,
    Major,
    Service,
    CountryScholarshipGuide,
    StudyCountry,
    TeamMember,
    University,
)
from .blog_search import related_blog_posts
from .cache_utils import (
    BLOG_TAGS_CACHE_KEY,
    api_cache_key,
    cached_page,
    get_api_cached,
    get_institute_cached,
    get_pricing_page_data_cached,
    get_public_stats_cached,
    get_service_categories_cached,
    has_active_courses_exists_cached,
    page_cache_seconds,
    set_api_cached,
    set_browse_api_cached,
)
from .utils import format_jalali_date, format_jalali_day_label, format_jalali_display, slot_has_started

from .study_destinations import country_flag_static, majors_country_nav_items, schools_country_nav_items

APPOINTMENT_COUNTRY_FLAGS = {
    code: country_flag_static(code)
    for code in (
        "china",
        "canada",
        "spain",
        "germany",
        "italy",
        "uk",
        "usa",
        "australia",
        "france",
        "netherlands",
        "other",
    )
}
for item in schools_country_nav_items():
    APPOINTMENT_COUNTRY_FLAGS.setdefault(item["code"], item["flag"])

SCHOOL_TYPE_ICONS = {
    "university": "ti-book",
    "college": "ti-briefcase",
    "school": "ti-pencil-alt",
    "institute": "ti-home",
}


def _schools_country_nav(countries):
    """آیتم‌های ناوبری کشور برای لیست دانشگاه‌ها."""
    return schools_country_nav_items()


def _schools_type_nav(types):
    """آیتم‌های ناوبری نوع موسسه برای لیست دانشگاه‌ها."""
    return [
        {
            "code": code,
            "label": label,
            "icon": SCHOOL_TYPE_ICONS.get(code, "ti-layout-grid2"),
        }
        for code, label in types
    ]

logger = logging.getLogger(__name__)


def redirect_evaluation_legacy(request):
    """ریدایرکت آدرس قدیمی /ارزیابی/ به فرم ارزیابی فعلی."""
    target = reverse("evaluation")
    qs = request.META.get("QUERY_STRING", "")
    if qs:
        target = f"{target}?{qs}"
    return redirect(target, permanent=True)


def page_not_found(request, exception=None):
    """صفحه ۴۰۴ برای آدرس‌های نامعتبر."""
    return render(request, "404.html", status=404)


def permission_denied(request, exception=None):
    """صفحه ۴۰۳؛ نمایش خطا بدون ریدایرکت."""
    return render(request, "403.html", status=403)


def csrf_failure(request, reason=""):
    """
    خطای CSRF (403).
    روی سرور معمولاً به دلیل cache شدن صفحه فرم، اختلاف scheme/domain، یا ارسال نشدن cookie رخ می‌دهد.
    """
    try:
        logger.warning(
            "CSRF failure: %s | path=%s host=%s referer=%s origin=%s secure=%s",
            reason,
            request.path,
            request.get_host(),
            request.META.get("HTTP_REFERER"),
            request.META.get("HTTP_ORIGIN"),
            request.is_secure(),
        )
    except Exception:
        pass

    return render(request, "csrf_failure.html", {"reason": reason}, status=403)


@cached_page
def index(request):
    """صفحه اصلی؛ آخرین ۳ پست وبلاگ و خدمات را نمایش می‌دهد."""
    posts_qs = (
        BlogPost.objects.filter(is_published=True)
        .only("id", "title", "slug", "excerpt", "image", "created_at", "author_id")
        .order_by("-created_at")[:3]
    )
    latest_posts = [
        {"post": p, "created_at_jalali": format_jalali_display(p.created_at)}
        for p in posts_qs
    ]
    services = (
        Service.objects.filter(is_active=True)
        .only("id", "title", "slug", "short_description", "icon", "order")
        .order_by("order", "id")[:6]
    )
    stats = get_public_stats_cached()
    institute = get_institute_cached()
    from .ai_discovery import resolve_site_url
    from .google_ai_seo import (
        build_index_answer_summary,
        build_index_page_schema_json,
        get_homepage_featured_faqs,
    )
    from .internal_linking import get_index_discovery_groups

    featured_faqs = get_homepage_featured_faqs()
    index_answer = build_index_answer_summary(institute)
    site_base = resolve_site_url(request)
    index_schema_json = build_index_page_schema_json(
        site_url=site_base,
        page_url=f"{site_base}/",
        institute_name=institute.name,
        answer_summary=index_answer,
        featured_faqs=featured_faqs,
    )

    return render(
        request,
        "core/index.html",
        {
            "latest_posts": latest_posts,
            "services": services,
            "discovery_groups": get_index_discovery_groups(),
            "university_count": stats["university_count"],
            "countries_count": getattr(institute, "countries_count", 0),
            "consultation_hours": stats["consultation_hours"],
            "students_sent": getattr(institute, "students_sent", 0),
            "featured_faqs": featured_faqs,
            "index_answer_summary": index_answer,
            "index_schema_json": index_schema_json,
        },
    )


@cached_page
def about(request):
    """صفحه درباره ما؛ داستان برند، خط زمانی، شمارشگر و تیم گروه‌بندی‌شده."""
    from core.about_content import BRAND_STORY, BRAND_TIMELINE, group_team_members
    from core.about_seo import build_about_page_seo

    institute = get_institute_cached()
    team_groups = group_team_members(
        TeamMember.objects.filter(is_active=True).only(
            "id",
            "name",
            "position",
            "image",
            "member_group",
            "order",
            "description",
            "title",
            "is_active",
        )
    )
    stats = get_public_stats_cached()
    site_url = getattr(settings, "SITE_URL", "").rstrip("/")
    if not site_url:
        site_url = f"{request.scheme}://{request.get_host()}"
    canonical = f"{site_url}{reverse('about')}"
    about_seo = build_about_page_seo(
        institute=institute,
        site_url=site_url,
        canonical_url=canonical,
    )
    return render(
        request,
        "core/about.html",
        {
            "brand_story": BRAND_STORY,
            "brand_timeline": BRAND_TIMELINE,
            "team_groups": team_groups,
            "university_count": stats["university_count"],
            "countries_count": getattr(institute, "countries_count", 0),
            "consultation_hours": stats["consultation_hours"],
            "students_sent": getattr(institute, "students_sent", 0),
            **about_seo,
        },
    )


@cached_page
def team_member_detail(request, pk):
    """صفحه تک‌عضو تیم."""
    member = get_object_or_404(
        TeamMember.objects.filter(is_active=True).only(
            "id",
            "name",
            "position",
            "title",
            "image",
            "description",
            "phone",
            "email",
            "telegram",
            "whatsapp",
            "instagram",
            "linkedin",
            "website",
            "member_group",
            "order",
            "is_active",
        ),
        pk=pk,
    )
    return render(request, "core/team_member_detail.html", {"member": member})


@cached_page
def achievement_detail(request, achievement_slug):
    """صفحه اختصاصی هر دستاورد (سئو)."""
    from .achievements_seo import build_achievement_detail_page_seo
    from .achievements_search import related_achievements
    from .models import MonthlyAchievement

    achievement = get_object_or_404(
        MonthlyAchievement.objects.filter(is_active=True),
        slug=achievement_slug,
    )

    institute = get_institute_cached()
    site_url = getattr(settings, "SITE_URL", "").rstrip("/")
    if not site_url:
        site_url = f"{request.scheme}://{request.get_host()}"

    seo = build_achievement_detail_page_seo(
        request=request,
        achievement=achievement,
        institute_name=getattr(institute, "name", "") or "موسسه",
        site_url=site_url,
    )

    return render(
        request,
        "core/achievement_detail.html",
        {
            "achievement": achievement,
            "related_achievements": related_achievements(achievement, limit=4),
            **seo,
        },
    )


def _achievement_api_json_response(data: dict, *, status: int = 200) -> JsonResponse:
    response = JsonResponse(data, status=status)
    response["X-Robots-Tag"] = "noindex, nofollow"
    return response


@never_cache
def achievement_search(request):
    """جستجوی هوشمند دستاوردها — بهترین تطابق + مرتبط‌ها."""
    from .achievements_search import filter_achievements, split_search_results

    q = request.GET.get("q", "").strip()
    month_label = request.GET.get("month", "").strip()

    cache_key = api_cache_key("achievement_search", month_label, q) if q else ""
    if cache_key:
        cached = get_api_cached(cache_key)
        if cached is not None:
            return _achievement_api_json_response(cached)

    best_slug = None
    suggestions = []
    if q:
        achievements, suggestions, best_slug = split_search_results(
            q,
            month_label=month_label,
            primary_limit=1,
            related_limit=5,
        )
    else:
        achievements = list(filter_achievements(month_label=month_label))

    html = render_to_string(
        "core/_achievements_grid.html",
        {
            "achievements": achievements,
            "suggestions": suggestions,
            "search_q": q,
            "best_achievement_slug": best_slug,
            "active_month": month_label,
        },
        request=request,
    )
    response_data = {
        "ok": True,
        "html": html,
        "count": len(achievements),
        "best_slug": best_slug,
        "related_count": len(suggestions),
    }
    if cache_key:
        set_api_cached(cache_key, response_data)
    return _achievement_api_json_response(response_data)


@never_cache
def achievement_suggest(request):
    """پیشنهاد دستاوردها برای autocomplete."""
    from .achievements_search import rank_achievements, suggest_achievements, tokenize_query

    q = request.GET.get("q", "").strip()
    month_label = request.GET.get("month", "").strip()

    cache_key = api_cache_key("achievement_suggest", month_label, q) if q else ""
    if cache_key:
        cached = get_api_cached(cache_key)
        if cached is not None:
            return _achievement_api_json_response(cached)

    items = suggest_achievements(q, month_label=month_label, limit=8)

    scored = {}
    if q and items:
        scored = {i.id: s for i, s in rank_achievements(items, q, limit=len(items))}

    payload = []
    for item in items:
        payload.append(
            {
                "id": item.id,
                "slug": item.slug,
                "title": item.title,
                "person_name": item.person_name,
                "person_role": item.person_role or "",
                "month_label": item.month_label or "",
                "smart_match": bool(scored.get(item.id, 0) >= 5) if scored else False,
            }
        )

    response_data = {"ok": True, "suggestions": payload, "smart": bool(q)}
    if cache_key:
        set_api_cached(cache_key, response_data)
    return _achievement_api_json_response(response_data)


@cached_page
def monthly_achievements(request):
    """صفحه دستاوردهای ماه — داستان موفقیت دانشجویان."""
    from .achievements_seo import build_achievements_page_seo
    from .models import MonthlyAchievement

    achievements = list(
        MonthlyAchievement.objects.filter(is_active=True).only(
            "id",
            "slug",
            "title",
            "person_name",
            "person_role",
            "month_label",
            "description",
            "image",
            "video_url",
            "video_file",
            "is_featured",
            "is_active",
            "order",
        )
    )
    month_labels = sorted(
        {a.month_label.strip() for a in achievements if (a.month_label or "").strip()},
        reverse=True,
    )
    featured_achievements = [a for a in achievements if a.is_featured][:5]
    achievements_with_video = sum(1 for a in achievements if a.has_video())

    institute = get_institute_cached()
    site_url = getattr(settings, "SITE_URL", "").rstrip("/")
    if not site_url:
        site_url = f"{request.scheme}://{request.get_host()}"

    seo = build_achievements_page_seo(
        request=request,
        institute_name=getattr(institute, "name", "") or "موسسه",
        site_url=site_url,
        achievements=achievements,
    )

    return render(
        request,
        "core/monthly_achievements.html",
        {
            "achievements": achievements,
            "month_labels": month_labels,
            "featured_achievements": featured_achievements,
            "achievements_total": len(achievements),
            "achievements_with_video": achievements_with_video,
            **seo,
        },
    )


def _blog_list_tags():
    tags = cache.get(BLOG_TAGS_CACHE_KEY)
    if tags is None:
        from .blog_search import unique_blog_tags

        tags = unique_blog_tags()
        cache.set(BLOG_TAGS_CACHE_KEY, tags, page_cache_seconds())
    return tags


def _blog_search_state(q: str, tag: str):
    """جستجوی هوشمند — فقط وقتی عبارت جستجو وجود دارد."""
    from .blog_search import fetch_and_rank_blog_posts, suggest_blog_query_correction

    q = (q or "").strip()
    if not q:
        return None, None, False

    ranked = fetch_and_rank_blog_posts(q=q, tag=tag)
    did_you_mean = None
    search_corrected = False

    if len(ranked) <= 2:
        correction = suggest_blog_query_correction(q, ranked=ranked)
        if correction and correction.strip().lower() != q.strip().lower():
            retry = fetch_and_rank_blog_posts(q=correction, tag=tag)
            if len(retry) > len(ranked):
                did_you_mean = correction
                if len(ranked) == 0:
                    ranked = retry
                    search_corrected = True

    return ranked, did_you_mean, search_corrected


@cached_page
def blog_list(request):
    """لیست پست‌های وبلاگ با جستجوی هوشمند، فیلتر برچسب و بارگذاری تدریجی."""
    from .blog_search import BLOG_PAGE_SIZE, BLOG_SEARCH_LIMIT, browse_blog_posts

    q = request.GET.get("q", "").strip()
    tag = request.GET.get("tag", "").strip()

    if q:
        ranked, did_you_mean, search_corrected = _blog_search_state(q, tag)
        posts = ranked[:BLOG_SEARCH_LIMIT]
        total_count = len(ranked)
        blog_has_more = False
    else:
        did_you_mean = None
        search_corrected = False
        posts, total_count, blog_has_more = browse_blog_posts(
            tag=tag, offset=0, limit=BLOG_PAGE_SIZE
        )

    return render(
        request,
        "blog/list.html",
        {
            "posts": posts,
            "filter_q": q,
            "filter_tag": tag,
            "tags": _blog_list_tags(),
            "total_count": total_count,
            "did_you_mean": did_you_mean,
            "search_corrected": search_corrected,
            "blog_has_more": blog_has_more,
            "blog_page_size": BLOG_PAGE_SIZE,
        },
    )


@never_cache
def blog_search(request):
    """جستجوی زنده وبلاگ (AJAX) + بارگذاری تدریجی."""
    from django.template.loader import render_to_string

    from .faq_search import _normalize_query
    from .blog_search import (
        BLOG_PAGE_SIZE,
        BLOG_PAGE_SIZE_MAX,
        BLOG_SEARCH_LIMIT,
        browse_blog_posts,
    )
    from .cache_utils import blog_api_cache_key

    q = request.GET.get("q", "").strip()
    tag = request.GET.get("tag", "").strip()
    partial = request.GET.get("partial", "").strip().lower() in ("1", "true", "yes")
    q_norm = _normalize_query(q) if q else ""

    if q and len(q) < 2:
        return _faq_api_json_response({"ok": True, "html": "", "total": 0, "too_short": True})

    try:
        offset = max(0, int(request.GET.get("offset", 0) or 0))
    except (TypeError, ValueError):
        offset = 0
    try:
        limit = int(request.GET.get("limit", BLOG_PAGE_SIZE) or BLOG_PAGE_SIZE)
    except (TypeError, ValueError):
        limit = BLOG_PAGE_SIZE
    limit = max(1, min(limit, BLOG_PAGE_SIZE_MAX))

    cache_key = ""
    if not partial:
        if q_norm:
            cache_key = blog_api_cache_key("blog_search", tag, q_norm)
        elif offset > 0:
            cache_key = blog_api_cache_key("blog_partial", tag, str(offset), str(limit))
        else:
            cache_key = blog_api_cache_key("blog_browse", tag, str(limit))
        cached = get_api_cached(cache_key)
        if cached is not None:
            return _faq_api_json_response(cached)

    if q:
        ranked, did_you_mean, search_corrected = _blog_search_state(q, tag)
        total_count = len(ranked)
        posts = ranked[:BLOG_SEARCH_LIMIT]
        blog_has_more = False
    elif partial and offset > 0:
        did_you_mean = None
        search_corrected = False
        posts, total_count, blog_has_more = browse_blog_posts(
            tag=tag, offset=offset, limit=limit
        )
        cards_html = render_to_string(
            "blog/_blog_cards.html",
            {"posts": posts},
            request=request,
        )
        partial_data = {
            "ok": True,
            "partial": True,
            "cards_html": cards_html,
            "count": len(posts),
            "total": total_count,
            "has_more": blog_has_more,
            "next_offset": offset + len(posts),
        }
        if cache_key:
            set_api_cached(cache_key, partial_data)
        return _faq_api_json_response(partial_data)
    else:
        posts, total_count, blog_has_more = browse_blog_posts(
            tag=tag, offset=0, limit=limit
        )

    html = render_to_string(
        "blog/_blog_results.html",
        {
            "posts": posts,
            "filter_q": q,
            "filter_tag": tag,
            "total_count": total_count,
            "did_you_mean": did_you_mean,
            "search_corrected": search_corrected,
            "blog_has_more": blog_has_more,
        },
        request=request,
    )

    response_data = {
        "ok": True,
        "html": html,
        "total": total_count,
        "did_you_mean": did_you_mean,
        "search_corrected": search_corrected,
        "best_slug": posts[0].slug if posts else "",
        "has_more": blog_has_more,
        "next_offset": len(posts),
    }
    if cache_key and (q_norm or not partial):
        set_api_cached(cache_key, response_data)
    return _faq_api_json_response(response_data)


@never_cache
def blog_suggest(request):
    """پیشنهاد زنده وبلاگ (autocomplete)."""
    from .faq_search import _normalize_query
    from .blog_search import suggest_blog_posts
    from .cache_utils import blog_api_cache_key

    q = request.GET.get("q", "").strip()
    tag = request.GET.get("tag", "").strip()
    q_norm = _normalize_query(q) if q else ""

    cache_key = ""
    if q_norm and len(q_norm) >= 2:
        cache_key = blog_api_cache_key("blog_suggest", tag, q_norm)
        cached = get_api_cached(cache_key)
        if cached is not None:
            return _faq_api_json_response(cached)

    suggestions = suggest_blog_posts(q, tag=tag, limit=8)
    response_data = {
        "ok": True,
        "suggestions": suggestions,
        "smart": bool(q_norm),
    }
    if cache_key:
        set_api_cached(cache_key, response_data)
    return _faq_api_json_response(response_data)


@cached_page
def blog_detail(request, slug):
    """صفحه جزئیات یک پست وبلاگ."""
    post = get_object_or_404(
        BlogPost.objects.select_related("author"),
        slug=slug,
        is_published=True,
    )

    from .blog_internal_links import get_enhanced_blog_resource_groups
    from .blog_seo import build_blog_post_seo

    institute = get_institute_cached()
    site_url = getattr(settings, "SITE_URL", "").rstrip("/")
    if not site_url:
        site_url = f"{request.scheme}://{request.get_host()}"
    canonical = f"{site_url}{reverse('blog_detail', kwargs={'slug': post.slug})}"
    org_schema_id = f"{site_url.rstrip('/')}/#organization"
    blog_seo = build_blog_post_seo(
        post=post,
        site_url=site_url,
        canonical_url=canonical,
        institute_name=getattr(institute, "name", "") or "موسسه",
        org_schema_id=org_schema_id,
        static_logo_path="/static/img/logo.png",
    )

    return render(
        request,
        "blog/single.html",
        {
            "post": post,
            "related_posts": related_blog_posts(post, limit=5),
            "blog_resource_groups": get_enhanced_blog_resource_groups(post),
            **blog_seo,
        },
    )


@never_cache
def contact(request):
    """صفحه تماس با ما؛ فرم POST را ذخیره می‌کند."""
    from .forms import CAPTCHA_SESSION_KEYS, init_form_with_captcha

    form, captcha_question = init_form_with_captcha(
        request, ContactForm, CAPTCHA_SESSION_KEYS["contact"]
    )
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect(f"{reverse('contact')}?success=1")

    success = request.GET.get("success") == "1"
    return render(
        request,
        "core/contact.html",
        {"form": form, "success": success, "captcha_question": captcha_question},
    )


def universities(request):
    """برای سازگاری قبلی؛ به صفحه لیست دانشگاه‌ها ریدایرکت می‌کند."""
    return redirect("schools_list")


def _majors_page_context(request):
    from .major_search import (
        FEATURED_MAJORS_SIDEBAR_LIMIT,
        MAJORS_PAGE_SIZE,
        get_featured_majors,
        list_majors_browse,
    )
    from .nav_degrees import parse_nav_degree_params

    country = request.GET.get("country", "").strip()
    university_slug = request.GET.get("university", "").strip()
    filter_university = None
    if university_slug:
        filter_university = (
            University.objects.filter(slug=university_slug)
            .only("slug", "name_fa", "name_en", "country")
            .first()
        )
        if filter_university and not country:
            country = filter_university.country
    majors_list, majors_total, majors_has_more = list_majors_browse(
        country_code=country,
        university_slug=university_slug if filter_university else "",
        offset=0,
        limit=MAJORS_PAGE_SIZE,
    )
    primary_country_nav, world_country_nav = majors_country_nav_items()
    active_world_country = None
    if country == "other":
        active_world_country = {"code": "other", "label": "سایر کشورها", "flag": ""}
    elif country:
        active_world_country = next(
            (i for i in world_country_nav if i["code"] == country), None
        )
    return {
        "majors_list": majors_list,
        "majors_total": majors_total,
        "majors_has_more": majors_has_more,
        "majors_page_size": MAJORS_PAGE_SIZE,
        "featured_majors": get_featured_majors(
            country_code=country, limit=FEATURED_MAJORS_SIDEBAR_LIMIT
        ),
        "primary_country_nav": primary_country_nav,
        "world_country_nav": world_country_nav,
        "active_world_country": active_world_country,
        "filter_country": country,
        "filter_university": filter_university,
        "filter_university_slug": university_slug if filter_university else "",
        "search_q": "",
        "suggestions": None,
        "best_major_slug": None,
        **parse_nav_degree_params(request.GET),
    }


@cached_page
def majors(request):
    """صفحه رشته‌های تحصیلی؛ جستجو و فیلتر کشور."""
    return render(request, "content/majors.html", _majors_page_context(request))


@never_cache
def majors_search(request):
    """جستجوی هوشمند رشته‌ها (AJAX) + بارگذاری تدریجی."""
    from .major_search import (
        MAJORS_PAGE_SIZE,
        MAJORS_PAGE_SIZE_MAX,
        _normalize_query,
        filter_majors,
        list_majors_browse,
        split_search_results,
    )

    q = request.GET.get("q", "").strip()
    country = request.GET.get("country", "").strip()
    university_slug = request.GET.get("university", "").strip()
    intent = request.GET.get("intent", "").strip()
    target_degree = request.GET.get("target_degree", "").strip()
    partial = request.GET.get("partial", "").strip().lower() in ("1", "true", "yes")
    q_norm = _normalize_query(q)
    try:
        offset = max(0, int(request.GET.get("offset", 0) or 0))
    except (TypeError, ValueError):
        offset = 0
    try:
        limit = int(request.GET.get("limit", MAJORS_PAGE_SIZE) or MAJORS_PAGE_SIZE)
    except (TypeError, ValueError):
        limit = MAJORS_PAGE_SIZE
    limit = max(1, min(limit, MAJORS_PAGE_SIZE_MAX))

    cache_key = ""
    if not partial:
        if q_norm:
            cache_key = api_cache_key(
                "majors_search", country, university_slug, intent, target_degree, q_norm
            )
        elif offset > 0:
            cache_key = api_cache_key(
                "majors_partial",
                country,
                university_slug,
                intent,
                target_degree,
                str(offset),
                str(limit),
            )
        else:
            cache_key = api_cache_key(
                "majors_browse", country, university_slug, intent, target_degree, str(limit)
            )
        cached = get_api_cached(cache_key)
        if cached is not None:
            return _faq_api_json_response(cached)

    if q:
        majors_list, suggestions, best_slug = split_search_results(
            q,
            country_code=country,
            university_slug=university_slug,
            primary_limit=1,
            related_limit=8,
            intent=intent,
            target_degree=target_degree,
        )
        majors_total = len(majors_list) + len(suggestions)
        majors_has_more = False
    elif partial and offset > 0:
        majors_list, majors_total, majors_has_more = list_majors_browse(
            country_code=country,
            university_slug=university_slug,
            offset=offset,
            limit=limit,
        )
        suggestions = []
        best_slug = None
        cards_html = render_to_string(
            "content/_majors_cards.html",
            {"majors_list": majors_list},
            request=request,
        )
        partial_data = {
            "ok": True,
            "partial": True,
            "cards_html": cards_html,
            "count": len(majors_list),
            "total": majors_total,
            "has_more": majors_has_more,
            "next_offset": offset + len(majors_list),
        }
        if cache_key:
            set_browse_api_cached(cache_key, partial_data)
        return _faq_api_json_response(partial_data)
    elif not q:
        majors_list, majors_total, majors_has_more = list_majors_browse(
            country_code=country,
            university_slug=university_slug,
            offset=0,
            limit=limit,
        )
        suggestions = []
        best_slug = None
    else:
        majors_list = list(filter_majors(country_code=country, university_slug=university_slug))
        suggestions = []
        best_slug = None
        majors_total = len(majors_list)
        majors_has_more = False

    html = render_to_string(
        "content/_majors_content.html",
        {
            "majors_list": majors_list,
            "search_q": q,
            "suggestions": suggestions,
            "best_major_slug": best_slug,
            "filter_country": country,
            "filter_university_slug": university_slug,
            "majors_total": majors_total,
            "majors_has_more": majors_has_more,
            "majors_page_size": limit,
        },
        request=request,
    )
    response_data = {
        "ok": True,
        "html": html,
        "count": len(majors_list) + (len(suggestions) if suggestions else 0),
        "primary_count": len(majors_list),
        "best_slug": best_slug,
        "related_count": len(suggestions) if suggestions else 0,
        "total": majors_total,
        "has_more": majors_has_more,
        "next_offset": len(majors_list),
    }
    if cache_key and (q_norm or not partial):
        if q_norm:
            set_api_cached(cache_key, response_data)
        else:
            set_browse_api_cached(cache_key, response_data)
    return _faq_api_json_response(response_data)


@never_cache
def majors_suggest(request):
    """پیشنهاد رشته برای autocomplete — سریع با فیلتر DB و کش کوتاه."""
    from .faq_search import tokenize_query
    from .major_search import _normalize_query, suggest_majors_ranked

    q = request.GET.get("q", "").strip()
    country = request.GET.get("country", "").strip()
    intent = request.GET.get("intent", "").strip()
    target_degree = request.GET.get("target_degree", "").strip()
    q_norm = _normalize_query(q)

    cache_key = ""
    if q_norm and len(q_norm) >= 2:
        cache_key = api_cache_key(
            "majors_suggest", country, intent, target_degree, q_norm
        )
        cached = get_api_cached(cache_key)
        if cached is not None:
            return _faq_api_json_response(cached)

    ranked = suggest_majors_ranked(
        q,
        country_code=country,
        limit=8,
        intent=intent,
        target_degree=target_degree,
    )
    tokens = tokenize_query(q_norm)

    payload = []
    for m, score in ranked:
        payload.append(
            {
                "id": m.id,
                "slug": m.slug,
                "title": m.title,
                "country": m.get_country_display() if m.country else "",
                "country_code": m.country or "",
                "smart_match": score >= 5.0,
            }
        )

    response_data = {"ok": True, "suggestions": payload, "smart": bool(q_norm and tokens)}
    if cache_key:
        set_api_cached(cache_key, response_data)
    return _faq_api_json_response(response_data)


def _services_page_context(request, category_slug=None):
    from .models import ServiceCategory
    from .service_search import filter_services, get_featured_services
    from .service_seo import build_services_page_seo

    categories = get_service_categories_cached()
    active_category = None
    if category_slug:
        active_category = get_object_or_404(
            ServiceCategory, slug=category_slug, is_active=True
        )

    services_list = list(filter_services(category_slug=category_slug or ""))
    featured_services = get_featured_services(category_slug=category_slug or "", limit=8)

    institute = get_institute_cached()
    site_url = getattr(settings, "SITE_URL", "").rstrip("/")
    if not site_url:
        site_url = f"{request.scheme}://{request.get_host()}"

    seo = build_services_page_seo(
        request=request,
        institute_name=getattr(institute, "name", "") or "موسسه",
        active_category=active_category,
        categories=categories,
        services=services_list,
        site_url=site_url,
    )

    from .internal_linking import get_services_discovery_groups
    from .service_needs import SERVICE_NEEDS

    return {
        "services_list": services_list,
        "categories": categories,
        "active_category": active_category,
        "featured_services": featured_services,
        "service_needs": SERVICE_NEEDS,
        "discovery_groups": get_services_discovery_groups(),
        **seo,
    }


@cached_page
def services(request):
    """صفحه خدمات با ما؛ دسته‌بندی، جستجو و پیشنهاد هوشمند."""
    ctx = _services_page_context(request)
    return render(request, "core/services.html", ctx)


@cached_page
def services_category(request, category_slug):
    """صفحه دسته‌بندی خدمات (سئو‌فرندلی)."""
    ctx = _services_page_context(request, category_slug=category_slug)
    return render(request, "core/services.html", ctx)


@never_cache
def services_search(request):
    """جستجو و فیلتر هوشمند خدمات (نیاز + دسته + عبارت)."""
    from .service_needs import NEEDS_BY_ID, parse_need_ids, smart_filter_services
    from .service_search import filter_services

    q = request.GET.get("q", "").strip()
    category_slug = request.GET.get("category", "").strip()
    need_ids = parse_need_ids(request.GET.get("needs", ""))
    needs_key = ",".join(sorted(need_ids))

    cache_key = ""
    if q or need_ids:
        cache_key = api_cache_key("services_search", category_slug, needs_key, q)
        cached = get_api_cached(cache_key)
        if cached is not None:
            return _faq_api_json_response(cached)

    if q or need_ids:
        primary, related, best_slug, meta = smart_filter_services(
            q=q,
            need_ids=need_ids,
            category_slug=category_slug,
        )
        services_list = primary
        suggestions = related
    else:
        services_list = list(filter_services(category_slug=category_slug))
        suggestions = []
        best_slug = None
        meta = {"mode": "all", "matched_count": len(services_list), "message": ""}

    need_labels = {n.id: n.label for n in NEEDS_BY_ID.values()}
    need_matches = meta.get("need_matches") or {}

    def _annotate_needs(service_list):
        for svc in service_list:
            if need_matches:
                nids = need_matches.get(svc.id, [])
            elif need_ids:
                nids = need_ids
            else:
                nids = []
            svc.matched_need_labels = [need_labels[nid] for nid in nids if nid in need_labels]

    _annotate_needs(services_list)
    _annotate_needs(suggestions)

    html = render_to_string(
        "core/_services_content.html",
        {
            "services_list": services_list,
            "search_q": q,
            "suggestions": suggestions,
            "best_service_slug": best_slug,
            "active_category_slug": category_slug,
            "selected_need_ids": need_ids,
            "filter_message": meta.get("message", ""),
            "filter_mode": meta.get("mode", "all"),
            "need_labels": need_labels,
            "need_matches": need_matches,
        },
        request=request,
    )
    response_data = {
        "ok": True,
        "html": html,
        "count": len(services_list) + len(suggestions),
        "primary_count": len(services_list),
        "best_slug": best_slug,
        "related_count": len(suggestions),
        "message": meta.get("message", ""),
        "mode": meta.get("mode", "all"),
    }
    if cache_key:
        set_api_cached(cache_key, response_data)
    return _faq_api_json_response(response_data)


@never_cache
def services_suggest(request):
    """پیشنهاد خدمات برای autocomplete."""
    from .service_needs import parse_need_ids, smart_filter_services
    from .service_search import rank_services, suggest_services

    q = request.GET.get("q", "").strip()
    category_slug = request.GET.get("category", "").strip()
    need_ids = parse_need_ids(request.GET.get("needs", ""))
    needs_key = ",".join(sorted(need_ids))

    cache_key = api_cache_key("services_suggest", category_slug, needs_key, q)
    cached = get_api_cached(cache_key)
    if cached is not None:
        return _faq_api_json_response(cached)

    if need_ids:
        primary, related, _, _ = smart_filter_services(
            q=q,
            need_ids=need_ids,
            category_slug=category_slug,
            limit=8,
        )
        items = (primary + related)[:8]
    else:
        items = suggest_services(q, category_slug=category_slug, limit=8)

    q_norm = request.GET.get("q", "").strip()
    if q_norm and items:
        scored = {s.id: sc for s, sc in rank_services(items, q_norm, limit=len(items))}
    else:
        scored = {}

    payload = []
    for s in items:
        payload.append(
            {
                "id": s.id,
                "slug": s.slug,
                "title": s.title,
                "category": s.category.name if s.category else "",
                "category_slug": s.category.slug if s.category else "",
                "smart_match": bool(scored.get(s.id, 0) >= 5) if scored else False,
            }
        )

    response_data = {"ok": True, "suggestions": payload, "smart": bool(q_norm)}
    set_api_cached(cache_key, response_data)
    return _faq_api_json_response(response_data)


def services_track_view(request):
    """ثبت بازدید خدمت برای رتبه‌بندی پیشنهادها."""
    from django.db.models import F

    if request.method != "POST":
        return _faq_api_json_response({"ok": False}, status=405)

    service_id = request.POST.get("service_id")
    try:
        service_id = int(service_id)
    except (TypeError, ValueError):
        return _faq_api_json_response({"ok": False}, status=400)

    updated = Service.objects.filter(pk=service_id, is_active=True).update(
        view_count=F("view_count") + 1
    )
    return _faq_api_json_response({"ok": bool(updated)})


@cached_page
def country_detail(request, country_code):
    """صفحه اختصاصی کشور مقصد برای سئو و هدایت کاربر به مسیرهای مرتبط."""
    from .country_search import _country_blog_q
    from .country_seo import build_country_page_seo

    country_code = (country_code or "").strip().lower()
    country = StudyCountry.objects.filter(code=country_code, is_active=True).first()
    if not country:
        from .study_destinations import ALL_DESTINATION_LABELS

        if country_code in ALL_DESTINATION_LABELS and country_code not in ("other", "not_sure"):
            from .seed_data.world_country_catalog import build_world_study_country_catalog

            catalog = {item["code"]: item for item in build_world_study_country_catalog()}
            item = catalog.get(country_code)
            if item:
                defaults = {k: v for k, v in item.items() if k != "code"}
                country, _ = StudyCountry.objects.update_or_create(
                    code=country_code,
                    defaults=defaults,
                )
    if not country:
        return render(request, "404.html", status=404)

    uni_fields = (
        "slug",
        "name_fa",
        "name_en",
        "city",
        "country",
        "type",
        "world_rank",
        "short_description",
        "image",
    )
    from django.db.models import IntegerField
    from django.db.models.functions import Cast

    uni_qs = University.objects.filter(country=country_code).only(*uni_fields)
    universities = list(
        uni_qs.exclude(world_rank="")
        .annotate(rank_num=Cast("world_rank", IntegerField()))
        .order_by("rank_num", "name_fa")[:6]
    )
    if len(universities) < 6:
        seen = {u.slug for u in universities}
        for uni in uni_qs.order_by("name_fa")[:12]:
            if uni.slug not in seen:
                universities.append(uni)
                seen.add(uni.slug)
            if len(universities) >= 6:
                break
    majors = list(
        Major.objects.filter(is_active=True, country=country_code)
        .only("id", "title", "slug", "short_description", "country", "order", "image")
        .order_by("order", "id")[:12]
    )
    courses = list(
        Course.objects.filter(is_active=True, country=country_code)
        .only("id", "title", "slug", "short_description", "country", "order", "image")
        .order_by("order", "id")[:8]
    )

    blog_q = _country_blog_q(country)
    blog_posts = (
        list(
            BlogPost.objects.filter(is_published=True)
            .filter(blog_q)
            .only("id", "title", "slug", "excerpt", "image", "created_at")
            .order_by("-created_at")[:6]
        )
        if blog_q
        else []
    )

    from .site_navigation import get_nav_countries_cached

    study_countries = get_nav_countries_cached()

    institute = get_institute_cached()
    site_url = getattr(settings, "SITE_URL", "").rstrip("/")
    if not site_url:
        site_url = f"{request.scheme}://{request.get_host()}"

    seo = build_country_page_seo(
        request=request,
        country=country,
        institute_name=getattr(institute, "name", "") or "موسسه",
        site_url=site_url,
    )

    from .country_immigration_pathway import build_country_immigration_pathway
    from .country_scholarship_seo import get_country_scholarship_guide
    from .nav_degrees import parse_nav_degree_params

    nav_ctx = parse_nav_degree_params(request.GET)
    scholarship_guide = None
    scholarship_preview = []
    degree_for_guide = nav_ctx.get("nav_target_degree") or ""
    scholarship_guide = get_country_scholarship_guide(country_code, degree_for_guide)
    if not scholarship_guide and degree_for_guide:
        scholarship_guide = get_country_scholarship_guide(country_code, "")
    if not scholarship_guide:
        scholarship_guide = (
            CountryScholarshipGuide.objects.filter(country=country, is_active=True)
            .order_by("target_degree")
            .first()
        )
    if scholarship_guide:
        scholarship_preview = list(
            scholarship_guide.scholarships.filter(is_active=True).order_by(
                "-is_featured", "order", "id"
            )[:3]
        )

    return render(
        request,
        "content/country_detail.html",
        {
            "country_code": country_code,
            "country": country,
            "study_countries": study_countries,
            "universities": universities,
            "majors": majors,
            "courses": courses,
            "blog_posts": blog_posts,
            "scholarship_guide": scholarship_guide,
            "scholarship_preview": scholarship_preview,
            "immigration_pathway": build_country_immigration_pathway(country),
            **seo,
            **nav_ctx,
        },
    )


@cached_page
def country_scholarships(request, country_code):
    """صفحه اختصاصی بورسیه هر کشور — محتوای سئو‌شده از دیتابیس."""
    from .country_scholarship_seo import build_country_scholarship_seo, get_country_scholarship_guide
    from .nav_degrees import parse_nav_degree_params

    country_code = (country_code or "").strip().lower()
    country = StudyCountry.objects.filter(code=country_code, is_active=True).first()
    if not country:
        return render(request, "404.html", status=404)

    nav_ctx = parse_nav_degree_params(request.GET)
    target_degree = nav_ctx.get("nav_target_degree") or ""
    guide = get_country_scholarship_guide(country_code, target_degree)
    if not guide:
        fallback = reverse("country_detail", kwargs={"country_code": country_code})
        if target_degree or nav_ctx.get("nav_intent"):
            from .nav_degrees import append_query_params

            q = {}
            if target_degree:
                q["target_degree"] = target_degree
            if nav_ctx.get("nav_intent"):
                q["intent"] = nav_ctx["nav_intent"]
            fallback = append_query_params(fallback, q)
        return redirect(f"{fallback}#guide-scholarship")

    scholarships = list(
        guide.scholarships.filter(is_active=True).order_by("-is_featured", "order", "id")
    )
    degree_guides = list(
        CountryScholarshipGuide.objects.filter(country=country, is_active=True).order_by(
            "target_degree"
        )
    )
    from .site_navigation import get_nav_countries_cached

    study_countries = get_nav_countries_cached()

    institute = get_institute_cached()
    site_url = getattr(settings, "SITE_URL", "").rstrip("/")
    if not site_url:
        site_url = f"{request.scheme}://{request.get_host()}"

    seo = build_country_scholarship_seo(
        request=request,
        country=country,
        guide=guide,
        scholarships=scholarships,
        institute_name=getattr(institute, "name", "") or "موسسه",
        site_url=site_url,
        target_degree=target_degree,
    )

    return render(
        request,
        "content/country_scholarships.html",
        {
            "country_code": country_code,
            "country": country,
            "guide": guide,
            "scholarships": scholarships,
            "degree_guides": degree_guides,
            "study_countries": study_countries,
            **seo,
            **nav_ctx,
        },
    )


def _country_api_json(data: dict, *, status: int = 200) -> JsonResponse:
    response = JsonResponse(data, status=status)
    response["X-Robots-Tag"] = "noindex, nofollow"
    return response


@never_cache
def country_search(request, country_code):
    """جستجوی محتوای مرتبط با یک کشور — فقط همان کشور."""
    from .country_search import split_country_search

    country_code = (country_code or "").strip().lower()
    if not StudyCountry.objects.filter(code=country_code, is_active=True).exists():
        return _country_api_json({"ok": False, "error": "country_not_found"}, status=404)

    q = request.GET.get("q", "").strip()

    cache_key = api_cache_key("country_search", country_code, q) if q else ""
    if cache_key:
        cached = get_api_cached(cache_key)
        if cached is not None:
            return _country_api_json(cached)

    primary, related = split_country_search(country_code, q)

    html = render_to_string(
        "content/_country_search_results.html",
        {
            "search_q": q,
            "primary_hits": primary,
            "related_hits": related,
            "country": StudyCountry.objects.get(code=country_code),
        },
        request=request,
    )
    response_data = {
        "ok": True,
        "html": html,
        "count": len(primary) + len(related),
    }
    if cache_key:
        set_api_cached(cache_key, response_data)
    return _country_api_json(response_data)


@never_cache
def country_suggest(request, country_code):
    """پیشنهاد جستجو در محتوای کشور."""
    from .country_search import suggest_country

    country_code = (country_code or "").strip().lower()
    if not StudyCountry.objects.filter(code=country_code, is_active=True).exists():
        return _country_api_json({"ok": False, "error": "country_not_found"}, status=404)

    q = request.GET.get("q", "").strip()
    # خزش گوگل بدون پارامتر q — پاسخ سبک؛ جستجو فقط با ورودی کاربر
    if not q:
        return _country_api_json({"ok": True, "suggestions": [], "smart": False})

    cache_key = api_cache_key("country_suggest", country_code, q)
    if cache_key:
        cached = get_api_cached(cache_key)
        if cached is not None:
            return _country_api_json(cached)

    try:
        items = suggest_country(country_code, q, limit=8)
    except Exception:
        return _country_api_json(
            {"ok": False, "error": "search_unavailable", "suggestions": []},
            status=503,
        )
    payload = [
        {
            "kind": hit.kind,
            "title": hit.title,
            "snippet": hit.snippet,
            "url": hit.url,
            "badge": hit.badge,
        }
        for hit in items
    ]
    response_data = {"ok": True, "suggestions": payload, "smart": True}
    set_api_cached(cache_key, response_data)
    return _country_api_json(response_data)


@never_cache
def courses_search(request):
    """جستجوی هوشمند دوره‌ها (AJAX) — اسلاگ‌های منطبق + پیشنهاد اصلاح."""
    from .course_search import _normalize_query, search_course_slugs

    q = request.GET.get("q", "").strip()
    country = request.GET.get("country", "").strip()
    q_norm = _normalize_query(q)

    cache_key = ""
    if q_norm:
        cache_key = api_cache_key("courses_search", country, q_norm)
        cached = get_api_cached(cache_key)
        if cached is not None:
            return _faq_api_json_response(cached)

    slugs, did_you_mean = search_course_slugs(q, country_code=country)
    response_data = {
        "ok": True,
        "slugs": slugs,
        "count": len(slugs),
        "smart": bool(q_norm),
        "did_you_mean": did_you_mean or "",
    }
    if cache_key:
        set_api_cached(cache_key, response_data)
    return _faq_api_json_response(response_data)


@never_cache
def courses_suggest(request):
    """پیشنهاد دوره برای autocomplete."""
    from .course_search import _normalize_query, suggest_courses_ranked
    from .faq_search import tokenize_query

    q = request.GET.get("q", "").strip()
    country = request.GET.get("country", "").strip()
    q_norm = _normalize_query(q)

    cache_key = ""
    if q_norm and len(q_norm) >= 2:
        cache_key = api_cache_key("courses_suggest", country, q_norm)
        cached = get_api_cached(cache_key)
        if cached is not None:
            return _faq_api_json_response(cached)

    ranked = suggest_courses_ranked(q, country_code=country, limit=8)
    tokens = tokenize_query(q_norm)
    payload = []
    for course, score in ranked:
        payload.append(
            {
                "id": course.id,
                "slug": course.slug,
                "title": course.title,
                "country": course.get_country_display() if course.country else "",
                "country_code": course.country or "",
                "smart_match": score >= 5.0,
            }
        )

    response_data = {
        "ok": True,
        "suggestions": payload,
        "smart": bool(q_norm and tokens),
    }
    if cache_key:
        set_api_cached(cache_key, response_data)
    return _faq_api_json_response(response_data)


@cached_page
def courses_list(request):
    """لیست دوره‌ها با فیلتر کشور."""
    from django.db.models import Count

    if not has_active_courses_exists_cached():
        return render(request, "content/courses_unavailable.html", status=404)

    country = request.GET.get("country", "").strip()
    valid_codes = {code for code, _ in Course.COUNTRY_CHOICES}
    if country and country not in valid_codes:
        country = ""

    base_qs = Course.objects.filter(is_active=True)
    qs = base_qs.only(
        "id",
        "title",
        "slug",
        "short_description",
        "description",
        "features",
        "country",
        "order",
        "image",
        "delivery_mode",
        "duration_hours",
        "price",
    )
    if country:
        qs = qs.filter(country=country)

    count_by_country = dict(
        base_qs.exclude(country="")
        .values("country")
        .annotate(c=Count("id"))
        .values_list("country", "c")
    )
    countries = Course.COUNTRY_CHOICES
    countries_nav = [
        (code, label, count_by_country.get(code, 0))
        for code, label in countries
    ]
    filter_country_label = ""
    if country:
        filter_country_label = dict(countries).get(country, "")

    return render(
        request,
        "content/courses_list.html",
        {
            "courses": qs.order_by("order", "id"),
            "countries": countries,
            "countries_nav": countries_nav,
            "filter_country": country,
            "filter_country_label": filter_country_label,
            "total_count": base_qs.count(),
            "featured_courses": base_qs.order_by("order", "id")[:5],
        },
    )


def elements(request):
    return render(request, "core/elements.html")


@cached_page
def course_details(request, slug):
    """صفحه جزئیات یک دوره."""
    from django.conf import settings
    from django.shortcuts import redirect

    from .course_seo import build_course_detail_seo

    course = get_object_or_404(
        Course.objects.select_related("instructor")
        .prefetch_related("syllabus_items", "faqs"),
        slug=slug,
        is_active=True,
    )
    if course.uses_external_link():
        return redirect(course.get_course_url())

    course_faqs = list(course.faqs.filter(is_active=True))
    institute = get_institute_cached()
    site_url = getattr(settings, "SITE_URL", "").rstrip("/")
    if not site_url:
        site_url = f"{request.scheme}://{request.get_host()}"
    seo = build_course_detail_seo(
        request=request,
        course=course,
        institute_name=getattr(institute, "name", "") or "موسسه",
        site_url=site_url,
    )
    return render(
        request,
        "content/course_details.html",
        {"course": course, "course_faqs": course_faqs, **seo},
    )


@cached_page
def course_instructor_detail(request, slug):
    """صفحه اختصاصی مدرس دوره — رزومه و دوره‌های ارائه‌شده."""
    from django.conf import settings

    from .course_seo import build_instructor_detail_seo
    from .models import CourseInstructor

    instructor = get_object_or_404(
        CourseInstructor.objects.prefetch_related("resume_entries"),
        slug=slug,
        is_active=True,
    )
    courses = list(
        instructor.courses.filter(is_active=True)
        .only(
            "title",
            "slug",
            "short_description",
            "image",
            "duration_hours",
            "delivery_mode",
            "price",
            "phone",
            "instructor_id",
        )
        .order_by("order", "id")
    )
    institute = get_institute_cached()
    site_url = getattr(settings, "SITE_URL", "").rstrip("/")
    if not site_url:
        site_url = f"{request.scheme}://{request.get_host()}"
    seo = build_instructor_detail_seo(
        request=request,
        instructor=instructor,
        institute_name=getattr(institute, "name", "") or "موسسه",
        site_url=site_url,
        courses=courses,
    )
    return render(
        request,
        "content/instructor_detail.html",
        {"instructor": instructor, "instructor_courses": courses, **seo},
    )


@cached_page
def major_details(request, slug):
    """صفحه جزئیات یک رشته."""
    from django.db.models import Prefetch

    from .models import MajorFAQ
    from .evaluation_links import build_evaluation_url
    from .university_majors import (
        build_appointment_url,
        build_schools_list_url_for_major,
        get_major_linked_universities_with_count,
        group_universities_preview_by_tier,
    )

    major = get_object_or_404(
        Major.objects.prefetch_related(
            Prefetch(
                "faqs",
                queryset=MajorFAQ.objects.filter(is_active=True).order_by("order", "id"),
            )
        ),
        slug=slug,
        is_active=True,
    )
    major_faqs = list(major.faqs.all())
    linked_universities, linked_universities_count = get_major_linked_universities_with_count(major)
    university_groups = group_universities_preview_by_tier(linked_universities)
    schools_list_url = build_schools_list_url_for_major(major)
    appointment_url = build_appointment_url(
        about="major",
        title=major.title,
        country=major.get_country_display() if major.country else "",
    )
    evaluation_url = build_evaluation_url(
        country=major.country or "",
        major=major.title,
        ref=f"major-{major.slug}",
    )
    from .internal_linking import get_priority_related_majors

    related_majors = get_priority_related_majors(
        country=major.country or "",
        exclude_slug=major.slug,
        limit=6,
    )
    institute = get_institute_cached()
    site_url = getattr(settings, "SITE_URL", "").rstrip("/")
    if not site_url:
        site_url = f"{request.scheme}://{request.get_host()}"
    canonical = f"{site_url}{reverse('major_details', kwargs={'slug': major.slug})}"
    from .major_seo import build_major_page_seo

    major_seo = build_major_page_seo(
        major=major,
        major_faqs=major_faqs,
        linked_universities=linked_universities,
        linked_universities_count=linked_universities_count,
        site_url=site_url,
        canonical_url=canonical,
        institute_name=getattr(institute, "name", "") or "موسسه",
    )
    return render(
        request,
        "content/major_details.html",
        {
            "major": major,
            "major_faqs": major_faqs,
            "related_majors": related_majors,
            "linked_universities": linked_universities,
            "linked_universities_count": linked_universities_count,
            "university_groups": university_groups,
            "schools_list_url": schools_list_url,
            "appointment_url": appointment_url,
            "evaluation_url": evaluation_url,
            **major_seo,
        },
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


@never_cache
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
        # اگر تاریخ از اسلات به‌دست نیامد، از فیلد روز فرم یا پارامتر GET استفاده می‌کنیم
        if not selected_date:
            day_param = request.POST.get("day") or request.GET.get("day")
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
            country_param = (request.GET.get("country") or "").strip()[:120]
            if country_param:
                initial_description = (
                    f"اینجانب در مورد رشته «{title_param}» در کشور {country_param} سوال دارم؛ "
                    f"ممنون می‌شوم در این زمینه راهنمایی‌ام کنید."
                )
            else:
                initial_description = (
                    f"اینجانب در مورد رشته «{title_param}» سوال دارم؛ "
                    f"ممنون می‌شوم در این زمینه راهنمایی‌ام کنید."
                )
        elif about == "universities":
            initial_description = "اینجانب در مورد دانشگاه‌ها و موسسات تحصیلی سوال دارم؛ ممنون می‌شوم در این زمینه راهنمایی‌ام کنید."
        elif about == "university" and title_param:
            country_param = (request.GET.get("country") or "").strip()[:120]
            if country_param:
                initial_description = (
                    f"اینجانب در مورد دانشگاه «{title_param}» در کشور {country_param} سوال دارم؛ "
                    f"ممنون می‌شوم در این زمینه راهنمایی‌ام کنید."
                )
            else:
                initial_description = (
                    f"اینجانب در مورد دانشگاه «{title_param}» سوال دارم؛ "
                    f"ممنون می‌شوم در این زمینه راهنمایی‌ام کنید."
                )
        elif about == "courses":
            initial_description = "اینجانب در مورد دوره‌ها و برنامه‌های تحصیلی سوال دارم؛ ممنون می‌شوم در این زمینه راهنمایی‌ام کنید."
        elif about == "course" and title_param:
            initial_description = f"اینجانب در مورد دوره «{title_param}» سوال دارم؛ ممنون می‌شوم در این زمینه راهنمایی‌ام کنید."
        elif about == "services":
            initial_description = (
                "اینجانب در مورد خدمات موسسه سوال دارم؛ "
                "ممنون می‌شوم در انتخاب خدمت مناسب راهنمایی‌ام کنید."
            )
        elif about == "service" and title_param:
            category_param = (request.GET.get("category") or "").strip()[:120]
            if category_param:
                initial_description = (
                    f"اینجانب درخواست مشاوره درباره خدمت «{title_param}» "
                    f"(دسته «{category_param}») دارم؛ "
                    f"ممنون می‌شوم در این زمینه راهنمایی‌ام کنید."
                )
            else:
                initial_description = (
                    f"اینجانب درخواست مشاوره درباره خدمت «{title_param}» دارم؛ "
                    f"ممنون می‌شوم در این زمینه راهنمایی‌ام کنید."
                )

    from .forms import CAPTCHA_SESSION_KEYS, init_form_with_captcha

    form_kwargs = {
        "slot_queryset": day_available_slots,
    }
    if request.method != "POST" and initial_description:
        form_kwargs["initial"] = {"description": initial_description}

    form, captcha_question = init_form_with_captcha(
        request,
        ConsultationRequestForm,
        CAPTCHA_SESSION_KEYS["appointment"],
        **form_kwargs,
    )
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect(f"{reverse('appointment')}?success=1")

    # اسلات انتخاب‌شده فعلی برای هایلایت در HTML
    selected_slot_id = None
    if request.method == "POST":
        selected_slot_id = request.POST.get("slot") or None
    else:
        selected_slot_id = None

    country_options = [
        (v, label, APPOINTMENT_COUNTRY_FLAGS.get(v, ""))
        for v, label in ConsultationRequest.COUNTRY_CHOICES
    ]
    available_days_ctx = [
        {
            "date": d,
            "value": d.isoformat(),
            "label_g": d.strftime("%Y-%m-%d"),
            "label_j": format_jalali_day_label(d),
        }
        for d in available_days
    ]
    selected_date_jalali = format_jalali_day_label(selected_date) if selected_date else ""
    has_available_slots = any(not s.is_booked for s in day_all_slots)
    first_available_slot_id = next(
        (s.pk for s in day_all_slots if not s.is_booked), None
    )
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
            "has_available_slots": has_available_slots,
            "first_available_slot_id": first_available_slot_id,
            "selected_slot_id": selected_slot_id,
            "country_options": country_options,
            "captcha_question": captcha_question,
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

    first_available_slot_id = (
        day_available_filtered[0].pk if day_available_filtered else None
    )
    html = render_to_string(
        "core/_appointment_slots.html",
        {
            "selected_date": selected_date,
            "selected_date_jalali": format_jalali_day_label(selected_date),
            "day_slots": day_all_slots,
            "has_available_slots": bool(day_available_filtered),
            "first_available_slot_id": first_available_slot_id,
            "selected_slot_id": None,
        },
        request=request,
    )

    return JsonResponse({"ok": True, "html": html})


def _scholarship_target_from_request(request) -> str:
    if request.POST.get("nav_intent", "").strip().lower() != "scholarship":
        return ""
    return (request.POST.get("nav_target_degree") or "").strip().lower()


def _save_evaluation_recommendation_snapshot(instance, *, scholarship_target: str = ""):
    """ذخیره خروجی پیشنهاد هوشمند برای نمایش در پنل کال‌سنتر."""
    try:
        from .evaluation_engine import build_evaluation_report

        report = build_evaluation_report(instance, scholarship_target=scholarship_target)
        instance.recommendation_snapshot = report
        instance.save(update_fields=["recommendation_snapshot", "updated_at"])
    except Exception:
        logger.exception("Failed to save evaluation recommendation snapshot pk=%s", instance.pk)


@never_cache
@require_GET
def captcha_refresh(request):
    """کپچای جدید برای فرم‌های عمومی (کلیک یا پس از خطای کد اشتباه)."""
    from .forms import CAPTCHA_SESSION_KEYS, generate_captcha

    form_key = (request.GET.get("form") or "").strip()
    session_key = CAPTCHA_SESSION_KEYS.get(form_key)
    if not session_key:
        return JsonResponse({"ok": False, "error": "invalid_form"}, status=400)
    question, answer = generate_captcha()
    request.session[session_key] = answer
    request.session.modified = True
    return JsonResponse({"ok": True, "question": question})


@never_cache
@require_POST
def evaluation_submit(request):
    """ثبت فرم ارزیابی و شروع job تحلیل (AJAX)."""
    from .evaluation_pipeline import (
        create_evaluation_job,
        eval_async_submit_ctx,
        queue_ahead_initial_for_job,
    )
    from .forms import CAPTCHA_SESSION_KEYS, init_form_with_captcha

    form, captcha_question = init_form_with_captcha(
        request, EvaluationRequestForm, CAPTCHA_SESSION_KEYS["evaluation"]
    )
    if not form.is_valid():
        return JsonResponse(
            {
                "ok": False,
                "errors": form.errors,
                "captcha_question": captcha_question,
            },
            status=400,
        )

    token = eval_async_submit_ctx.set(True)
    try:
        instance = form.save()
        scholarship_target = _scholarship_target_from_request(request)
        job_id = create_evaluation_job(instance, scholarship_target=scholarship_target)
    finally:
        eval_async_submit_ctx.reset(token)

    request.session["eval_active_job"] = job_id
    from .evaluation_pipeline import start_evaluation_job_async

    start_evaluation_job_async(job_id)
    return JsonResponse(
        {
            "ok": True,
            "job_id": job_id,
            "queue_ahead": queue_ahead_initial_for_job(job_id),
        }
    )


@never_cache
@require_GET
def evaluation_process(request):
    """Polling پیشرفت تحلیل ارزیابی."""
    from .evaluation_pipeline import read_evaluation_job, start_evaluation_job_async
    from .seo_robots import private_robots_header

    job_id = (request.GET.get("job") or "").strip() or request.session.get("eval_active_job")
    if not job_id:
        response = JsonResponse(
            {"ok": False, "error": "job_missing", "message": "شناسه تحلیل یافت نشد."},
            status=400,
        )
        response["X-Robots-Tag"] = private_robots_header()
        return response

    from .evaluation_pipeline import job_needs_processing

    result = read_evaluation_job(job_id)
    if job_needs_processing(job_id):
        start_evaluation_job_async(job_id)
        result = read_evaluation_job(job_id)
    if result.get("error") == "job_not_found":
        response = JsonResponse(result, status=404)
        response["X-Robots-Tag"] = private_robots_header()
        return response
    if result.get("status") == "running" and not result.get("job_id"):
        result["job_id"] = job_id
    status_code = 200 if result.get("ok") or result.get("status") == "running" else 500
    if result.get("status") == "error" and result.get("error") != "job_not_found":
        status_code = 500
    response = JsonResponse(result, status=status_code)
    response["X-Robots-Tag"] = private_robots_header()
    return response


@never_cache
def evaluation_majors_suggest(request):
    """پیشنهاد هوشمند رشته برای combobox فرم ارزیابی."""
    from .evaluation_majors import suggest_evaluation_majors_ranked
    from .faq_search import _normalize_query, tokenize_query

    q = request.GET.get("q", "").strip()
    countries_raw = request.GET.get("countries", "").strip()
    country_codes = [p.strip() for p in countries_raw.split(",") if p.strip()]
    q_norm = _normalize_query(q)

    cache_key = ""
    if q_norm and len(q_norm) >= 2:
        cache_key = api_cache_key("evaluation_majors_suggest", countries_raw, q_norm)
        cached = get_api_cached(cache_key)
        if cached is not None:
            return _faq_api_json_response(cached)

    ranked = suggest_evaluation_majors_ranked(q, country_codes=country_codes, limit=10)
    payload = []
    for opt, score in ranked:
        payload.append(
            {
                "title": opt["title"],
                "countries": list(opt.get("countries") or []),
                "country_labels": list(opt.get("country_labels") or []),
                "smart_match": score >= 5.0,
            }
        )

    response_data = {
        "ok": True,
        "suggestions": payload,
        "smart": bool(q_norm and tokenize_query(q_norm)),
    }
    if cache_key:
        set_api_cached(cache_key, response_data)
    return _faq_api_json_response(response_data)


@require_GET
@never_cache
def evaluation_country_suggest(request):
    """پیشنهاد کشور مقصد وقتی کاربر مطمئن نیست یا «سایر» انتخاب کرده."""
    from .evaluation_country_hints import (
        profile_ready_for_country_suggestions,
        suggest_destination_countries,
    )

    selection = request.GET.get("selection", "").strip().lower()
    if selection == "other":
        return JsonResponse(
            {"ok": True, "profile_ready": False, "suggestions": []}
        )

    field = request.GET.get("field", "").strip()
    degree = request.GET.get("degree", "").strip()
    gpa = request.GET.get("gpa", "").strip()
    profile_ready = profile_ready_for_country_suggestions(
        field_of_study=field,
        average_grade=gpa,
        current_degree=degree,
    )
    suggestions = (
        suggest_destination_countries(
            field_of_study=field,
            current_degree=degree,
            average_grade=gpa,
            language_test=request.GET.get("lang_test", "").strip(),
            language_score=request.GET.get("lang_score", "").strip(),
            budget_limited=request.GET.get("budget_limited", "").strip().lower()
            in ("1", "true", "yes"),
        )
        if profile_ready
        else []
    )
    return JsonResponse(
        {"ok": True, "profile_ready": profile_ready, "suggestions": suggestions}
    )


@never_cache
def evaluation(request):
    """فرم ارزیابی اولیه شرایط متقاضی."""
    from .evaluation_share import create_evaluation_share, get_valid_evaluation_share
    from .models import EvaluationReportShare

    from .forms import CAPTCHA_SESSION_KEYS, init_form_with_captcha

    form, captcha_question = init_form_with_captcha(
        request, EvaluationRequestForm, CAPTCHA_SESSION_KEYS["evaluation"]
    )
    if request.method == "POST" and form.is_valid():
        instance = form.save()
        _save_evaluation_recommendation_snapshot(
            instance,
            scholarship_target=_scholarship_target_from_request(request),
        )
        instance.refresh_from_db(fields=["recommendation_snapshot"])
        share = create_evaluation_share(
            instance,
            instance.recommendation_snapshot,
        )
        request.session["eval_share_token"] = str(share.token)
        return redirect("evaluation_result", token=share.token)

    # سازگاری با لینک قدیمی ?result=1
    if request.GET.get("result") == "1":
        token = request.session.pop("eval_share_token", None)
        if not token:
            pk = request.session.pop("eval_result_id", None)
            if pk:
                from .evaluation_engine import build_evaluation_report
                from .models import EvaluationRequest

                try:
                    ev = EvaluationRequest.objects.get(pk=pk)
                    share = create_evaluation_share(
                        ev, ev.recommendation_snapshot or build_evaluation_report(ev)
                    )
                    token = str(share.token)
                except EvaluationRequest.DoesNotExist:
                    pass
        if token:
            share = get_valid_evaluation_share(token)
            if share:
                return redirect("evaluation_result", token=share.token)

    from .evaluation_majors import get_evaluation_major_options, get_evaluation_major_suggestions

    major_suggestions = get_evaluation_major_suggestions()
    major_options = get_evaluation_major_options()
    from .evaluation_form_countries import (
        EVAL_FORM_COUNTRY_CARDS,
        EVAL_FORM_COUNTRY_EXTRAS,
        EVAL_FORM_REAL_COUNTRY_CODES,
        EVAL_FORM_TARGET_COUNTRY_CHOICES,
    )

    selected_countries = []
    if form.is_bound:
        selected_countries = form.data.getlist("desired_countries")
    elif form.instance and form.instance.pk and form.instance.desired_countries:
        selected_countries = [
            p.strip() for p in form.instance.desired_countries.split(",") if p.strip()
        ]

    from .nav_degrees import parse_nav_degree_params
    from .evaluation_links import parse_evaluation_prefill_params

    eval_start_step = 4 if request.method == "POST" and form.errors.get("captcha_answer") else None

    import json

    from .forms import INTAKE_EXTEND_STEP, INTAKE_TERMS, INTAKE_YEARS_AHEAD, current_jalali_year
    from .evaluation_engine import warm_evaluation_catalog
    from .evaluation_seo import build_evaluation_page_seo

    warm_evaluation_catalog()

    institute = get_institute_cached()
    site_url = getattr(settings, "SITE_URL", "").rstrip("/")
    if not site_url:
        site_url = f"{request.scheme}://{request.get_host()}"
    seo = build_evaluation_page_seo(
        institute_name=getattr(institute, "name", "") or "موسسه",
        site_url=site_url,
    )

    return render(
        request,
        "core/evaluation.html",
        {
            **seo,
            "form": form,
            "captcha_question": captcha_question,
            "eval_start_step": eval_start_step,
            "eval_jalali_year": current_jalali_year(),
            "eval_intake_terms_json": json.dumps(list(INTAKE_TERMS), ensure_ascii=False),
            "eval_intake_years_ahead": INTAKE_YEARS_AHEAD,
            "eval_intake_extend_step": INTAKE_EXTEND_STEP,
            "major_suggestions": major_suggestions,
            "eval_major_options_json": json.dumps(major_options, ensure_ascii=False),
            "eval_country_cards": EVAL_FORM_COUNTRY_CARDS,
            "eval_country_extras": EVAL_FORM_COUNTRY_EXTRAS,
            "eval_target_countries": EVAL_FORM_TARGET_COUNTRY_CHOICES,
            "eval_real_country_codes_json": json.dumps(
                EVAL_FORM_REAL_COUNTRY_CODES, ensure_ascii=False
            ),
            "selected_countries": selected_countries,
            **parse_nav_degree_params(request.GET),
            **parse_evaluation_prefill_params(request.GET),
        },
    )


@never_cache
def evaluation_result(request, token):
    """صفحه اشتراک‌گذاری نتیجه ارزیابی (۷ روز معتبر)."""
    from django.db.models import F

    from .evaluation_engine import get_evaluation_display_report
    from .evaluation_share import build_share_absolute_url, get_valid_evaluation_share

    institute = get_institute_cached()
    site_url = getattr(settings, "SITE_URL", "").rstrip("/")
    if not site_url:
        site_url = f"{request.scheme}://{request.get_host()}"

    share = get_valid_evaluation_share(token)
    if not share:
        from .evaluation_result_seo import (
            PRIVATE_ROBOTS_HEADER,
            build_evaluation_expired_page_seo,
        )

        response = render(
            request,
            "core/evaluation_result_expired.html",
            {
                "evaluation_url": reverse("evaluation"),
                **build_evaluation_expired_page_seo(
                    institute_name=getattr(institute, "name", "") or "موسسه",
                    site_url=site_url,
                ),
            },
            status=410,
        )
        response["X-Robots-Tag"] = PRIVATE_ROBOTS_HEADER
        return response

    from .models import EvaluationReportShare

    EvaluationReportShare.objects.filter(pk=share.pk).update(
        view_count=F("view_count") + 1
    )

    expires_jalali = None
    try:
        from .utils import format_datetime_both

        expires_jalali = format_datetime_both(share.expires_at)
    except Exception:
        expires_jalali = share.expires_at.strftime("%Y-%m-%d %H:%M")

    stored_report = share.report if isinstance(share.report, dict) else {}
    eval_req = share.evaluation
    report = get_evaluation_display_report(
        eval_req,
        stored_report,
        cache_token=str(share.token),
    )
    if not isinstance(report, dict):
        report = stored_report

    from .evaluation_result_seo import (
        PRIVATE_ROBOTS_HEADER,
        build_evaluation_result_page_seo,
    )
    from .evaluation_section_feedback import build_feedback_context

    response = render(
        request,
        "core/evaluation_result.html",
        {
            "report": report,
            "share": share,
            "share_url": build_share_absolute_url(request, share),
            "expires_display": expires_jalali,
            "pdf_url": reverse("evaluation_result_pdf", kwargs={"token": share.token}),
            "evaluation_url": reverse("evaluation"),
            "eval_section_feedback": build_feedback_context(share, request),
            **build_evaluation_result_page_seo(
                institute_name=getattr(institute, "name", "") or "موسسه",
                site_url=site_url,
            ),
        },
    )
    response["Cache-Control"] = "private, no-store, max-age=0"
    response["X-Robots-Tag"] = PRIVATE_ROBOTS_HEADER
    return response


@never_cache
def evaluation_result_feedback(request, token):
    """ثبت لایک/دیسلایک روی بخش‌های گزارش ارزیابی."""
    import json

    from .evaluation_section_feedback import save_section_feedback
    from .evaluation_share import get_valid_evaluation_share

    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "method_not_allowed"}, status=405)

    share = get_valid_evaluation_share(token)
    if not share:
        return JsonResponse({"ok": False, "error": "expired"}, status=410)

    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"ok": False, "error": "invalid_json"}, status=400)

    section = str(payload.get("section", "")).strip()
    item_key = str(payload.get("item_key", "")).strip()
    try:
        vote = int(payload.get("vote", 0))
    except (TypeError, ValueError):
        return JsonResponse({"ok": False, "error": "invalid_vote"}, status=400)

    try:
        row = save_section_feedback(share, section=section, vote=vote, item_key=item_key)
    except ValueError as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=400)

    return JsonResponse({"ok": True, "vote": row.vote, "section": row.section, "item_key": row.item_key})


@never_cache
def evaluation_result_pdf(request, token):
    """خروجی PDF نتیجه ارزیابی."""
    from django.template.loader import render_to_string
    from django.http import HttpResponse

    from .cache_utils import get_institute_cached
    from .evaluation_share import get_valid_evaluation_share

    share = get_valid_evaluation_share(token)
    if not share:
        return render(request, "core/evaluation_result_expired.html", status=410)

    institute = get_institute_cached()
    html = render_to_string(
        "core/evaluation_result_pdf.html",
        {
            "report": share.report,
            "share": share,
            "institute": institute,
        },
        request=request,
    )

    try:
        from io import BytesIO

        from xhtml2pdf import pisa

        result = BytesIO()
        pdf = pisa.CreatePDF(html, dest=result, encoding="UTF-8")
        if pdf.err:
            raise RuntimeError("PDF generation failed")
        response = HttpResponse(result.getvalue(), content_type="application/pdf")
        response["Content-Disposition"] = (
            f'attachment; filename="safiran-evaluation-{share.token}.pdf"'
        )
        from .evaluation_result_seo import PRIVATE_ROBOTS_HEADER

        response["X-Robots-Tag"] = PRIVATE_ROBOTS_HEADER
        return response
    except Exception:
        logger.exception("evaluation_result_pdf fallback to print for token=%s", token)
        return render(
            request,
            "core/evaluation_result_print.html",
            {
                "report": share.report,
                "share": share,
                "institute": institute,
                "auto_print": True,
            },
        )


def _faq_page_context(request, category_slug=None):
    from .cache_utils import get_institute_cached
    from .faq_search import filter_faqs, get_featured_faqs
    from .faq_seo import build_faq_page_seo
    from .models import FAQCategory

    categories = list(
        FAQCategory.objects.filter(is_active=True)
        .only(
            "id",
            "name",
            "slug",
            "description",
            "icon",
            "meta_title",
            "meta_description",
            "order",
            "is_active",
        )
        .order_by("order", "id")
    )
    active_category = None
    if category_slug:
        active_category = get_object_or_404(
            FAQCategory, slug=category_slug, is_active=True
        )

    faqs = list(filter_faqs(category_slug=category_slug or ""))
    featured_faqs = get_featured_faqs(category_slug=category_slug or "", limit=8)

    institute = get_institute_cached()
    site_url = getattr(settings, "SITE_URL", "").rstrip("/")
    if not site_url:
        site_url = f"{request.scheme}://{request.get_host()}"

    seo = build_faq_page_seo(
        request=request,
        institute_name=getattr(institute, "name", "") or "موسسه",
        active_category=active_category,
        categories=categories,
        faqs=faqs,
        site_url=site_url,
    )

    return {
        "faqs": faqs,
        "categories": categories,
        "active_category": active_category,
        "featured_faqs": featured_faqs,
        **seo,
    }


@cached_page
def faq(request):
    """سوالات متداول؛ دسته‌بندی، جستجو و پیشنهاد هوشمند."""
    ctx = _faq_page_context(request)
    return render(request, "core/faq.html", ctx)


@cached_page
def faq_category(request, category_slug):
    """صفحه دسته‌بندی سوالات متداول (سئو‌فرندلی)."""
    ctx = _faq_page_context(request, category_slug=category_slug)
    return render(request, "core/faq.html", ctx)


@cached_page
def faq_detail(request, faq_slug):
    """صفحه اختصاصی هر سوال متداول (سئو)."""
    from .faq_seo import build_faq_detail_page_seo
    from .models import FAQ

    faq = get_object_or_404(
        FAQ.objects.select_related("category"),
        slug=faq_slug,
        is_active=True,
    )

    institute = get_institute_cached()
    site_url = getattr(settings, "SITE_URL", "").rstrip("/")
    if not site_url:
        site_url = f"{request.scheme}://{request.get_host()}"

    related_faqs = list(
        FAQ.objects.filter(is_active=True, category_id=faq.category_id)
        .select_related("category")
        .only(
            "id",
            "slug",
            "question",
            "answer",
            "order",
            "view_count",
            "category_id",
            "category__name",
            "category__slug",
        )
        .exclude(pk=faq.pk)
        .order_by("order", "id")[:5]
    )
    if len(related_faqs) < 3:
        related_faqs = list(
            FAQ.objects.filter(is_active=True)
            .select_related("category")
            .only(
                "id",
                "slug",
                "question",
                "answer",
                "order",
                "view_count",
                "category_id",
                "category__name",
                "category__slug",
            )
            .exclude(pk=faq.pk)
            .order_by("-view_count", "order", "id")[:5]
        )

    seo = build_faq_detail_page_seo(
        request=request,
        faq=faq,
        institute_name=getattr(institute, "name", "") or "موسسه",
        site_url=site_url,
    )

    return render(
        request,
        "core/faq_detail.html",
        {
            "faq": faq,
            "related_faqs": related_faqs,
            **seo,
        },
    )


def _faq_api_json_response(data: dict, *, status: int = 200) -> JsonResponse:
    """پاسخ API داخلی FAQ — بدون ایندکس در موتور جستجو."""
    response = JsonResponse(data, status=status)
    response["X-Robots-Tag"] = "noindex, nofollow"
    return response


@never_cache
def faq_search(request):
    """جستجوی FAQ؛ بهترین نتیجه بالا + مرتبط‌ها پایین."""
    from .faq_search import _normalize_query, filter_faqs, split_search_results

    q = request.GET.get("q", "").strip()
    category_slug = request.GET.get("category", "").strip()
    q_norm = _normalize_query(q) if q else ""

    cache_key = ""
    if q_norm:
        cache_key = api_cache_key("faq_search", category_slug, q_norm)
        cached = get_api_cached(cache_key)
        if cached is not None:
            return _faq_api_json_response(cached)

    best_slug = None
    if q:
        faqs, suggestions, best_slug = split_search_results(
            q,
            category_slug=category_slug,
            primary_limit=1,
            related_limit=6,
        )
    else:
        faqs = list(filter_faqs(category_slug=category_slug))
        suggestions = []

    html = render_to_string(
        "core/_faq_content.html",
        {
            "faqs": faqs,
            "search_q": q,
            "suggestions": suggestions,
            "best_faq_slug": best_slug,
            "active_category_slug": category_slug,
        },
        request=request,
    )
    response_data = {
        "ok": True,
        "html": html,
        "count": len(faqs),
        "best_slug": best_slug,
        "related_count": len(suggestions),
    }
    if cache_key:
        set_api_cached(cache_key, response_data)
    return _faq_api_json_response(response_data)


@never_cache
def faq_suggest(request):
    """پیشنهاد سوالات برای autocomplete."""
    from .faq_search import _normalize_query, suggest_faqs

    q = request.GET.get("q", "").strip()
    category_slug = request.GET.get("category", "").strip()
    q_norm = _normalize_query(q) if q else ""

    cache_key = ""
    if q_norm and len(q_norm) >= 2:
        cache_key = api_cache_key("faq_suggest", category_slug, q_norm)
        cached = get_api_cached(cache_key)
        if cached is not None:
            return _faq_api_json_response(cached)

    items = suggest_faqs(q, category_slug=category_slug, limit=8)

    from .faq_search import rank_faqs, tokenize_query

    q_norm = request.GET.get("q", "").strip()
    tokens = tokenize_query(q_norm)

    payload = []
    if q_norm and items:
        scored = {f.id: s for f, s in rank_faqs(items, q_norm, limit=len(items))}
    else:
        scored = {}

    for f in items:
        payload.append(
            {
                "id": f.id,
                "slug": f.slug,
                "question": f.question,
                "category": f.category.name if f.category else "",
                "category_slug": f.category.slug if f.category else "",
                "smart_match": bool(scored.get(f.id, 0) >= 5) if scored else False,
            }
        )

    response_data = {"ok": True, "suggestions": payload, "smart": bool(q_norm)}
    if cache_key:
        set_api_cached(cache_key, response_data)
    return _faq_api_json_response(response_data)


def faq_track_view(request):
    """ثبت بازدید سوال برای رتبه‌بندی پیشنهادها."""
    from django.db.models import F

    from .models import FAQ

    if request.method != "POST":
        return _faq_api_json_response({"ok": False}, status=405)

    faq_id = request.POST.get("faq_id")
    try:
        faq_id = int(faq_id)
    except (TypeError, ValueError):
        return _faq_api_json_response({"ok": False}, status=400)

    updated = FAQ.objects.filter(pk=faq_id, is_active=True).update(
        view_count=F("view_count") + 1
    )
    return _faq_api_json_response({"ok": bool(updated)})


def achievement_track_view(request):
    """ثبت بازدید دستاورد — جدا از کش صفحه."""
    from django.db.models import F

    from .models import MonthlyAchievement

    if request.method != "POST":
        return _achievement_api_json_response({"ok": False}, status=405)

    achievement_id = request.POST.get("achievement_id")
    try:
        achievement_id = int(achievement_id)
    except (TypeError, ValueError):
        return _achievement_api_json_response({"ok": False}, status=400)

    updated = MonthlyAchievement.objects.filter(
        pk=achievement_id, is_active=True
    ).update(view_count=F("view_count") + 1)
    return _achievement_api_json_response({"ok": bool(updated)})


SCHOOLS_TIER_OTHER_LABEL = "سایر دانشگاه‌ها"


def _schools_list_query_string(*, q="", country="", utype="", tier="", page=None, nav_ctx=None):
    """ساخت query string فیلترهای لیست دانشگاه‌ها."""
    from urllib.parse import urlencode

    params = {}
    if q:
        params["q"] = q
    if country:
        params["country"] = country
    if utype:
        params["type"] = utype
    if tier:
        params["tier"] = tier
    if page and int(page) > 1:
        params["page"] = int(page)
    if nav_ctx:
        if nav_ctx.get("nav_target_degree"):
            params["target_degree"] = nav_ctx["nav_target_degree"]
        if nav_ctx.get("nav_intent"):
            params["intent"] = nav_ctx["nav_intent"]
    return urlencode(params)


def _schools_page_context(request):
    from .cache_utils import get_public_stats_cached
    from .nav_degrees import parse_nav_degree_params
    from .university_search import (
        FEATURED_UNIVERSITIES_LIMIT,
        SCHOOLS_PAGE_SIZE,
        SCHOOLS_TIER_OTHER,
        get_featured_universities,
        list_universities_browse,
        split_search_results,
    )

    country = request.GET.get("country", "").strip()
    utype = request.GET.get("type", "").strip()
    tier = request.GET.get("tier", "").strip()
    if tier and tier != SCHOOLS_TIER_OTHER:
        tier = ""
    major_slug = request.GET.get("major", "").strip()
    q = request.GET.get("q", "").strip()
    filter_major = None
    if major_slug:
        filter_major = (
            Major.objects.filter(slug=major_slug, is_active=True)
            .only("slug", "title", "country")
            .first()
        )
        if filter_major and not country:
            country = filter_major.country

    suggestions = None
    best_uni_slug = None
    if q:
        universities, suggestions, best_uni_slug = split_search_results(
            q,
            country_code=country,
            utype=utype,
            major_slug=major_slug if filter_major else "",
            tier_code=tier,
            primary_limit=1,
            related_limit=8,
        )
        total_count = len(universities) + (len(suggestions) if suggestions else 0)
        schools_has_more = False
    else:
        universities, total_count, schools_has_more = list_universities_browse(
            country_code=country,
            utype=utype,
            major_slug=major_slug if filter_major else "",
            tier_code=tier,
            offset=0,
            limit=SCHOOLS_PAGE_SIZE,
        )
    countries = University.COUNTRY_CHOICES
    types = University.TYPE_CHOICES
    country_labels = dict(countries)
    nav_ctx = parse_nav_degree_params(request.GET)

    scholarship_guides = []
    if nav_ctx.get("nav_show_scholarship_banner"):
        from .scholarship_catalog import build_country_scholarship_guides

        scholarship_guides = build_country_scholarship_guides(
            target_degree=nav_ctx.get("nav_target_degree") or "",
            country_filter=country,
            programs_per_country=2,
        )

    if filter_major:
        hero_title = f"دانشگاه‌های رشته {filter_major.title}"
        hero_lead = (
            f"دانشگاه‌هایی که رشته {filter_major.title} را "
            f"در {filter_major.get_country_display()} ارائه می‌دهند — مقایسه، رتبه و مشاوره پذیرش."
        )
    elif tier == SCHOOLS_TIER_OTHER and country:
        label = country_labels.get(country, country)
        hero_title = f"{SCHOOLS_TIER_OTHER_LABEL} — {label}"
        hero_lead = (
            f"دانشگاه‌های {label} خارج از ۳۰ مؤسسه برتر — جستجو، مقایسه و مشاوره پذیرش."
        )
    elif tier == SCHOOLS_TIER_OTHER:
        hero_title = SCHOOLS_TIER_OTHER_LABEL
        hero_lead = (
            "دانشگاه‌ها و موسسات خارج از ۳۰ مؤسسه برتر هر کشور — "
            "جستجو بر اساس نام و شهر، فیلتر کشور و نوع موسسه."
        )
    elif country:
        label = country_labels.get(country, country)
        hero_title = f"دانشگاه‌های {label}"
        hero_lead = (
            f"جستجو و مقایسه دانشگاه‌ها و موسسات مناسب پذیرش در {label} — "
            "با فیلتر هوشمند، رتبه جهانی و مشاوره تخصصی."
        )
    else:
        hero_title = "دانشگاه‌ها و موسسات مناسب پذیرش تحصیلی"
        hero_lead = (
            "لیست دانشگاه‌های کانادا، اسپانیا، چین و بیش از ۴۰ کشور دیگر — "
            "جستجو بر اساس نام و شهر، فیلتر کشور و نوع موسسه، و درخواست مشاوره برای انتخاب بهترین گزینه."
        )

    nav_items = schools_country_nav_items()
    world_country_nav = [i for i in nav_items if i.get("group") == "world"]
    active_world_country = next(
        (i for i in world_country_nav if i["code"] == country), None
    )

    return {
        "universities": universities,
        "total_count": total_count,
        "catalog_university_count": get_public_stats_cached()["university_count"],
        "schools_has_more": schools_has_more,
        "schools_page_size": SCHOOLS_PAGE_SIZE,
        "filter_q": q,
        "filter_country": country,
        "filter_type": utype,
        "filter_tier": tier,
        "schools_tier_other_label": SCHOOLS_TIER_OTHER_LABEL,
        "filter_major": filter_major,
        "filter_major_slug": major_slug if filter_major else "",
        "countries": countries,
        "types": types,
        "country_nav": [i for i in nav_items if i.get("group") == "primary"],
        "world_country_nav": world_country_nav,
        "active_world_country": active_world_country,
        "type_nav": _schools_type_nav(types),
        "scholarship_guides": scholarship_guides,
        "featured_universities": get_featured_universities(
            country_code=country,
            utype=utype,
            tier_code=tier,
            limit=FEATURED_UNIVERSITIES_LIMIT,
        ),
        "hero_title": hero_title,
        "hero_lead": hero_lead,
        "search_q": q,
        "suggestions": suggestions,
        "best_uni_slug": best_uni_slug,
        **nav_ctx,
    }


@cached_page
def schools_list(request):
    """لیست دانشگاه‌ها و موسسات مناسب پذیرش تحصیلی."""
    return render(request, "schools/list.html", _schools_page_context(request))


@never_cache
def schools_search(request):
    """جستجوی دانشگاه‌ها (AJAX) + بارگذاری تدریجی."""
    from .university_search import (
        SCHOOLS_PAGE_SIZE,
        SCHOOLS_PAGE_SIZE_MAX,
        SCHOOLS_TIER_OTHER,
        _normalize_query,
        list_universities_browse,
        split_search_results,
    )

    q = request.GET.get("q", "").strip()
    country = request.GET.get("country", "").strip()
    utype = request.GET.get("type", "").strip()
    tier = request.GET.get("tier", "").strip()
    if tier and tier != SCHOOLS_TIER_OTHER:
        tier = ""
    major_slug = request.GET.get("major", "").strip()
    partial = request.GET.get("partial", "").strip().lower() in ("1", "true", "yes")
    q_norm = _normalize_query(q)
    try:
        offset = max(0, int(request.GET.get("offset", 0) or 0))
    except (TypeError, ValueError):
        offset = 0
    try:
        limit = int(request.GET.get("limit", SCHOOLS_PAGE_SIZE) or SCHOOLS_PAGE_SIZE)
    except (TypeError, ValueError):
        limit = SCHOOLS_PAGE_SIZE
    limit = max(1, min(limit, SCHOOLS_PAGE_SIZE_MAX))

    cache_key = ""
    if not partial:
        if q_norm:
            cache_key = api_cache_key(
                "schools_search", country, utype, tier, major_slug, q_norm
            )
        elif offset > 0:
            cache_key = api_cache_key(
                "schools_partial", country, utype, tier, major_slug, str(offset), str(limit)
            )
        else:
            cache_key = api_cache_key(
                "schools_browse", country, utype, tier, major_slug, str(limit)
            )
        cached = get_api_cached(cache_key)
        if cached is not None:
            return _faq_api_json_response(cached)

    if q:
        universities, suggestions, best_slug = split_search_results(
            q,
            country_code=country,
            utype=utype,
            major_slug=major_slug,
            tier_code=tier,
            primary_limit=1,
            related_limit=8,
        )
        total_count = len(universities) + len(suggestions)
        schools_has_more = False
    elif partial and offset > 0:
        universities, total_count, schools_has_more = list_universities_browse(
            country_code=country,
            utype=utype,
            major_slug=major_slug,
            tier_code=tier,
            offset=offset,
            limit=limit,
        )
        suggestions = []
        best_slug = None
        cards_html = render_to_string(
            "schools/_schools_cards.html",
            {"universities": universities},
            request=request,
        )
        partial_data = {
            "ok": True,
            "partial": True,
            "cards_html": cards_html,
            "count": len(universities),
            "total": total_count,
            "has_more": schools_has_more,
            "next_offset": offset + len(universities),
        }
        if cache_key:
            set_browse_api_cached(cache_key, partial_data)
        return _faq_api_json_response(partial_data)
    elif not q:
        universities, total_count, schools_has_more = list_universities_browse(
            country_code=country,
            utype=utype,
            major_slug=major_slug,
            tier_code=tier,
            offset=0,
            limit=limit,
        )
        suggestions = []
        best_slug = None
    else:
        universities, total_count, schools_has_more = [], 0, False
        suggestions = []
        best_slug = None

    from .nav_degrees import parse_nav_degree_params

    nav_ctx = parse_nav_degree_params(request.GET)
    scholarship_guides = []
    if nav_ctx.get("nav_show_scholarship_banner"):
        from .scholarship_catalog import build_country_scholarship_guides

        scholarship_guides = build_country_scholarship_guides(
            target_degree=nav_ctx.get("nav_target_degree") or "",
            country_filter=country,
            programs_per_country=2,
        )

    html = render_to_string(
        "schools/_schools_list_content.html",
        {
            "universities": universities,
            "search_q": q,
            "suggestions": suggestions,
            "best_uni_slug": best_slug,
            "filter_country": country,
            "filter_major_slug": major_slug,
            "filter_type": utype,
            "filter_tier": tier,
            "total_count": total_count,
            "schools_has_more": schools_has_more,
            "schools_page_size": limit,
            "scholarship_guides": scholarship_guides,
            **nav_ctx,
        },
        request=request,
    )
    response_data = {
        "ok": True,
        "html": html,
        "count": len(universities) + (len(suggestions) if suggestions else 0),
        "primary_count": len(universities),
        "best_slug": best_slug,
        "related_count": len(suggestions) if suggestions else 0,
        "total": total_count,
        "has_more": schools_has_more,
        "next_offset": len(universities),
    }
    if cache_key and (q_norm or not partial):
        if q_norm:
            set_api_cached(cache_key, response_data)
        else:
            set_browse_api_cached(cache_key, response_data)
    return _faq_api_json_response(response_data)


@never_cache
def schools_suggest(request):
    """پیشنهاد دانشگاه برای autocomplete."""
    from .university_search import SCHOOLS_TIER_OTHER, _normalize_query, suggest_universities_ranked

    q = request.GET.get("q", "").strip()
    country = request.GET.get("country", "").strip()
    utype = request.GET.get("type", "").strip()
    tier = request.GET.get("tier", "").strip()
    if tier and tier != SCHOOLS_TIER_OTHER:
        tier = ""
    q_norm = _normalize_query(q)

    cache_key = ""
    if q_norm:
        cache_key = api_cache_key("schools_suggest", country, utype, tier, q_norm)
        cached = get_api_cached(cache_key)
        if cached is not None:
            return _faq_api_json_response(cached)

    ranked = suggest_universities_ranked(
        q, country_code=country, utype=utype, tier_code=tier, limit=8
    )
    suggestions = [
        {
            "title": uni.name_fa,
            "slug": uni.slug,
            "country": uni.get_country_display(),
            "smart_match": score >= 14.0,
        }
        for uni, score in ranked
    ]
    data = {
        "ok": True,
        "suggestions": suggestions,
        "smart": bool(q_norm and suggestions and suggestions[0].get("smart_match")),
    }
    if cache_key:
        set_api_cached(cache_key, data)
    return _faq_api_json_response(data)


@cached_page
def school_detail(request, slug):
    """صفحه جزئیات یک دانشگاه / موسسه."""
    from django.db.models import Prefetch

    from .models import UniversityFAQ
    from .evaluation_links import build_evaluation_url
    from .university_majors import (
        build_appointment_url,
        build_majors_list_url_for_university,
        get_university_linked_majors,
        group_majors_preview_by_category,
    )

    uni_fields = (
        "id",
        "slug",
        "name_fa",
        "name_en",
        "city",
        "country",
        "type",
        "world_rank",
        "short_description",
        "description",
        "image",
        "website",
        "is_approved_by_mo_science",
        "is_approved_by_mo_health",
        "meta_title",
        "meta_description",
    )
    university = get_object_or_404(
        University.objects.prefetch_related(
            "gallery_images",
            Prefetch(
                "faqs",
                queryset=UniversityFAQ.objects.filter(is_active=True).order_by(
                    "order", "id"
                ),
            ),
        ).only(*uni_fields),
        slug=slug,
    )
    linked_majors = get_university_linked_majors(university)
    major_groups = group_majors_preview_by_category(linked_majors)
    majors_list_url = build_majors_list_url_for_university(university)
    appointment_url = build_appointment_url(
        about="university",
        title=university.name_fa,
        country=university.get_country_display() if university.country else "",
    )
    evaluation_url = build_evaluation_url(
        country=university.country or "",
        university=university.slug,
        ref=f"uni-{university.slug}",
    )
    from .internal_linking import get_priority_related_universities

    related = get_priority_related_universities(
        country=university.country or "",
        exclude_slug=university.slug,
        limit=6,
    )
    from .schema_utils import country_iso_alpha2
    from .university_seo import build_university_page_seo

    institute = get_institute_cached()
    site_url = getattr(settings, "SITE_URL", "").rstrip("/")
    if not site_url:
        site_url = f"{request.scheme}://{request.get_host()}"
    canonical = f"{site_url}{reverse('school_detail', kwargs={'slug': university.slug})}"
    university_seo = build_university_page_seo(
        university=university,
        university_faqs=list(university.faqs.all()),
        linked_majors=linked_majors,
        site_url=site_url,
        canonical_url=canonical,
        institute_name=getattr(institute, "name", "") or "موسسه",
    )

    return render(
        request,
        "schools/detail.html",
        {
            "university": university,
            "related_universities": related,
            "university_faqs": list(university.faqs.all()),
            "linked_majors": linked_majors,
            "linked_majors_count": len(linked_majors),
            "major_groups": major_groups,
            "majors_list_url": majors_list_url,
            "appointment_url": appointment_url,
            "evaluation_url": evaluation_url,
            "type_icon": SCHOOL_TYPE_ICONS.get(university.type, "ti-book"),
            "country_flag": APPOINTMENT_COUNTRY_FLAGS.get(university.country, ""),
            "university_country_iso": country_iso_alpha2(university.country or ""),
            **university_seo,
        },
    )


@cached_page
def pricing(request):
    """صفحه تعرفه‌ها و ماشین‌حساب هوشمند."""
    from .pricing_calculator import get_calculator_steps
    from .pricing_seo import build_pricing_page_seo

    page_data = get_pricing_page_data_cached()
    institute = get_institute_cached()
    site_url = getattr(settings, "SITE_URL", "").rstrip("/")
    if not site_url:
        site_url = f"{request.scheme}://{request.get_host()}"

    seo = build_pricing_page_seo(
        request=request,
        institute_name=getattr(institute, "name", "") or "موسسه",
        site_url=site_url,
        tariffs=page_data["tariffs"],
    )

    return render(
        request,
        "core/pricing.html",
        {
            **page_data,
            "calculator_steps": get_calculator_steps(),
            **seo,
        },
    )


@require_POST
def pricing_calculate(request):
    """API ماشین‌حساب تعرفه — همیشه تازه (بدون کش) برای دقت قیمت."""
    from .pricing_calculator import CalculatorInput, calculate_pricing

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"ok": False, "error": "درخواست نامعتبر است."}, status=400)

    data = CalculatorInput(
        goal=(payload.get("goal") or "").strip(),
        situation=(payload.get("situation") or "").strip(),
        country_slug=(payload.get("country_slug") or "").strip(),
        extra_keys=payload.get("extra_keys") or [],
        excluded_keys=payload.get("excluded_keys") or [],
    )
    result = calculate_pricing(data)
    status = 200 if result.get("ok") else 400
    response = JsonResponse(result, status=status)
    response["Cache-Control"] = "no-store"
    return response


@never_cache
def site_suggest(request):
    """پیشنهاد زنده جستجوی سراسری برای نوبار."""
    from .site_navigation import has_active_courses_cached
    from .site_search import group_hits, suggest_site_search

    q = request.GET.get("q", "").strip()
    q_key = q.strip().lower()
    cache_key = api_cache_key("site_suggest", q_key) if len(q_key) >= 2 else ""
    if cache_key:
        cached = get_api_cached(cache_key)
        if cached is not None:
            return _faq_api_json_response(cached)

    include_courses = has_active_courses_cached()
    hits = suggest_site_search(
        q,
        limit=8,
        include_courses=include_courses,
    )
    from .site_query_correction import suggest_query_correction

    did_you_mean = suggest_query_correction(q, hits=hits)
    if did_you_mean and did_you_mean.strip().lower() == q.strip().lower():
        did_you_mean = None
    response_data = {
        "ok": True,
        "q": q,
        "smart": bool(q),
        "did_you_mean": did_you_mean,
        "count": len(hits),
        "groups": group_hits(hits, highlight_q=q),
        "suggestions": [h.to_dict(highlight_q=q) for h in hits],
    }
    if cache_key:
        set_api_cached(cache_key, response_data)
    return _faq_api_json_response(response_data)


@cached_page
def site_search_page(request):
    """صفحه نتایج جستجوی سراسری."""
    from .site_navigation import has_active_courses_cached
    from .site_search import group_hits, site_search

    q = request.GET.get("q", "").strip()
    include_courses = has_active_courses_cached()
    hits = site_search(
        q,
        limit=40,
        include_courses=include_courses,
    )
    from .site_query_correction import suggest_query_correction

    did_you_mean = suggest_query_correction(q, hits=hits)
    if did_you_mean and did_you_mean.strip().lower() == q.strip().lower():
        did_you_mean = None
    groups = group_hits(hits, highlight_q=q)
    type_filters = [
        {"type": g["type"], "label": g["type_label"], "count": len(g["items"])}
        for g in groups
    ]
    return render(
        request,
        "core/search.html",
        {
            "search_q": q,
            "hits": hits,
            "groups": groups,
            "type_filters": type_filters,
            "result_count": len(hits),
            "did_you_mean": did_you_mean,
        },
    )

