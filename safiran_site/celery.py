"""Celery application — فقط وقتی CELERY_ENABLED=1 در .env فعال است worker لازم است."""

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "safiran_site.settings")

app = Celery("safiran_site")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
