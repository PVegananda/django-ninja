# utils/redis_client.py
"""
Utility functions untuk berinteraksi langsung dengan Redis menggunakan redis-py.

Digunakan untuk fitur yang memerlukan kontrol lebih detail atas data structure Redis,
seperti Sorted Sets (leaderboard), counter view, dll.

Untuk caching biasa, gunakan Django Cache Framework (django.core.cache.cache).
"""
import redis
import json

# Koneksi ke Redis (database 0 untuk raw Redis, database 1 untuk Django cache)
# host='redis' karena mengakses dari dalam Docker network
r = redis.Redis(host='redis', port=6379, db=0, decode_responses=True)


# =============================================================================
# Course Detail Cache (String)
# =============================================================================

def cache_course_detail(course_id, course_data, ttl=300):
    """
    Cache detail course sebagai JSON string.

    Args:
        course_id: ID course
        course_data: dict berisi data course
        ttl: Time-to-live dalam detik (default 5 menit)
    """
    key = f'course:{course_id}:detail'
    r.set(key, json.dumps(course_data), ex=ttl)


def get_cached_course_detail(course_id):
    """
    Ambil detail course dari cache.

    Returns:
        dict jika ada di cache, None jika tidak ada
    """
    key = f'course:{course_id}:detail'
    data = r.get(key)
    if data:
        return json.loads(data)
    return None


# =============================================================================
# View Counter (String / INCR)
# =============================================================================

def increment_course_views(course_id):
    """
    Increment view counter untuk course secara atomic.

    Returns:
        int: Total views setelah increment
    """
    key = f'course:{course_id}:views'
    return r.incr(key)


def get_course_views(course_id):
    """
    Ambil jumlah view sebuah course.

    Returns:
        int: Jumlah views (0 jika belum ada)
    """
    key = f'course:{course_id}:views'
    views = r.get(key)
    return int(views) if views else 0


# =============================================================================
# Leaderboard / Popularity (Sorted Set)
# =============================================================================

def update_course_popularity(course_id, score_increment=1):
    """
    Update popularity score course di Redis Sorted Set.
    Dipanggil setiap kali ada enrollment baru.

    Args:
        course_id: ID course
        score_increment: Nilai yang ditambahkan ke score (default 1)
    """
    r.zincrby('popular_courses', score_increment, f'course:{course_id}')


def get_top_courses(limit=10):
    """
    Ambil top N course terpopuler berdasarkan jumlah enrollment.

    Args:
        limit: Jumlah course yang dikembalikan (default 10)

    Returns:
        list of tuples: [(course_id_str, score), ...]
    """
    return r.zrevrange('popular_courses', 0, limit - 1, withscores=True)


def init_course_popularity(course_id, initial_score):
    """
    Inisialisasi score course di leaderboard.
    Biasanya dipanggil saat course pertama kali dibuat.

    Args:
        course_id: ID course
        initial_score: Score awal (misalnya jumlah member saat ini)
    """
    r.zadd('popular_courses', {f'course:{course_id}': initial_score})
