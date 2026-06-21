# analytics/api.py
"""
Analytics API Endpoints untuk Simple LMS.

Semua endpoint di sini berinteraksi dengan MongoDB melalui
activity_service dan aggregation_service.

Base URL: /api/analytics/
"""
from ninja import NinjaAPI
from ninja.errors import HttpError
from ninja_simple_jwt.auth.ninja_auth import HttpJwtAuth
from analytics.activity_service import (
    log_activity, get_user_activities,
    get_course_activities, get_all_activities,
    ACTION_VIEW_COURSE, ACTION_ENROLL, ACTION_POST_COMMENT,
    ACTION_VIEW_CONTENT, ACTION_LOGIN
)
from analytics.aggregation_service import (
    get_action_summary, get_most_active_users,
    get_popular_courses_from_logs, get_daily_activity_stats,
    get_user_course_stats
)
from datetime import datetime

analytics_api = NinjaAPI(
    title="Simple LMS Analytics API",
    version="1.0.0",
    description="Analytics API menggunakan MongoDB sebagai document store - Modul 11",
    urls_namespace="analytics"
)

apiAuth = HttpJwtAuth()


# ============================================================================
# ACTIVITY LOG ENDPOINTS
# ============================================================================

@analytics_api.post('activities/log/', auth=apiAuth, tags=["Activity Logs"])
def create_activity_log(request, action: str, course_id: int = None,
                        course_name: str = None, browser: str = None):
    """
    Mencatat aktivitas user saat ini ke MongoDB.

    Query Parameters:
    - action: Jenis aktivitas (view_course, enroll_course, post_comment, view_content, login)
    - course_id: ID course terkait (opsional)
    - course_name: Nama course (opsional)
    - browser: Browser yang digunakan (opsional, dari metadata)

    Response: ID dokumen MongoDB yang baru dibuat

    Authentication: Wajib login (Bearer token)
    """
    valid_actions = [ACTION_VIEW_COURSE, ACTION_ENROLL, ACTION_POST_COMMENT,
                     ACTION_VIEW_CONTENT, ACTION_LOGIN]

    if action not in valid_actions:
        raise HttpError(400, f"Action tidak valid. Pilih salah satu: {valid_actions}")

    metadata = {}
    if browser:
        metadata['browser'] = browser

    # Ambil IP dari request
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded:
        metadata['ip'] = x_forwarded.split(',')[0]
    else:
        metadata['ip'] = request.META.get('REMOTE_ADDR', 'unknown')

    doc_id = log_activity(
        user_id=request.user.id,
        username=request.user.username,
        action=action,
        course_id=course_id,
        course_name=course_name,
        metadata=metadata if metadata else None
    )

    return {
        "message": "Aktivitas berhasil dicatat",
        "document_id": doc_id,
        "action": action,
        "timestamp": datetime.utcnow().isoformat()
    }


@analytics_api.get('activities/my/', auth=apiAuth, tags=["Activity Logs"])
def get_my_activities(request, limit: int = 20):
    """
    Mengambil riwayat aktivitas user yang sedang login.

    Query Parameters:
    - limit: Jumlah aktivitas yang dikembalikan (default 20, max 100)

    Authentication: Wajib login (Bearer token)
    """
    if limit > 100:
        limit = 100

    activities = get_user_activities(user_id=request.user.id, limit=limit)

    # Konversi datetime ke string agar bisa di-serialize ke JSON
    for activity in activities:
        if 'timestamp' in activity and isinstance(activity['timestamp'], datetime):
            activity['timestamp'] = activity['timestamp'].isoformat()

    return {
        "user_id": request.user.id,
        "username": request.user.username,
        "total_returned": len(activities),
        "activities": activities
    }


@analytics_api.get('activities/course/{course_id}/', auth=apiAuth, tags=["Activity Logs"])
def get_activities_by_course(request, course_id: int, limit: int = 50):
    """
    Mengambil semua aktivitas yang berkaitan dengan sebuah course.

    Path Parameters:
    - course_id: ID course

    Query Parameters:
    - limit: Jumlah aktivitas (default 50, max 200)

    Authentication: Wajib login (Bearer token)
    """
    if limit > 200:
        limit = 200

    activities = get_course_activities(course_id=course_id, limit=limit)

    for activity in activities:
        if 'timestamp' in activity and isinstance(activity['timestamp'], datetime):
            activity['timestamp'] = activity['timestamp'].isoformat()

    return {
        "course_id": course_id,
        "total_returned": len(activities),
        "activities": activities
    }


@analytics_api.get('activities/all/', auth=apiAuth, tags=["Activity Logs"])
def get_all_activity_logs(request, limit: int = 100):
    """
    Mengambil semua activity logs terbaru (hanya superadmin).

    Query Parameters:
    - limit: Jumlah aktivitas (default 100, max 500)

    Authentication: Wajib login (Bearer token) + Superadmin
    """
    if not request.user.is_superuser:
        raise HttpError(403, "Hanya superadmin yang dapat melihat semua activity logs")

    if limit > 500:
        limit = 500

    activities = get_all_activities(limit=limit)

    for activity in activities:
        if 'timestamp' in activity and isinstance(activity['timestamp'], datetime):
            activity['timestamp'] = activity['timestamp'].isoformat()

    return {
        "total_returned": len(activities),
        "activities": activities
    }


# ============================================================================
# ANALYTICS / AGGREGATION ENDPOINTS
# ============================================================================

@analytics_api.get('stats/action-summary/', tags=["Analytics"])
def action_summary(request):
    """
    Menampilkan ringkasan jumlah setiap jenis aktivitas.

    Menggunakan MongoDB Aggregation Pipeline ($group + $sort).

    Response: [{"_id": "view_course", "total": 150}, ...]
    """
    result = get_action_summary()
    return {"summary": result}


@analytics_api.get('stats/active-users/', tags=["Analytics"])
def most_active_users(request, limit: int = 10):
    """
    Menampilkan top N user paling aktif berdasarkan jumlah aktivitas.

    Query Parameters:
    - limit: Jumlah user (default 10, max 50)

    Response: [{"username": "student1", "total_activities": 50}, ...]
    """
    if limit > 50:
        limit = 50
    result = get_most_active_users(limit=limit)
    return {"top_users": result}


@analytics_api.get('stats/popular-courses/', tags=["Analytics"])
def popular_courses_analytics(request, limit: int = 10):
    """
    Menampilkan top N course terpopuler berdasarkan activity logs di MongoDB.

    Berbeda dengan endpoint Redis leaderboard, ini menghitung
    berdasarkan data historis di MongoDB.

    Query Parameters:
    - limit: Jumlah course (default 10, max 50)

    Response: [{"course_name": "Django Basics", "total_interactions": 200}, ...]
    """
    if limit > 50:
        limit = 50
    result = get_popular_courses_from_logs(limit=limit)
    return {"popular_courses": result}


@analytics_api.get('stats/daily/', tags=["Analytics"])
def daily_activity_stats(request, days: int = 7):
    """
    Menampilkan statistik aktivitas harian untuk N hari terakhir.

    Berguna untuk dashboard activity trend.

    Query Parameters:
    - days: Jumlah hari ke belakang (default 7, max 30)

    Response: [{"date": "2025-01-15", "total": 350}, ...]
    """
    if days > 30:
        days = 30
    result = get_daily_activity_stats(days=days)
    return {"daily_stats": result, "period_days": days}


@analytics_api.get('stats/user/{user_id}/', auth=apiAuth, tags=["Analytics"])
def user_stats(request, user_id: int):
    """
    Menampilkan statistik lengkap aktivitas seorang user.

    Path Parameters:
    - user_id: ID user

    Authentication: Wajib login (hanya diri sendiri atau superadmin)
    """
    # Hanya boleh melihat data diri sendiri atau jika superadmin
    if request.user.id != user_id and not request.user.is_superuser:
        raise HttpError(403, "Anda hanya bisa melihat statistik diri sendiri")

    result = get_user_course_stats(user_id=user_id)
    return result
