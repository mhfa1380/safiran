"""سئو صفحات دوره و مدرس."""

from __future__ import annotations

import json
from typing import Any

from django.urls import reverse

from .models import Course, CourseInstructor


def build_course_detail_seo(
    *,
    request,
    course: Course,
    institute_name: str,
    site_url: str,
) -> dict[str, Any]:
    base = site_url.rstrip("/")
    path = reverse("course_details", kwargs={"slug": course.slug})
    page_url = f"{base}{path}"

    meta_title = course.get_meta_title()
    meta_description = course.get_meta_description()
    og_title = f"{meta_title} | {institute_name}"

    instructor = course.instructor if getattr(course, "instructor_id", None) else None
    if instructor and instructor.is_active:
        instructor_url = f"{base}{instructor.get_absolute_url()}"
    else:
        instructor_url = ""

    course_schema: dict[str, Any] = {
        "@type": "Course",
        "@id": f"{page_url}#course",
        "name": course.title,
        "description": meta_description,
        "url": page_url,
        "provider": {
            "@type": "Organization",
            "name": institute_name,
            "url": f"{base}/",
        },
        "inLanguage": "fa-IR",
    }
    if course.duration_hours:
        course_schema["timeRequired"] = f"PT{course.duration_hours}H"
    if instructor and instructor.is_active:
        course_schema["instructor"] = {
            "@type": "Person",
            "name": instructor.name,
            "url": instructor_url,
            "jobTitle": instructor.position,
        }

    graph: list[dict[str, Any]] = [
        {
            "@type": "WebPage",
            "@id": f"{page_url}#webpage",
            "url": page_url,
            "name": meta_title,
            "description": meta_description,
            "inLanguage": "fa-IR",
        },
        course_schema,
        {
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "صفحه اصلی", "item": f"{base}/"},
                {
                    "@type": "ListItem",
                    "position": 2,
                    "name": "دوره‌ها",
                    "item": f"{base}{reverse('courses_list')}",
                },
                {"@type": "ListItem", "position": 3, "name": course.title, "item": page_url},
            ],
        },
    ]

    return {
        "course_meta_title": meta_title,
        "course_meta_description": meta_description,
        "course_page_url": page_url,
        "course_og_title": og_title,
        "course_schema_json": json.dumps(
            {"@context": "https://schema.org", "@graph": graph},
            ensure_ascii=False,
        ),
    }


def build_instructor_detail_seo(
    *,
    request,
    instructor: CourseInstructor,
    institute_name: str,
    site_url: str,
    courses: list[Course],
) -> dict[str, Any]:
    base = site_url.rstrip("/")
    path = instructor.get_absolute_url()
    page_url = f"{base}{path}"

    meta_title = instructor.get_meta_title()
    meta_description = instructor.get_meta_description()
    og_title = f"{meta_title} | {institute_name}"

    image_url = ""
    if instructor.image:
        image_url = request.build_absolute_uri(instructor.image.url)

    person: dict[str, Any] = {
        "@type": "Person",
        "@id": f"{page_url}#person",
        "name": instructor.name,
        "url": page_url,
        "jobTitle": instructor.position,
        "description": meta_description,
        "knowsAbout": instructor.get_specialties_list()[:8] or None,
        "worksFor": {
            "@type": "Organization",
            "name": institute_name,
            "url": f"{base}/",
        },
    }
    if image_url:
        person["image"] = image_url
    if instructor.email:
        person["email"] = instructor.email

    teaches = []
    for course in courses[:6]:
        teaches.append(
            {
                "@type": "Course",
                "name": course.title,
                "url": f"{base}{reverse('course_details', kwargs={'slug': course.slug})}",
            }
        )
    if teaches:
        person["teaches"] = teaches

    graph: list[dict[str, Any]] = [
        {
            "@type": "ProfilePage",
            "@id": f"{page_url}#webpage",
            "url": page_url,
            "name": meta_title,
            "description": meta_description,
            "inLanguage": "fa-IR",
            "mainEntity": {"@id": f"{page_url}#person"},
        },
        person,
        {
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "صفحه اصلی", "item": f"{base}/"},
                {
                    "@type": "ListItem",
                    "position": 2,
                    "name": "دوره‌ها",
                    "item": f"{base}{reverse('courses_list')}",
                },
                {"@type": "ListItem", "position": 3, "name": instructor.name, "item": page_url},
            ],
        },
    ]

    return {
        "instructor_meta_title": meta_title,
        "instructor_meta_description": meta_description,
        "instructor_page_url": page_url,
        "instructor_og_title": og_title,
        "instructor_schema_json": json.dumps(
            {"@context": "https://schema.org", "@graph": graph},
            ensure_ascii=False,
        ),
    }
