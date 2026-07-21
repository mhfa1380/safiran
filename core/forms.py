import random
import re
from datetime import date

from django import forms
from django.core.exceptions import ValidationError
from django.db import transaction

from .evaluation_form_countries import (
    EVAL_FORM_DESIRED_COUNTRY_CHOICES,
    EVAL_FORM_TARGET_COUNTRY_CHOICES,
)
from .evaluation_validation import (
    normalize_average_grade_for_storage,
    normalize_language_score_for_storage,
    pick_target_country_from_desired,
    validate_average_grade,
    validate_language_score,
    validate_phone,
    validate_preferred_intake,
)
from .models import ContactMessage, ConsultationRequest, EvaluationRequest
from .referral_source import (
    REFERRAL_GOOGLE,
    REFERRAL_OTHER,
    REFERRAL_SOCIAL,
    REFERRAL_SOCIAL_CHOICES,
    REFERRAL_SOURCE_CHOICES,
)
from .utils import gregorian_to_jalali

INTAKE_TERMS = ("پاییز", "بهار", "تابستان")
INTAKE_YEARS_AHEAD = 40
INTAKE_EXTEND_STEP = 5


def current_jalali_year() -> int:
    jy, _, _ = gregorian_to_jalali(date.today().year, date.today().month, date.today().day)
    return jy


def build_intake_choices(*, start_year: int | None = None, years_ahead: int = INTAKE_YEARS_AHEAD):
    """گزینه‌های ترم/سال شروع از امسال شمسی به بعد."""
    jy = start_year if start_year is not None else current_jalali_year()
    choices = [("", "انتخاب ترم / سال")]
    for y in range(jy, jy + years_ahead + 1):
        for term in INTAKE_TERMS:
            label = f"{term} {y}"
            choices.append((label, label))
    return choices


CAPTCHA_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ"
CAPTCHA_LENGTH = 5


def generate_captcha():
    """کد حروفی تصادفی؛ (متن نمایشی، جواب)."""
    code = "".join(random.choices(CAPTCHA_ALPHABET, k=CAPTCHA_LENGTH))
    return " ".join(code), code


def generate_math_captcha():
    """سازگاری با کد قبلی ادمین — (a, b, question, answer)."""
    display, answer = generate_captcha()
    return display, answer, display, answer


def build_captcha_answer_field():
    return forms.CharField(
        label="کد امنیتی",
        required=True,
        max_length=CAPTCHA_LENGTH,
        widget=forms.TextInput(
            attrs={
                "class": "form-control form-captcha__control",
                "placeholder": "کد را وارد کنید",
                "autocomplete": "off",
                "inputmode": "text",
                "spellcheck": "false",
                "dir": "ltr",
                "maxlength": str(CAPTCHA_LENGTH),
            }
        ),
    )


CAPTCHA_SESSION_KEYS = {
    "contact": "contact_captcha_answer",
    "appointment": "appointment_captcha_answer",
    "evaluation": "evaluation_captcha_answer",
}


def init_form_with_captcha(request, form_class, session_key, *, post_data=None, **form_kwargs):
    """ساخت فرم با کپچای حروفی ذخیره‌شده در سشن."""
    if request.method == "POST":
        expected = request.session.pop(session_key, None)
        data = post_data if post_data is not None else request.POST
        form = form_class(data, captcha_expected=expected, **form_kwargs)
    else:
        form = form_class(captcha_expected=None, **form_kwargs)
    captcha_question, captcha_answer = generate_captcha()
    request.session[session_key] = captcha_answer
    return form, captcha_question


class MathCaptchaMixin:
    """فیلد و اعتبارسنجی کپچای حروفی برای فرم‌های عمومی."""

    def __init__(self, *args, captcha_expected=None, **kwargs):
        self._captcha_expected = captcha_expected
        super().__init__(*args, **kwargs)
        if "captcha_answer" not in self.fields:
            self.fields["captcha_answer"] = build_captcha_answer_field()

    def clean_captcha_answer(self):
        raw = self.cleaned_data.get("captcha_answer", "")
        value = re.sub(r"[^A-Za-z]", "", raw).upper()
        if not self._captcha_expected:
            raise ValidationError("کد امنیتی منقضی شده. صفحه را رفرش کنید.")
        if value != str(self._captcha_expected).upper():
            raise ValidationError("کد امنیتی نادرست است.")
        return value


class BotProtectedFormMixin:
    """
    میکسین ساده برای اضافه کردن فیلد honeypot نامرئی به فرم‌ها
    تا بسیاری از ربات‌های ساده شناسایی و بلاک شوند.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "honeypot" not in self.fields:
            self.fields["honeypot"] = forms.CharField(
                required=False,
                widget=forms.TextInput(
                    attrs={
                        "class": "hp-field",
                        "autocomplete": "off",
                        "tabindex": "-1",
                        "aria-hidden": "true",
                        "style": "display:none;",
                    }
                ),
            )

    def clean_honeypot(self):
        value = (self.cleaned_data.get("honeypot") or "").strip()
        if value:
            raise ValidationError("ارسال نامعتبر بود.")
        return value


class QuickConsultationForm(BotProtectedFormMixin, forms.Form):
    """فرم ساده درخواست مشاوره از صفحه لیست دانشگاه‌ها."""

    full_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "نام و نام خانوادگی"}
        ),
    )
    phone = forms.CharField(
        max_length=20,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "شماره تماس"}
        ),
    )
    university_id = forms.IntegerField(required=False, widget=forms.HiddenInput())


class ContactForm(MathCaptchaMixin, BotProtectedFormMixin, forms.ModelForm):
    """فرم تماس با ما."""

    class Meta:
        model = ContactMessage
        fields = ["full_name", "email", "subject", "message"]
        widgets = {
            "full_name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "نام خود را وارد کنید"}
            ),
            "email": forms.EmailInput(
                attrs={"class": "form-control", "placeholder": "ایمیل خود را وارد کنید"}
            ),
            "subject": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "موضوع پیام را وارد کنید"}
            ),
            "message": forms.Textarea(
                attrs={
                    "class": "form-control w-100",
                    "rows": 9,
                    "placeholder": "متن پیام را وارد کنید",
                }
            ),
        }


class ReferralSourceFormMixin:
    """فیلدهای «از کجا با ما آشنا شدید» — مشترک ارزیابی و مشاوره."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._configure_referral_fields()

    def _configure_referral_fields(self):
        """ModelForm فیلدهای مدل را با TextInput می‌سازد — ویجت کارت‌ها را اینجا تنظیم می‌کنیم."""
        if "referral_source" in self.fields:
            self.fields["referral_source"].widget = forms.HiddenInput()
            self.fields["referral_source"].required = True
        if "referral_social_platform" in self.fields:
            self.fields["referral_social_platform"].widget = forms.HiddenInput()
            self.fields["referral_social_platform"].required = False
        if "referral_detail" in self.fields:
            self.fields["referral_detail"].widget = forms.TextInput(
                attrs={
                    "class": "form-control ref-src__detail-input",
                    "placeholder": "توضیح کوتاه…",
                    "maxlength": "200",
                    "autocomplete": "off",
                }
            )
            self.fields["referral_detail"].required = False

    referral_source = forms.ChoiceField(
        label="از کجا با موسسه آشنا شدید؟",
        choices=REFERRAL_SOURCE_CHOICES,
        required=True,
        widget=forms.HiddenInput,
    )
    referral_social_platform = forms.ChoiceField(
        label="کدام شبکه اجتماعی؟",
        choices=[("", "—")] + list(REFERRAL_SOCIAL_CHOICES),
        required=False,
        widget=forms.HiddenInput,
    )
    referral_detail = forms.CharField(
        label="جزئیات",
        required=False,
        max_length=200,
        widget=forms.TextInput(
            attrs={
                "class": "form-control ref-src__detail-input",
                "placeholder": "توضیح کوتاه…",
                "maxlength": "200",
                "autocomplete": "off",
            }
        ),
    )

    def clean(self):
        cleaned = super().clean()
        src = (cleaned.get("referral_source") or "").strip()
        if not src:
            self.add_error(
                "referral_source",
                "لطفاً مشخص کنید از کجا با ما آشنا شدید.",
            )
            return cleaned

        social = (cleaned.get("referral_social_platform") or "").strip()
        detail = (cleaned.get("referral_detail") or "").strip()

        if src == REFERRAL_SOCIAL and not social:
            self.add_error(
                "referral_social_platform",
                "یکی از شبکه‌های اجتماعی را انتخاب کنید.",
            )

        if src == REFERRAL_OTHER and not detail:
            self.add_error(
                "referral_detail",
                "لطفاً منبع را به‌اختصار بنویسید.",
            )

        if src != REFERRAL_SOCIAL:
            cleaned["referral_social_platform"] = ""
        if src not in (REFERRAL_GOOGLE, REFERRAL_OTHER):
            cleaned["referral_detail"] = ""
        else:
            cleaned["referral_detail"] = detail[:200]

        return cleaned


class ConsultationRequestForm(
    ReferralSourceFormMixin, MathCaptchaMixin, BotProtectedFormMixin, forms.ModelForm
):
    """فرم رزرو وقت مشاوره."""

    def __init__(self, *args, slot_queryset=None, captcha_expected=None, **kwargs):
        super().__init__(*args, captcha_expected=captcha_expected, **kwargs)
        if slot_queryset is not None:
            self.fields["slot"].queryset = slot_queryset
        self.fields["slot"].required = True
        self.fields["slot"].label = "زمان مشاوره"

    def save(self, commit=True):
        instance = super().save(commit=False)
        if not commit:
            return instance

        if instance.slot_id:
            from core.models import ConsultationSlot

            with transaction.atomic():
                slot = (
                    ConsultationSlot.objects.select_for_update()
                    .filter(pk=instance.slot_id, is_booked=False)
                    .first()
                )
                if not slot:
                    raise ValidationError("این زمان قبلاً رزرو شده است. لطفاً زمان دیگری انتخاب کنید.")
                ConsultationSlot.objects.filter(pk=slot.pk).update(is_booked=True)
                instance.save()
            return instance

        instance.save()
        return instance

    class Meta:
        model = ConsultationRequest
        fields = [
            "full_name",
            "phone",
            "email",
            "consultation_type",
            "country",
            "slot",
            "description",
            "referral_source",
            "referral_social_platform",
            "referral_detail",
        ]
        widgets = {
            "full_name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "نام و نام خانوادگی"}
            ),
            "phone": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "شماره تماس"}
            ),
            "email": forms.EmailInput(
                attrs={"class": "form-control", "placeholder": "آدرس ایمیل (اختیاری)"}
            ),
            "consultation_type": forms.Select(attrs={"class": "form-control"}),
            "country": forms.Select(attrs={"class": "form-control"}),
            "slot": forms.RadioSelect(attrs={"class": "form-check-input"}),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "شرایط، اهداف و سوالات خود را بنویسید...",
                }
            ),
        }


class EvaluationRequestForm(
    ReferralSourceFormMixin, MathCaptchaMixin, BotProtectedFormMixin, forms.ModelForm
):
    """فرم ارزیابی اولیه شرایط متقاضی (الگو گرفته از Elmino)."""

    BIRTH_YEAR_CHOICES = [("", "انتخاب سال")] + [(y, y) for y in range(1350, 1405)]
    _jy_static, _, _ = gregorian_to_jalali(date.today().year, date.today().month, date.today().day)
    GRAD_YEAR_CHOICES = [("", "انتخاب سال"), ("studying", "در حال تحصیل")] + [
        (str(y), str(y)) for y in range(1384, _jy_static + 11)
    ]

    birth_year = forms.TypedChoiceField(
        label="سال تولد",
        required=False,
        coerce=lambda v: int(v) if v not in (None, "") else None,
        choices=BIRTH_YEAR_CHOICES,
        widget=forms.Select(attrs={"class": "form-control no-nice-select"}),
    )
    graduation_year = forms.ChoiceField(
        label="سال فارغ التحصیلی",
        required=False,
        choices=GRAD_YEAR_CHOICES,
        widget=forms.Select(attrs={"class": "form-control no-nice-select"}),
    )
    preferred_intake = forms.ChoiceField(
        label="ترم / سال شروع",
        required=False,
        choices=[("", "انتخاب ترم / سال")],
        widget=forms.Select(attrs={"class": "form-control no-nice-select"}),
    )

    desired_countries = forms.MultipleChoiceField(
        label="کشورهای مورد نظر شما",
        required=False,
        choices=EVAL_FORM_DESIRED_COUNTRY_CHOICES,
        widget=forms.CheckboxSelectMultiple,
    )
    target_country = forms.ChoiceField(
        label="کشور مقصد",
        required=False,
        choices=EVAL_FORM_TARGET_COUNTRY_CHOICES,
        widget=forms.HiddenInput(),
    )

    class Meta:
        model = EvaluationRequest
        fields = [
            # اطلاعات شخصی
            "full_name",
            "phone",
            "email",
            "birth_year",
            "marital_status",
            "apply_timeline",
            "has_financial_capacity",
            # سوابق تحصیلی
            "current_degree",
            "field_of_study",
            "average_grade",
            "graduation_year",
            # آزمون زبان
            "language_test_type",
            "has_ielts",
            "language_score",
            # اولویت‌ها و کشور مقصد
            "target_country",
            "desired_countries",
            "desired_major",
            "service_scope",
            # سایر
            "preferred_intake",
            "notes",
            "referral_source",
            "referral_social_platform",
            "referral_detail",
            # دستاوردها
            "has_journal_article",
            "has_conference_article",
            "has_book",
            "has_international_tests",
        ]
        widgets = {
            "full_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "نام و نام خانوادگی",
                    "autocomplete": "name",
                }
            ),
            "phone": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "۰۹۱۲۳۴۵۶۷۸۹",
                    "inputmode": "tel",
                    "autocomplete": "tel",
                }
            ),
            "email": forms.EmailInput(
                attrs={"class": "form-control", "placeholder": "آدرس ایمیل (اختیاری)"}
            ),
            "marital_status": forms.Select(
                attrs={"class": "form-control no-nice-select"}
            ),
            "apply_timeline": forms.Select(
                attrs={"class": "form-control no-nice-select"}
            ),
            "has_financial_capacity": forms.CheckboxInput(
                attrs={"class": "form-check-input", "style": "margin-right: 0;"}
            ),
            "current_degree": forms.Select(
                attrs={"class": "form-control no-nice-select"}
            ),
            "field_of_study": forms.TextInput(
                attrs={
                    "class": "form-control major-combobox__field",
                    "placeholder": "جستجو یا نام رشته را بنویسید…",
                    "autocomplete": "off",
                    "role": "combobox",
                    "aria-autocomplete": "list",
                    "aria-expanded": "false",
                }
            ),
            "average_grade": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "۰ تا ۲۰ — مثلاً ۱۷.۵ (درصد: ۸۵٪)",
                    "inputmode": "decimal",
                    "autocomplete": "off",
                }
            ),
            "language_test_type": forms.Select(
                attrs={"class": "form-control no-nice-select"}
            ),
            "has_ielts": forms.HiddenInput(),
            "language_score": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "مثلاً IELTS 6.5 / TOEFL 80",
                }
            ),
            "desired_major": forms.TextInput(
                attrs={
                    "class": "form-control major-combobox__field",
                    "placeholder": "جستجو یا نام رشته مورد نظر…",
                    "autocomplete": "off",
                    "role": "combobox",
                    "aria-autocomplete": "list",
                    "aria-expanded": "false",
                }
            ),
            "service_scope": forms.Select(
                attrs={"class": "form-control no-nice-select"}
            ),
            "notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "اولویت‌ها، بودجه تقریبی، کشور یا دانشگاه‌های مورد علاقه و ...",
                }
            ),
            "has_journal_article": forms.CheckboxInput(
                attrs={"class": "form-check-input", "style": "margin-right: 0;"}
            ),
            "has_conference_article": forms.CheckboxInput(
                attrs={"class": "form-check-input", "style": "margin-right: 0;"}
            ),
            "has_book": forms.CheckboxInput(
                attrs={"class": "form-check-input", "style": "margin-right: 0;"}
            ),
            "has_international_tests": forms.CheckboxInput(
                attrs={"class": "form-check-input", "style": "margin-right: 0;"}
            ),
        }

    def clean_desired_countries(self):
        data = self.cleaned_data.get("desired_countries") or []
        if not data:
            raise ValidationError("حداقل یک کشور مقصد را انتخاب کنید.")
        return ",".join(data)

    def clean_desired_major(self):
        raw = (self.cleaned_data.get("desired_major") or "").strip()
        if not raw:
            raise ValidationError("رشته مورد نظر الزامی است.")
        return raw

    def clean_average_grade(self):
        raw = (self.cleaned_data.get("average_grade") or "").strip()
        if not raw:
            raise ValidationError("معدل الزامی است.")
        result = validate_average_grade(raw)
        if result["status"] == "error":
            raise ValidationError(result["message"])
        return normalize_average_grade_for_storage(raw)

    def clean_phone(self):
        raw = (self.cleaned_data.get("phone") or "").strip()
        if not raw:
            raise ValidationError("شماره تماس الزامی است.")
        result = validate_phone(raw)
        if result["status"] == "error":
            raise ValidationError(result["message"])
        return raw

    def clean_language_score(self):
        raw = (self.cleaned_data.get("language_score") or "").strip()
        test = self.data.get("language_test_type") or EvaluationRequest.TEST_NONE
        if test == EvaluationRequest.TEST_NONE:
            return ""
        if not raw:
            return ""
        result = validate_language_score(test, raw)
        if result["status"] == "error":
            raise ValidationError(result["message"])
        return normalize_language_score_for_storage(raw)

    def clean_preferred_intake(self):
        raw = (self.cleaned_data.get("preferred_intake") or "").strip()
        if not raw:
            return ""
        result = validate_preferred_intake(raw, min_jalali_year=current_jalali_year())
        if result["status"] == "error":
            raise ValidationError(result["message"])
        return raw

    def clean(self):
        cleaned = super().clean()
        if self.errors:
            return cleaned

        desired_csv = cleaned.get("desired_countries") or ""
        cleaned["target_country"] = pick_target_country_from_desired(desired_csv) or cleaned.get(
            "target_country"
        )

        test = cleaned.get("language_test_type") or EvaluationRequest.TEST_NONE
        cleaned["has_ielts"] = test != EvaluationRequest.TEST_NONE

        return cleaned

    def __init__(self, *args, captcha_expected=None, **kwargs):
        super().__init__(*args, captcha_expected=captcha_expected, **kwargs)
        self.fields["preferred_intake"].choices = build_intake_choices()
        self.fields["graduation_year"].choices = [("", "انتخاب سال"), ("studying", "در حال تحصیل")] + [
            (str(y), str(y)) for y in range(1384, current_jalali_year() + 11)
        ]
        if "service_scope" in self.fields:
            self.fields["service_scope"].empty_label = None
        if "desired_major" in self.fields:
            self.fields["desired_major"].required = True
        if not self.is_bound:
            if "marital_status" in self.fields:
                self.fields["marital_status"].empty_label = None
                self.fields["marital_status"].initial = EvaluationRequest.MARITAL_SINGLE
            if "apply_timeline" in self.fields:
                self.fields["apply_timeline"].empty_label = None
                self.fields["apply_timeline"].initial = EvaluationRequest.APPLY_SOON
        for name in (
            "full_name",
            "phone",
            "email",
            "field_of_study",
            "average_grade",
            "language_score",
            "desired_major",
        ):
            if name in self.fields:
                self.fields[name].widget.attrs.setdefault("class", "form-control eval-input")
        for name in (
            "birth_year",
            "graduation_year",
            "preferred_intake",
            "marital_status",
            "apply_timeline",
            "current_degree",
            "language_test_type",
            "target_country",
            "service_scope",
        ):
            if name in self.fields:
                cls = self.fields[name].widget.attrs.get("class", "form-control")
                self.fields[name].widget.attrs["class"] = f"{cls} eval-input eval-input--select"

