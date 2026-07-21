"""منبع آشنایی کاربر — فرم ارزیابی و رزرو مشاوره."""
from __future__ import annotations

REFERRAL_WEBSITE = "website"
REFERRAL_GOOGLE = "google"
REFERRAL_SOCIAL = "social"
REFERRAL_FRIEND = "friend"
REFERRAL_UNIVERSITY = "university"
REFERRAL_AD = "advertisement"
REFERRAL_OTHER = "other"

REFERRAL_SOURCE_CHOICES: tuple[tuple[str, str], ...] = (
    (REFERRAL_WEBSITE, "سایت saroshan.ir"),
    (REFERRAL_GOOGLE, "گوگل / جستجو"),
    (REFERRAL_SOCIAL, "شبکه اجتماعی"),
    (REFERRAL_FRIEND, "معرفی دوستان یا آشنایان"),
    (REFERRAL_UNIVERSITY, "دانشگاه / مدرسه / استاد"),
    (REFERRAL_AD, "تبلیغات (بیلبورد، پیامک و …)"),
    (REFERRAL_OTHER, "سایر"),
)

SOCIAL_BALE = "bale"
SOCIAL_EITAA = "eitaa"
SOCIAL_TELEGRAM = "telegram"
SOCIAL_INSTAGRAM = "instagram"

REFERRAL_SOCIAL_CHOICES: tuple[tuple[str, str], ...] = (
    (SOCIAL_BALE, "بله"),
    (SOCIAL_EITAA, "ایتا"),
    (SOCIAL_TELEGRAM, "تلگرام"),
    (SOCIAL_INSTAGRAM, "اینستاگرام"),
)

_REFERRAL_LABELS = dict(REFERRAL_SOURCE_CHOICES)
_SOCIAL_LABELS = dict(REFERRAL_SOCIAL_CHOICES)


def format_referral_display(
    source: str,
    social_platform: str = "",
    detail: str = "",
) -> str:
    """متن قابل‌خواندن برای ادمین و گزارش."""
    if not source:
        return "—"
    parts = [_REFERRAL_LABELS.get(source, source)]
    if source == REFERRAL_SOCIAL and social_platform:
        parts.append(_SOCIAL_LABELS.get(social_platform, social_platform))
    detail = (detail or "").strip()
    if detail:
        parts.append(f"({detail})")
    return " — ".join(parts)
