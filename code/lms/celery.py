# lms/celery.py
"""
Konfigurasi Celery untuk Simple LMS.

File ini adalah entry point Celery. Menginisialisasi instance Celery app
dan mengkonfigurasinya untuk bekerja dengan Django settings.

Cara menjalankan worker (dari dalam Docker):
    celery -A lms worker -l info

Cara menjalankan beat scheduler:
    celery -A lms beat -l info
"""
import os
from celery import Celery

# Set default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lms.settings')

# Buat instance Celery dengan nama project
app = Celery('lms')

# Baca konfigurasi dari Django settings dengan prefix CELERY_
# Semua setting yang dimulai CELERY_ di settings.py akan digunakan
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks dari semua app yang terdaftar di INSTALLED_APPS
# Celery akan mencari file tasks.py di setiap app
app.autodiscover_tasks()
