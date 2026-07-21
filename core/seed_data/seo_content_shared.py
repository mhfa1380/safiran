"""ثابت‌ها و لینک‌های مشترک تولید محتوای سئو."""
from __future__ import annotations

COUNTRY_SEO_HOOKS: dict[str, tuple[str, str]] = {
    "canada": ("PGWP و Co-op", "IELTS، بورسیه ورودی، مسیر اقامت"),
    "china": ("بورسیه CSC", "ویزای X2، شهریه مناسب"),
    "spain": ("ویزای D", "شهریه دولتی، هزینه پایین"),
    "germany": ("شهریه دولتی", "Blocked Account، تحصیل انگلیسی"),
    "uk": ("Student Route", "رتبه QS، بورسیه Chevening"),
    "usa": ("OPT و CPT", "بورسیه F-1، پذیرش ایرانی"),
    "australia": ("Post-Study Visa", "G8، بورسیه ورودی"),
    "france": ("Campus France", "بورسیه Eiffel، ویزای D"),
    "italy": ("ویزای D", "شهریه دولتی، هزینه مناسب"),
    "netherlands": ("MVV", "تحصیل انگلیسی‌زبان"),
    "japan": ("MEXT", "بورسیه دولتی"),
    "south_korea": ("GKS", "فناوری و تحقیق"),
    "malaysia": ("شهریه پایین", "برنامه‌های دو‌مدرکی"),
    "turkey": ("Türkiye Bursları", "نزدیکی فرهنگی"),
    "uae": ("ویزای دانشجویی", "کمپوس بین‌المللی"),
}


def evaluation_href(country_code: str, *, ref: str = "", major: str = "") -> str:
    try:
        from core.evaluation_links import build_evaluation_url

        return build_evaluation_url(country=country_code, major=major, ref=ref)
    except Exception:
        from urllib.parse import urlencode

        params: dict[str, str] = {}
        if country_code:
            params["country"] = country_code
        if major:
            params["major"] = major
        if ref:
            params["ref"] = ref
        q = f"?{urlencode(params)}" if params else ""
        return f"/ارزیابی-مهاجرت{q}"
