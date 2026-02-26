import random
from datetime import date

from django import forms
from django.core.exceptions import ValidationError

from .models import ContactMessage, ConsultationRequest, EvaluationRequest
from .utils import gregorian_to_jalali


def generate_math_captcha():
    """یک سوال ریاضی ساده برای کپچا تولید می‌کند. (عدد، متن سوال، جواب)"""
    a, b = random.randint(1, 9), random.randint(1, 9)
    return (a, b, f"{a} + {b} = ?", str(a + b))


class BotProtectedFormMixin:
    """
    میکسین ساده برای اضافه کردن فیلد honeypot نامرئی به فرم‌ها
    تا بسیاری از ربات‌های ساده شناسایی و بلاک شوند.
    """

    honeypot = forms.CharField(
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


class ContactForm(BotProtectedFormMixin, forms.ModelForm):
    """فرم تماس با ما."""

    captcha_answer = forms.CharField(
        label="کد امنیتی",
        required=True,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "نتیجه را وارد کنید",
                "autocomplete": "off",
            }
        ),
    )

    def __init__(self, *args, captcha_expected=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._captcha_expected = captcha_expected

    def clean_captcha_answer(self):
        value = self.cleaned_data.get("captcha_answer", "").strip()
        if not self._captcha_expected:
            raise ValidationError("کد امنیتی منقضی شده. صفحه را رفرش کنید.")
        if value != str(self._captcha_expected):
            raise ValidationError("کد امنیتی نادرست است.")
        return value

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


class ConsultationRequestForm(BotProtectedFormMixin, forms.ModelForm):
    """فرم رزرو وقت مشاوره."""

    def __init__(self, *args, slot_queryset=None, **kwargs):
        super().__init__(*args, **kwargs)
        if slot_queryset is not None:
            self.fields["slot"].queryset = slot_queryset
        self.fields["slot"].required = True
        self.fields["slot"].label = "زمان مشاوره"

    def save(self, commit=True):
        instance = super().save(commit=False)
        if commit and instance.slot_id:
            instance.slot.is_booked = True
            instance.slot.save(update_fields=["is_booked"])
        if commit:
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


class EvaluationRequestForm(BotProtectedFormMixin, forms.ModelForm):
    """فرم ارزیابی اولیه شرایط متقاضی (الگو گرفته از Elmino)."""

    BIRTH_YEAR_CHOICES = [(y, y) for y in range(1350, 1405)]
    _jy, _, _ = gregorian_to_jalali(date.today().year, date.today().month, date.today().day)
    GRAD_YEAR_CHOICES = [("studying", "در حال تحصیل")] + [
        (str(y), str(y)) for y in range(1384, _jy + 11)
    ]

    birth_year = forms.TypedChoiceField(
        label="سال تولد",
        required=False,
        coerce=int,
        choices=BIRTH_YEAR_CHOICES,
        widget=forms.Select(attrs={"class": "form-control no-nice-select"}),
    )
    graduation_year = forms.ChoiceField(
        label="سال فارغ التحصیلی",
        required=False,
        choices=GRAD_YEAR_CHOICES,
        widget=forms.Select(attrs={"class": "form-control no-nice-select"}),
    )

    DESIRED_COUNTRY_CHOICES = [
        ("china", "چین"),
        ("canada", "کانادا"),
        ("spain", "اسپانیا"),
        ("not_sure", "هنوز تصمیم نگرفته‌ام"),
        ("other", "سایر کشورها"),
    ]
    desired_countries = forms.MultipleChoiceField(
        label="کشورهای مورد نظر شما",
        required=False,
        choices=DESIRED_COUNTRY_CHOICES,
        widget=forms.CheckboxSelectMultiple,
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
            # دستاوردها
            "has_journal_article",
            "has_conference_article",
            "has_book",
            "has_international_tests",
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
                attrs={"class": "form-control", "placeholder": "رشته تحصیلی"}
            ),
            "average_grade": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "مثلاً ۱۸.۵"}
            ),
            "language_test_type": forms.Select(
                attrs={"class": "form-control no-nice-select"}
            ),
            "has_ielts": forms.CheckboxInput(
                attrs={"class": "form-check-input", "style": "margin-right: 0;"}
            ),
            "language_score": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "مثلاً IELTS 6.5 / TOEFL 80",
                }
            ),
            "target_country": forms.Select(
                attrs={"class": "form-control no-nice-select"}
            ),
            "desired_major": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "رشته مورد نظر (اختیاری)"}
            ),
            "service_scope": forms.Select(
                attrs={"class": "form-control no-nice-select"}
            ),
            "preferred_intake": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "مثلاً پاییز ۱۴۰۴ / September 2025",
                }
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
        # ذخیره به صورت رشته جداشده با ویرگول برای سادگی
        return ",".join(data)

