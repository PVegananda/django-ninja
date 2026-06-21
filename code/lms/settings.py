"""
Django settings untuk Simple LMS - Modul 12: Message Brokers & Async Tasks

Melanjutkan dari modul-modul sebelumnya dengan tambahan:
- Celery + RabbitMQ untuk asynchronous task processing
- Celery Beat untuk periodic tasks (cron jobs)
- Redis sebagai result backend Celery (DB 2)
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: jangan gunakan key ini di production!
SECRET_KEY = "django-insecure-lab05-db-optimization-simple-lms-key-2025"

# SECURITY WARNING: matikan DEBUG di production!
DEBUG = True

ALLOWED_HOSTS = ['*']


# =============================================================================
# Aplikasi yang terdaftar
# =============================================================================

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "silk",                 # Django Silk - query profiling (Modul 05)
    "ninja_simple_jwt",     # JWT authentication (Modul 07)
    "courses",              # Aplikasi Simple LMS kita
    "analytics",            # Analytics app berbasis MongoDB (Modul 11)
]


# =============================================================================
# Middleware
# =============================================================================

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "silk.middleware.SilkyMiddleware",  # Silk harus di posisi awal (setelah Security)
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "lms.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "lms.wsgi.application"


# =============================================================================
# Database - PostgreSQL (sesuai docker-compose.yml)
# =============================================================================
# Berbeda dengan Lab-compliance yang menggunakan SQLite,
# lab ini menggunakan PostgreSQL agar optimasi index terlihat nyata.

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "lms_db",
        "USER": "postgres",
        "PASSWORD": "postgres",
        "HOST": "database",  # Nama service di docker-compose.yml
        "PORT": "5432",
    }
}


# =============================================================================
# Django Silk - Konfigurasi Profiling
# Akses dashboard di: http://localhost:8000/silk/
# =============================================================================

SILKY_PYTHON_PROFILER = True   # Aktifkan function-level profiling
SILKY_META = True              # Track query Silk sendiri (untuk transparansi)


# =============================================================================
# Password validation
# =============================================================================

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# =============================================================================
# Internationalization
# =============================================================================

LANGUAGE_CODE = "id"
TIME_ZONE = "Asia/Jakarta"
USE_I18N = True
USE_TZ = True


# =============================================================================
# Static dan Media files
# =============================================================================

STATIC_URL = "static/"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# =============================================================================
# Redis Cache Configuration - Modul 10: NoSQL Redis
# =============================================================================
# django-redis sebagai backend cache, menyimpan data di Redis db 1
# KEY_PREFIX: namespace untuk menghindari collision dengan key lain
# TIMEOUT: default TTL 5 menit (300 detik)

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://redis:6379/1",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
        "KEY_PREFIX": "simple_lms",
        "TIMEOUT": 300,  # Default TTL: 5 menit
    }
}


# =============================================================================
# Session Configuration - Redis Session Backend
# =============================================================================
# Menggunakan Redis (via cache) sebagai session store,
# jauh lebih cepat daripada database session default.

SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"
SESSION_COOKIE_AGE = 86400          # 24 jam dalam detik
SESSION_SAVE_EVERY_REQUEST = False  # Hanya save jika session berubah


# =============================================================================
# Celery Configuration - Modul 12: Message Brokers & Async Tasks
# =============================================================================
# Broker: RabbitMQ (AMQP) untuk mengantri task
# Result Backend: Redis DB 2 untuk menyimpan hasil task

CELERY_BROKER_URL = os.environ.get(
    'CELERY_BROKER_URL',
    'amqp://admin:password123@rabbitmq:5672//'
)

CELERY_RESULT_BACKEND = os.environ.get(
    'CELERY_RESULT_BACKEND',
    'redis://redis:6379/2'
)

# Serialisasi pesan dalam format JSON (aman dan universal)
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'

# Timezone sesuai dengan Django (Asia/Jakarta)
CELERY_TIMEZONE = 'Asia/Jakarta'

# Pastikan task result tidak expired terlalu cepat (1 hari)
CELERY_RESULT_EXPIRES = 86400

# =============================================================================
# Celery Beat - Periodic Tasks (cron jobs)
# =============================================================================
# Jadwal task yang berjalan otomatis tanpa trigger manual.
# Celery Beat mengirim task ke queue sesuai jadwal,
# Celery Worker yang mengeksekusinya.

from celery.schedules import crontab  # noqa: E402

CELERY_BEAT_SCHEDULE = {
    # Generate statistik harian setiap tengah malam
    'daily-course-stats': {
        'task': 'courses.tasks.generate_daily_stats',
        'schedule': crontab(hour=0, minute=0),  # Setiap hari pukul 00:00 WIB
        'args': (),
    },
    # Cleanup MongoDB activity logs yang sudah lebih dari 30 hari
    'cleanup-old-activity-logs': {
        'task': 'courses.tasks.cleanup_old_logs',
        'schedule': crontab(hour=2, minute=0),  # Setiap hari pukul 02:00 WIB
        'args': (),
    },
}
