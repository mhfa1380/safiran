from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"
    verbose_name = "سفیران آینده روشن"

    def ready(self):
        import os

        from django.conf import settings

        import core.signals  # noqa: F401 — شامل setup_sqlite_pragmas روی connection_created
        from core.file_cleanup import connect_upload_file_signals

        connect_upload_file_signals()

        if getattr(settings, "MHFA_FOOTER_ENABLED", False):
            if not settings.DEBUG or os.environ.get("RUN_MAIN") == "true":
                from core.mhfa_live import warm_footer_cache_async

                warm_footer_cache_async()

        # استفاده از AdminSite سفارشی برای badge پیام‌های جدید
        from django.contrib import admin
        from core.admin_site import admin_site

        admin_site._registry = admin.site._registry.copy()
        # ModelAdminها باید admin_site ما را استفاده کنند تا each_context (و badge) در sidebar هم بیاید
        for model_admin in admin_site._registry.values():
            model_admin.admin_site = admin_site
        admin.site = admin_site

        from core.admin_auth import register_auth_admin

        register_auth_admin(admin.site)
