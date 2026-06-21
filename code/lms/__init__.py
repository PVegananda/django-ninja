# lms/__init__.py
"""
Register Celery app saat Django startup.

Import ini memastikan Celery app selalu di-load saat Django start,
sehingga @shared_task decorator dapat berfungsi dengan benar di semua app.
"""
from .celery import app as celery_app

__all__ = ('celery_app',)
