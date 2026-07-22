from __future__ import annotations

from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User

from panel.models import CaseAppointment, CaseEvent, CustomerCase, PanelSettings
from panel.services import ROLE_MANAGER, ROLE_STAFF, user_is_panel_manager


class PanelLoginForm(AuthenticationForm):
    username = forms.CharField(
        label="نام کاربری",
        widget=forms.TextInput(
            attrs={"class": "pnl-input", "autocomplete": "username", "placeholder": "نام کاربری"}
        ),
    )
    password = forms.CharField(
        label="رمز عبور",
        widget=forms.PasswordInput(
            attrs={
                "class": "pnl-input",
                "autocomplete": "current-password",
                "placeholder": "رمز عبور",
            }
        ),
    )


class QuickCallForm(forms.Form):
    contact_result = forms.ChoiceField(
        label="نتیجه تماس",
        choices=CaseEvent.CONTACT_RESULT_CHOICES,
        initial=CaseEvent.CONTACT_ANSWERED,
        widget=forms.RadioSelect(attrs={"class": "pnl-call-radio"}),
    )
    notes = forms.CharField(
        label="گزارش تماس",
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "pnl-input pnl-call-textarea",
                "rows": 4,
                "placeholder": "چی گفته شد؟ مثلاً: کانادا کارشناسی، آیلتس ۶، بودجه متوسط، فردا مدارک می‌فرستد…",
            }
        ),
    )
    follow_preset = forms.ChoiceField(
        label="پیگیری بعدی",
        choices=[
            ("today_evening", "امروز عصر"),
            ("tomorrow", "فردا"),
            ("3days", "۳ روز"),
            ("1week", "۱ هفته"),
            ("custom", "تاریخ دلخواه"),
            ("none", "بدون موعد"),
        ],
        initial="tomorrow",
        widget=forms.RadioSelect(attrs={"class": "pnl-call-radio"}),
    )
    custom_jalali_date = forms.CharField(
        label="تاریخ شمسی پیگیری",
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "pnl-input",
                "placeholder": "1405/04/31",
                "dir": "ltr",
                "inputmode": "numeric",
            }
        ),
    )
    next = forms.CharField(required=False, widget=forms.HiddenInput())


class CloseCaseForm(forms.Form):
    loss_reason = forms.ChoiceField(
        label="دلیل مختومه",
        choices=CustomerCase.LOSS_REASON_CHOICES,
        widget=forms.Select(attrs={"class": "pnl-input"}),
    )
    loss_note = forms.CharField(
        label="توضیح",
        widget=forms.Textarea(
            attrs={"class": "pnl-input", "rows": 2, "placeholder": "توضیح کوتاه…"}
        ),
    )


class StageChangeForm(forms.Form):
    stage = forms.ChoiceField(
        label="مرحله",
        choices=[c for c in CustomerCase.STAGE_CHOICES if c[0] != CustomerCase.STAGE_LOST],
        widget=forms.Select(attrs={"class": "pnl-input"}),
    )


class AssignForm(forms.Form):
    assigned_to = forms.ModelChoiceField(
        label="مسئول",
        queryset=User.objects.none(),
        required=False,
        empty_label="— بدون مسئول —",
        widget=forms.Select(attrs={"class": "pnl-input"}),
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        qs = User.objects.filter(
            is_active=True,
            groups__name__in=[ROLE_STAFF, ROLE_MANAGER],
        ).distinct().order_by("username")
        if user and not user_is_panel_manager(user):
            qs = qs.filter(pk=user.pk)
        self.fields["assigned_to"].queryset = qs


class CaseFilterForm(forms.Form):
    q = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={"class": "pnl-input", "placeholder": "جستجو نام، موبایل، کد پرونده…"}
        ),
    )
    scope = forms.ChoiceField(
        required=False,
        choices=[
            ("", "همه باز"),
            ("mine", "مال من"),
            ("unassigned", "بدون مسئول"),
            ("overdue", "عقب‌افتاده"),
            ("today", "پیگیری امروز"),
            ("new", "جدید"),
            ("closed", "مختومه/موفق"),
        ],
        widget=forms.Select(attrs={"class": "pnl-input"}),
    )
    source = forms.ChoiceField(
        required=False,
        choices=[("", "همه منابع")] + list(CustomerCase.SOURCE_CHOICES),
        widget=forms.Select(attrs={"class": "pnl-input"}),
    )
    stage = forms.ChoiceField(
        required=False,
        choices=[("", "همه مراحل")] + list(CustomerCase.STAGE_CHOICES),
        widget=forms.Select(attrs={"class": "pnl-input"}),
    )
    assignee = forms.ModelChoiceField(
        required=False,
        queryset=User.objects.none(),
        empty_label="همه مسئول‌ها",
        widget=forms.Select(attrs={"class": "pnl-input"}),
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user and user_is_panel_manager(user):
            self.fields["assignee"].queryset = (
                User.objects.filter(
                    is_active=True,
                    groups__name__in=[ROLE_STAFF, ROLE_MANAGER],
                )
                .distinct()
                .order_by("username")
            )
        else:
            self.fields.pop("assignee", None)


class ManualCaseForm(forms.Form):
    full_name = forms.CharField(
        label="نام و نام خانوادگی",
        max_length=150,
        widget=forms.TextInput(
            attrs={
                "class": "pnl-input",
                "placeholder": "مثلاً سارا محمدی",
                "autocomplete": "name",
            }
        ),
    )
    phone = forms.CharField(
        label="موبایل",
        max_length=30,
        widget=forms.TextInput(
            attrs={
                "class": "pnl-input",
                "placeholder": "0912…",
                "inputmode": "tel",
                "dir": "ltr",
                "autocomplete": "tel",
            }
        ),
    )
    email = forms.EmailField(
        label="ایمیل",
        required=False,
        widget=forms.EmailInput(
            attrs={
                "class": "pnl-input",
                "placeholder": "اختیاری",
                "dir": "ltr",
                "autocomplete": "email",
            }
        ),
    )
    target_country = forms.CharField(
        label="کشور مقصد",
        required=False,
        max_length=50,
        widget=forms.TextInput(attrs={"class": "pnl-input", "placeholder": "مثلاً کانادا"}),
    )
    target_degree = forms.CharField(
        label="مقطع",
        required=False,
        max_length=50,
        widget=forms.TextInput(attrs={"class": "pnl-input", "placeholder": "مثلاً کارشناسی ارشد"}),
    )
    stage = forms.ChoiceField(
        label="مرحله شروع",
        choices=[
            (CustomerCase.STAGE_ATTRACTION, "جذب"),
            (CustomerCase.STAGE_INITIAL, "مشاوره اولیه"),
            (CustomerCase.STAGE_FOLLOW_UP, "پیگیری"),
        ],
        initial=CustomerCase.STAGE_ATTRACTION,
        widget=forms.Select(attrs={"class": "pnl-input"}),
    )
    notes = forms.CharField(
        label="یادداشت اولیه",
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "pnl-input",
                "rows": 3,
                "placeholder": "منبع تماس، توضیح کوتاه…",
            }
        ),
    )
    assign_to_me = forms.BooleanField(
        label="به من تخصیص بده",
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={"class": "pnl-create-check"}),
    )


class DocumentUploadForm(forms.Form):
    title = forms.CharField(
        label="عنوان مدرک",
        required=False,
        max_length=150,
        widget=forms.TextInput(attrs={"class": "pnl-input", "placeholder": "مثلاً پاسپورت"}),
    )
    file = forms.FileField(label="فایل", widget=forms.ClearableFileInput(attrs={"class": "pnl-input"}))


class AppointmentForm(forms.Form):
    kind = forms.ChoiceField(
        label="نوع جلسه",
        choices=CaseAppointment.KIND_CHOICES,
        initial=CaseAppointment.KIND_SPECIALIZED,
        widget=forms.Select(attrs={"class": "pnl-input"}),
    )
    mode = forms.ChoiceField(
        label="حضوری / آنلاین",
        choices=CaseAppointment.MODE_CHOICES,
        initial=CaseAppointment.MODE_ONLINE,
        widget=forms.Select(attrs={"class": "pnl-input"}),
    )
    jalali_date = forms.CharField(
        label="تاریخ شمسی",
        help_text="مثال: 1405/04/31",
        widget=forms.TextInput(
            attrs={"class": "pnl-input", "placeholder": "1405/04/31", "dir": "ltr"}
        ),
    )
    time_hm = forms.CharField(
        label="ساعت",
        help_text="مثال: 10:30",
        widget=forms.TextInput(
            attrs={"class": "pnl-input", "placeholder": "10:30", "dir": "ltr"}
        ),
    )
    title = forms.CharField(
        label="عنوان",
        required=False,
        max_length=200,
        widget=forms.TextInput(attrs={"class": "pnl-input", "placeholder": "اختیاری"}),
    )
    notes = forms.CharField(
        label="یادداشت",
        required=False,
        widget=forms.Textarea(attrs={"class": "pnl-input", "rows": 2}),
    )


class PanelSettingsForm(forms.Form):
    auto_assign_enabled = forms.BooleanField(
        label="تخصیص خودکار پروندهٔ جدید",
        required=False,
        widget=forms.CheckboxInput(),
    )
    auto_assign_mode = forms.ChoiceField(
        label="روش تخصیص خودکار",
        choices=PanelSettings.MODE_CHOICES,
        widget=forms.Select(attrs={"class": "pnl-input"}),
    )
    fixed_assignee = forms.ModelChoiceField(
        label="مسئول ثابت",
        queryset=User.objects.none(),
        required=False,
        empty_label="— انتخاب کنید —",
        widget=forms.Select(attrs={"class": "pnl-input"}),
    )
    daily_followup_enabled = forms.BooleanField(
        label="توزیع روزانهٔ خودکار صف پیگیری",
        required=False,
        widget=forms.CheckboxInput(),
    )
    daily_followup_mode = forms.ChoiceField(
        label="روش توزیع روزانه",
        choices=[c for c in PanelSettings.MODE_CHOICES if c[0] != PanelSettings.MODE_FIXED],
        widget=forms.Select(attrs={"class": "pnl-input"}),
    )
    daily_followup_scope = forms.ChoiceField(
        label="دامنهٔ توزیع روزانه",
        choices=PanelSettings.SCOPE_CHOICES,
        widget=forms.Select(attrs={"class": "pnl-input"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        qs = User.objects.filter(
            is_active=True,
            groups__name__in=[ROLE_STAFF, ROLE_MANAGER],
        ).distinct().order_by("username")
        self.fields["fixed_assignee"].queryset = qs
