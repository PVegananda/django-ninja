"""
URL configuration untuk Simple LMS - Modul 11: NoSQL MongoDB

Routes:
  /admin/           → Django Admin panel
  /silk/            → Django Silk profiling dashboard
  /api/v1/          → API v1 endpoints (basic operations)
  /api/v2/          → API v2 endpoints (enhanced responses)
  /api/analytics/   → Analytics API berbasis MongoDB (Modul 11)
  /                 → Semua URL dari app courses (lihat courses/urls.py)
"""

from django.contrib import admin
from django.urls import path, include
from courses.apiv1 import apiv1
from courses.apiv2 import apiv2
from analytics.api import analytics_api

urlpatterns = [
    path('admin/', admin.site.urls),
    path('silk/', include('silk.urls', namespace='silk')),
    path('api/v1/', apiv1.urls),
    path('api/v2/', apiv2.urls),
    path('api/analytics/', analytics_api.urls),
    path('', include('courses.urls')),
]
