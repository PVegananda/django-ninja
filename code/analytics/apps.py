"""
Analytics app untuk Simple LMS.

App ini bertanggung jawab untuk menyimpan dan mengambil data analytics
dari MongoDB. Tidak menggunakan Django ORM karena MongoDB bukan relational database.

Komponen:
- activity_service.py  : Logic untuk menyimpan activity logs
- aggregation_service.py : Logic untuk aggregation pipeline (analisis data)
- api.py               : Endpoint API untuk analytics
"""
from django.apps import AppConfig


class AnalyticsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'analytics'
    verbose_name = 'Analytics (MongoDB)'
