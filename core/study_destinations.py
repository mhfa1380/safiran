"""
کشورهای مقصد تحصیلی — منبع واحد برای لیبل، پرچم، و گروه‌بندی UI.
"""
from __future__ import annotations

# کشورهای اصلی با صفحه StudyCountry و رشته‌های کامل
PRIMARY_STUDY_COUNTRY_CODES = frozenset({"canada", "spain", "china"})

# کشورهای پرطرفدار جهان (خارج از سه کشور اصلی)
WORLD_STUDY_COUNTRY_CODES = (
    "uk",
    "usa",
    "australia",
    "germany",
    "italy",
    "france",
    "netherlands",
    "switzerland",
    "japan",
    "south_korea",
    "singapore",
    "hong_kong",
    "ireland",
    "sweden",
    "belgium",
    "austria",
    "new_zealand",
    "denmark",
    "finland",
    "norway",
    "portugal",
    "poland",
    "czech",
    "hungary",
    "greece",
    "turkey",
    "malaysia",
    "uae",
    "saudi_arabia",
    "qatar",
    "india",
    "thailand",
    "israel",
    "brazil",
    "mexico",
    "argentina",
    "chile",
    "south_africa",
    "egypt",
    "russia",
    "taiwan",
)

WORLD_STUDY_COUNTRY_LABELS: dict[str, str] = {
    "uk": "انگلستان",
    "usa": "آمریکا",
    "australia": "استرالیا",
    "germany": "آلمان",
    "italy": "ایتالیا",
    "france": "فرانسه",
    "netherlands": "هلند",
    "switzerland": "سوئیس",
    "japan": "ژاپن",
    "south_korea": "کره جنوبی",
    "singapore": "سنگاپور",
    "hong_kong": "هنگ‌کنگ",
    "ireland": "ایرلند",
    "sweden": "سوئد",
    "belgium": "بلژیک",
    "austria": "اتریش",
    "new_zealand": "نیوزیلند",
    "denmark": "دانمارک",
    "finland": "فنلاند",
    "norway": "نروژ",
    "portugal": "پرتغال",
    "poland": "لهستان",
    "czech": "جمهوری چک",
    "hungary": "مجارستان",
    "greece": "یونان",
    "turkey": "ترکیه",
    "malaysia": "مالزی",
    "uae": "امارات",
    "saudi_arabia": "عربستان",
    "qatar": "قطر",
    "india": "هند",
    "thailand": "تایلند",
    "israel": "اسرائیل",
    "brazil": "برزیل",
    "mexico": "مکزیک",
    "argentina": "آرژانتین",
    "chile": "شیلی",
    "south_africa": "آفریقای جنوبی",
    "egypt": "مصر",
    "russia": "روسیه",
    "taiwan": "تایوان",
}

PRIMARY_STUDY_COUNTRY_LABELS: dict[str, str] = {
    "canada": "کانادا",
    "spain": "اسپانیا",
    "china": "چین",
}

# ISO 3166-1 alpha-2 برای فایل پرچم در static/img/flags/
COUNTRY_FLAG_FILES: dict[str, str] = {
    "canada": "img/flags/ca.svg",
    "spain": "img/flags/es.svg",
    "china": "img/flags/cn.svg",
    "germany": "img/flags/de.svg",
    "italy": "img/flags/it.svg",
    "uk": "img/flags/gb.svg",
    "usa": "img/flags/us.svg",
    "australia": "img/flags/au.svg",
    "france": "img/flags/fr.svg",
    "netherlands": "img/flags/nl.svg",
    "switzerland": "img/flags/ch.svg",
    "japan": "img/flags/jp.svg",
    "south_korea": "img/flags/kr.svg",
    "singapore": "img/flags/sg.svg",
    "hong_kong": "img/flags/hk.svg",
    "ireland": "img/flags/ie.svg",
    "sweden": "img/flags/se.svg",
    "belgium": "img/flags/be.svg",
    "austria": "img/flags/at.svg",
    "new_zealand": "img/flags/nz.svg",
    "denmark": "img/flags/dk.svg",
    "finland": "img/flags/fi.svg",
    "norway": "img/flags/no.svg",
    "portugal": "img/flags/pt.svg",
    "poland": "img/flags/pl.svg",
    "czech": "img/flags/cz.svg",
    "hungary": "img/flags/hu.svg",
    "greece": "img/flags/gr.svg",
    "turkey": "img/flags/tr.svg",
    "malaysia": "img/flags/my.svg",
    "uae": "img/flags/ae.svg",
    "saudi_arabia": "img/flags/sa.svg",
    "qatar": "img/flags/qa.svg",
    "india": "img/flags/in.svg",
    "thailand": "img/flags/th.svg",
    "israel": "img/flags/il.svg",
    "brazil": "img/flags/br.svg",
    "mexico": "img/flags/mx.svg",
    "argentina": "img/flags/ar.svg",
    "chile": "img/flags/cl.svg",
    "south_africa": "img/flags/za.svg",
    "egypt": "img/flags/eg.svg",
    "russia": "img/flags/ru.svg",
    "taiwan": "img/flags/tw.svg",
    "other": "",
}

CONSULTATION_COUNTRY_CHOICES = [
    ("canada", "کانادا"),
    ("spain", "اسپانیا"),
    ("china", "چین"),
    ("other", "سایر کشورها"),
]

UNIVERSITY_COUNTRY_CHOICES = [
    ("canada", "کانادا"),
    ("spain", "اسپانیا"),
    ("china", "چین"),
] + [(code, WORLD_STUDY_COUNTRY_LABELS[code]) for code in WORLD_STUDY_COUNTRY_CODES] + [
    ("other", "سایر کشورها"),
]

ALL_DESTINATION_LABELS: dict[str, str] = {
    **PRIMARY_STUDY_COUNTRY_LABELS,
    **WORLD_STUDY_COUNTRY_LABELS,
    "other": "سایر کشورها",
    "not_sure": "هنوز مطمئن نیستم",
    "germany": "آلمان",
    "italy": "ایتالیا",
}


def is_primary_study_country(code: str) -> bool:
    return code in PRIMARY_STUDY_COUNTRY_CODES


def is_world_study_country(code: str) -> bool:
    return code in WORLD_STUDY_COUNTRY_CODES


def country_flag_static(code: str) -> str:
    return COUNTRY_FLAG_FILES.get(code, "")


def schools_country_nav_items() -> list[dict]:
    """ناوبری کشور برای لیست دانشگاه‌ها — اصلی + سایر کشورها."""
    items = []
    for code, label in PRIMARY_STUDY_COUNTRY_LABELS.items():
        items.append(
            {"code": code, "label": label, "flag": country_flag_static(code), "group": "primary"}
        )
    for code in WORLD_STUDY_COUNTRY_CODES:
        items.append(
            {
                "code": code,
                "label": WORLD_STUDY_COUNTRY_LABELS[code],
                "flag": country_flag_static(code),
                "group": "world",
            }
        )
    return items


def majors_country_nav_items() -> tuple[list[dict], list[dict]]:
    """ناوبری کشور صفحه رشته‌ها — فقط کشورهایی که رشته فعال دارند."""
    from core.models import Major

    codes = frozenset(
        Major.objects.filter(is_active=True)
        .exclude(country="")
        .values_list("country", flat=True)
        .distinct()
    )
    primary: list[dict] = []
    world: list[dict] = []
    for item in schools_country_nav_items():
        if item["code"] not in codes:
            continue
        if item.get("group") == "primary":
            primary.append(item)
        elif item.get("group") == "world":
            world.append(item)
    return primary, world
