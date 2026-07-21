"""فرم ورود ادمین با کپچای حروفی (همان الگوی فرم تماس)."""

import re

from django.contrib.admin.forms import AdminAuthenticationForm
from django.core.exceptions import ValidationError

from .forms import CAPTCHA_LENGTH, build_captcha_answer_field

ADMIN_LOGIN_CAPTCHA_KEY = "admin_login_captcha"


class SafiranAdminLoginForm(AdminAuthenticationForm):
    """ورود ادمین + اعتبارسنجی کپچای session."""

    def clean_captcha_answer(self):
        raw = self.cleaned_data.get("captcha_answer") or ""
        value = re.sub(r"[^A-Za-z]", "", raw).upper()
        expected = None
        if self.request:
            expected = self.request.session.pop(ADMIN_LOGIN_CAPTCHA_KEY, None)
        if not expected or value != str(expected).upper():
            raise ValidationError("کد امنیتی نادرست است. دوباره تلاش کنید.")
        return value

    def __init__(self, request=None, *args, **kwargs):
        super().__init__(request, *args, **kwargs)
        if "captcha_answer" not in self.fields:
            field = build_captcha_answer_field()
            field.widget.attrs["class"] = "admin-login__captcha-input form-captcha__control"
            field.widget.attrs["placeholder"] = "کد را وارد کنید"
            field.max_length = CAPTCHA_LENGTH
            self.fields["captcha_answer"] = field
        if "username" in self.fields:
            self.fields["username"].label = "نام کاربری"
        if "password" in self.fields:
            self.fields["password"].label = "گذرواژه"
        for name in ("username", "password"):
            if name in self.fields:
                self.fields[name].widget.attrs.setdefault("class", "admin-login__input")
        if "username" in self.fields:
            self.fields["username"].widget.attrs.setdefault("placeholder", "نام کاربری")
            self.fields["username"].widget.attrs.setdefault("autocomplete", "username")
        if "password" in self.fields:
            self.fields["password"].widget.attrs.setdefault("placeholder", "گذرواژه")
            self.fields["password"].widget.attrs.setdefault("autocomplete", "current-password")
