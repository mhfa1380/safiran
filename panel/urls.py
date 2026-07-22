from django.urls import path

from panel import views

app_name = "panel"

urlpatterns = [
    path("login/", views.PanelLoginView.as_view(), name="login"),
    path("logout/", views.panel_logout, name="logout"),
    path("", views.dashboard, name="dashboard"),
    path("cases/", views.case_list, name="case_list"),
    path("cases/new/", views.case_create, name="case_create"),
    path("followup/", views.followup_queue, name="followup"),
    path("search/", views.search, name="search"),
    path("search/suggest/", views.search_suggest, name="search_suggest"),
    path("api/notifications/", views.notifications_api, name="notifications_api"),
    path("flow/", views.flow_view, name="flow"),
    path("calendar/", views.calendar_view, name="calendar"),
    path("report/", views.report_view, name="report"),
    path("report/export.csv", views.report_export_csv, name="report_export"),
    path("manage/", views.manage_view, name="manage"),
    path("settings/", views.settings_view, name="settings"),
    path("help/", views.help_page, name="help"),
    path("cases/<int:pk>/", views.case_detail, name="case_detail"),
    path("cases/<int:pk>/ai/", views.case_ai, name="case_ai"),
    path("cases/<int:pk>/call/", views.case_call, name="case_call"),
    path("cases/<int:pk>/close/", views.case_close, name="case_close"),
    path("cases/<int:pk>/stage/", views.case_stage, name="case_stage"),
    path("cases/<int:pk>/assign/", views.case_assign, name="case_assign"),
    path("cases/<int:pk>/claim/", views.case_claim, name="case_claim"),
    path("cases/<int:pk>/appointment/", views.case_appointment, name="case_appointment"),
    path("cases/<int:pk>/checklist/", views.case_checklist_toggle, name="case_checklist"),
    path("cases/<int:pk>/document/", views.case_document_upload, name="case_document"),
    path("cases/<int:pk>/reopen/", views.case_reopen, name="case_reopen"),
]
