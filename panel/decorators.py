from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.http import HttpResponseForbidden

from panel.services import user_can_access_panel, user_is_panel_manager


def panel_login_required(view):
    @wraps(view)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path(), login_url="panel:login")
        if not user_can_access_panel(request.user):
            return HttpResponseForbidden("دسترسی به پنل پیگیری ندارید.")
        return view(request, *args, **kwargs)

    return _wrapped


def panel_manager_required(view):
    @wraps(view)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path(), login_url="panel:login")
        if not user_is_panel_manager(request.user):
            return HttpResponseForbidden("فقط مدیر پیگیری به این بخش دسترسی دارد.")
        return view(request, *args, **kwargs)

    return _wrapped
