# analytics/aggregation_service.py
"""
Service untuk Aggregation Pipeline MongoDB di Simple LMS.

Aggregation pipeline adalah fitur powerful MongoDB untuk menganalisis data,
mirip dengan GROUP BY, COUNT, SUM, AVG di SQL, tetapi lebih fleksibel.

Setiap fungsi menggunakan pipeline dengan stage-stage MongoDB:
  $match   → Filter dokumen (seperti WHERE di SQL)
  $group   → Agregasi data (seperti GROUP BY)
  $sort    → Mengurutkan hasil
  $limit   → Membatasi jumlah hasil
  $project → Memilih field yang ditampilkan (seperti SELECT)
"""
from datetime import datetime, timezone, timedelta
from utils.mongo_client import get_collection

COLLECTION_NAME = 'activity_logs'


def get_action_summary() -> list:
    """
    Menghitung jumlah setiap jenis aktivitas (action).

    Equivalent SQL:
        SELECT action, COUNT(*) as total FROM activity_logs GROUP BY action ORDER BY total DESC

    Returns:
        list of dict: [{'_id': 'view_course', 'total': 150}, ...]
    """
    collection = get_collection(COLLECTION_NAME)

    pipeline = [
        {
            '$group': {
                '_id': '$action',
                'total': {'$sum': 1}
            }
        },
        {
            '$sort': {'total': -1}
        }
    ]

    return list(collection.aggregate(pipeline))


def get_most_active_users(limit: int = 10) -> list:
    """
    Mengambil top N user paling aktif berdasarkan jumlah aktivitas.

    Equivalent SQL:
        SELECT username, COUNT(*) as total_activities
        FROM activity_logs GROUP BY username ORDER BY total_activities DESC LIMIT N

    Args:
        limit: Jumlah user yang dikembalikan (default 10)

    Returns:
        list of dict: [{'username': 'student1', 'total_activities': 50}, ...]
    """
    collection = get_collection(COLLECTION_NAME)

    pipeline = [
        {
            '$group': {
                '_id': '$username',
                'user_id': {'$first': '$user_id'},
                'total_activities': {'$sum': 1}
            }
        },
        {
            '$sort': {'total_activities': -1}
        },
        {
            '$limit': limit
        },
        {
            '$project': {
                '_id': 0,
                'username': '$_id',
                'user_id': 1,
                'total_activities': 1
            }
        }
    ]

    return list(collection.aggregate(pipeline))


def get_popular_courses_from_logs(limit: int = 10) -> list:
    """
    Mengambil top N course terpopuler berdasarkan activity logs di MongoDB.

    Hanya menghitung aktivitas 'view_course' dan 'enroll_course'.

    Args:
        limit: Jumlah course yang dikembalikan (default 10)

    Returns:
        list of dict: [{'course_name': 'Django Basics', 'course_id': 1, 'views': 200}, ...]
    """
    collection = get_collection(COLLECTION_NAME)

    pipeline = [
        {
            '$match': {
                'action': {'$in': ['view_course', 'enroll_course']},
                'course_id': {'$exists': True}
            }
        },
        {
            '$group': {
                '_id': '$course_id',
                'course_name': {'$first': '$course_name'},
                'total_interactions': {'$sum': 1},
                'view_count': {
                    '$sum': {'$cond': [{'$eq': ['$action', 'view_course']}, 1, 0]}
                },
                'enroll_count': {
                    '$sum': {'$cond': [{'$eq': ['$action', 'enroll_course']}, 1, 0]}
                }
            }
        },
        {
            '$sort': {'total_interactions': -1}
        },
        {
            '$limit': limit
        },
        {
            '$project': {
                '_id': 0,
                'course_id': '$_id',
                'course_name': 1,
                'total_interactions': 1,
                'view_count': 1,
                'enroll_count': 1
            }
        }
    ]

    return list(collection.aggregate(pipeline))


def get_daily_activity_stats(days: int = 7) -> list:
    """
    Mengambil statistik aktivitas harian untuk N hari terakhir.

    Equivalent SQL:
        SELECT DATE(timestamp) as date, COUNT(*) as total
        FROM activity_logs WHERE timestamp >= NOW() - INTERVAL '7 days'
        GROUP BY DATE(timestamp) ORDER BY date DESC

    Args:
        days: Jumlah hari ke belakang (default 7)

    Returns:
        list of dict: [{'date': '2025-01-15', 'total': 350}, ...]
    """
    collection = get_collection(COLLECTION_NAME)

    since = datetime.now(timezone.utc) - timedelta(days=days)

    pipeline = [
        {
            '$match': {
                'timestamp': {'$gte': since}
            }
        },
        {
            '$group': {
                '_id': {
                    'year': {'$year': '$timestamp'},
                    'month': {'$month': '$timestamp'},
                    'day': {'$dayOfMonth': '$timestamp'}
                },
                'total': {'$sum': 1}
            }
        },
        {
            '$sort': {'_id': -1}
        },
        {
            '$project': {
                '_id': 0,
                'date': {
                    '$dateToString': {
                        'format': '%Y-%m-%d',
                        'date': {
                            '$dateFromParts': {
                                'year': '$_id.year',
                                'month': '$_id.month',
                                'day': '$_id.day'
                            }
                        }
                    }
                },
                'total': 1
            }
        }
    ]

    return list(collection.aggregate(pipeline))


def get_user_course_stats(user_id: int) -> dict:
    """
    Mengambil statistik aktivitas seorang user secara lengkap.

    Args:
        user_id: ID user

    Returns:
        dict: Statistik user {'total_activities': 50, 'courses_viewed': 10, ...}
    """
    collection = get_collection(COLLECTION_NAME)

    pipeline = [
        {
            '$match': {'user_id': user_id}
        },
        {
            '$group': {
                '_id': '$user_id',
                'total_activities': {'$sum': 1},
                'unique_courses': {'$addToSet': '$course_id'},
                'actions': {'$push': '$action'}
            }
        },
        {
            '$project': {
                '_id': 0,
                'user_id': '$_id',
                'total_activities': 1,
                'courses_visited': {'$size': '$unique_courses'},
            }
        }
    ]

    result = list(collection.aggregate(pipeline))
    if result:
        return result[0]
    return {'user_id': user_id, 'total_activities': 0, 'courses_visited': 0}
