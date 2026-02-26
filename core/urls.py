"""URL routing for core app."""
from django.shortcuts import redirect
from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    # آدرس‌های سئو‌فرندلی با کلمات کلیدی فارسی
    path("درباره-ما/", views.about, name="about"),
    path("team/<int:pk>/", views.team_member_detail, name="team_member_detail"),
    path("blog/", views.blog_list, name="blog"),
    path("blog/<slug:slug>/", views.blog_detail, name="blog_detail"),
    path("تماس-با-ما/", views.contact, name="contact"),
    path("universities/", views.universities, name="universities"),
    path("رشته-های-تحصیلی/", views.majors, name="majors"),
    path("رشته/<slug:slug>/", views.major_details, name="major_details"),
    path("خدمات-موسسه/", views.services, name="services"),
    path("elements/", views.elements, name="elements"),
    path("دوره-های-تحصیلی/", views.courses_list, name="courses_list"),
    path("دوره/<slug:slug>/", views.course_details, name="course_details"),
    path("رزرو-مشاوره/", views.appointment, name="appointment"),
    path("appointment/slots/", views.appointment_slots, name="appointment_slots"),
    path("quick-consultation/", views.quick_consultation, name="quick_consultation"),
    path("ارزیابی-مهاجرت/", views.evaluation, name="evaluation"),
    path("سوالات-متداول/", views.faq, name="faq"),
    path("faq/search/", views.faq_search, name="faq_search"),
    path("دانشگاه-های-خارج/", views.schools_list, name="schools_list"),
    path("دانشگاه/<slug:slug>/", views.school_detail, name="school_detail"),
    # ریدایرکت ۳۰۱ برای آدرس‌های قدیمی (حفظ سئو و لینک‌ها)
    path("about/", lambda r: redirect("about", permanent=True)),
    path("contact/", lambda r: redirect("contact", permanent=True)),
    path("majors/", lambda r: redirect("majors", permanent=True)),
    path("major/<slug:slug>/", lambda r, slug: redirect("major_details", slug=slug, permanent=True)),
    path("services/", lambda r: redirect("services", permanent=True)),
    path("courses/", lambda r: redirect("courses_list", permanent=True)),
    path("course/<slug:slug>/", lambda r, slug: redirect("course_details", slug=slug, permanent=True)),
    path("appointment/", lambda r: redirect("appointment", permanent=True)),
    path("evaluation/", lambda r: redirect("evaluation", permanent=True)),
    path("faq/", lambda r: redirect("faq", permanent=True)),
    path("schools/", lambda r: redirect("schools_list", permanent=True)),
    path("schools/<slug:slug>/", lambda r, slug: redirect("school_detail", slug=slug, permanent=True)),
]
