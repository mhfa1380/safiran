"""گزینه‌های کشور فقط برای فرم ارزیابی (جدا از ConsultationRequest و بقیه سایت)."""

from core.study_destinations import ALL_DESTINATION_LABELS, country_flag_static

EVAL_FORM_COUNTRY_CARDS = [
    {"code": "canada", "label": "کانادا", "flag": country_flag_static("canada")},
    {"code": "spain", "label": "اسپانیا", "flag": country_flag_static("spain")},
    {"code": "china", "label": "چین", "flag": country_flag_static("china")},
    {"code": "germany", "label": "آلمان", "flag": country_flag_static("germany")},
    {"code": "italy", "label": "ایتالیا", "flag": country_flag_static("italy")},
    {"code": "uk", "label": ALL_DESTINATION_LABELS["uk"], "flag": country_flag_static("uk")},
    {"code": "usa", "label": ALL_DESTINATION_LABELS["usa"], "flag": country_flag_static("usa")},
    {"code": "australia", "label": ALL_DESTINATION_LABELS["australia"], "flag": country_flag_static("australia")},
]

EVAL_FORM_COUNTRY_EXTRAS = [
    {"code": "not_sure", "label": "هنوز مطمئن نیستم", "icon": "ti-help"},
    {"code": "other", "label": "سایر کشورها", "icon": "ti-world"},
]

_EVAL_REAL_CODES = [c["code"] for c in EVAL_FORM_COUNTRY_CARDS]

EVAL_FORM_TARGET_COUNTRY_CHOICES = [("", "— انتخاب کنید —")] + [
    (c["code"], c["label"]) for c in EVAL_FORM_COUNTRY_CARDS
] + [("other", "سایر کشورها")]

EVAL_FORM_DESIRED_COUNTRY_CHOICES = [
    (c["code"], c["label"]) for c in EVAL_FORM_COUNTRY_CARDS
] + [
    ("not_sure", "هنوز مطمئن نیستم"),
    ("other", "سایر کشورها"),
]

EVAL_FORM_REAL_COUNTRY_CODES = _EVAL_REAL_CODES

# گزینه‌های ذخیره‌شده در EvaluationRequest.target_country (بدون «هنوز مطمئن نیستم»)
EVAL_MODEL_TARGET_COUNTRY_CHOICES = [
    (c["code"], c["label"]) for c in EVAL_FORM_COUNTRY_CARDS
] + [("other", "سایر کشورها")]
