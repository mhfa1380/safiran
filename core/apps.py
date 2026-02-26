from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"
    verbose_name = "سفیران آینده روشن"

    def ready(self):
        import core.signals  # noqa: F401

        # استفاده از AdminSite سفارشی برای badge پیام‌های جدید
        from django.contrib import admin
        from core.admin_site import admin_site

        admin_site._registry = admin.site._registry.copy()
        # ModelAdminها باید admin_site ما را استفاده کنند تا each_context (و badge) در sidebar هم بیاید
        for model_admin in admin_site._registry.values():
            model_admin.admin_site = admin_site
        admin.site = admin_site
