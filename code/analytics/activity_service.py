# analytics/activity_service.py
"""
Service untuk mencatat dan mengambil Activity Logs ke/dari MongoDB.

Activity Log adalah catatan setiap aktivitas user di Simple LMS,
seperti melihat course, mendaftar, memberi komentar, dll.

Struktur dokumen activity_logs:
{
    "_id": ObjectId("..."),         # Auto-generated oleh MongoDB
    "user_id": 1,                   # FK ke users (PostgreSQL)
    "username": "student1",         # Denormalized untuk performa query
    "action": "view_course",        # Jenis aktivitas
    "course_id": 5,                 # FK ke courses (PostgreSQL) - optional
    "course_name": "Django Basics", # Denormalized
    "metadata": {                   # Data tambahan sesuai jenis aktivitas
        "ip": "192.168.1.1",
        "browser": "Chrome",
        "duration_seconds": 1200
    },
    "timestamp": ISODate("...")     # Waktu aktivitas
}
"""
from datetime import datetime, timezone
from utils.mongo_client import get_collection

# Nama collection di MongoDB
COLLECTION_NAME = 'activity_logs'

# Konstanta jenis aksi
ACTION_VIEW_COURSE = 'view_course'
ACTION_ENROLL = 'enroll_course'
ACTION_POST_COMMENT = 'post_comment'
ACTION_VIEW_CONTENT = 'view_content'
ACTION_LOGIN = 'login'


def log_activity(user_id: int, username: str, action: str,
                 course_id: int = None, course_name: str = None,
                 metadata: dict = None):
    """
    Mencatat satu aktivitas user ke MongoDB.

    Args:
        user_id: ID user dari PostgreSQL
        username: Username (denormalized untuk performa)
        action: Jenis aktivitas (gunakan konstanta ACTION_*)
        course_id: ID course terkait (opsional)
        course_name: Nama course (denormalized, opsional)
        metadata: Dict berisi data tambahan sesuai konteks

    Returns:
        str: ID dokumen yang baru dibuat (ObjectId sebagai string)

    Example:
        log_activity(
            user_id=1, username='student1',
            action=ACTION_VIEW_COURSE,
            course_id=5, course_name='Django Basics',
            metadata={'browser': 'Chrome', 'ip': '127.0.0.1'}
        )
    """
    collection = get_collection(COLLECTION_NAME)

    document = {
        'user_id': user_id,
        'username': username,
        'action': action,
        'timestamp': datetime.now(timezone.utc),
    }

    if course_id is not None:
        document['course_id'] = course_id

    if course_name is not None:
        document['course_name'] = course_name

    if metadata:
        document['metadata'] = metadata

    result = collection.insert_one(document)
    return str(result.inserted_id)


def get_user_activities(user_id: int, limit: int = 20) -> list:
    """
    Mengambil riwayat aktivitas seorang user, diurutkan terbaru dulu.

    Args:
        user_id: ID user
        limit: Jumlah maksimum dokumen yang dikembalikan (default 20)

    Returns:
        list of dict: Daftar aktivitas user
    """
    collection = get_collection(COLLECTION_NAME)

    cursor = collection.find(
        {'user_id': user_id},
        {'_id': 0}  # Exclude _id agar bisa di-serialize
    ).sort('timestamp', -1).limit(limit)

    return list(cursor)


def get_course_activities(course_id: int, limit: int = 50) -> list:
    """
    Mengambil semua aktivitas yang berkaitan dengan sebuah course.

    Args:
        course_id: ID course
        limit: Jumlah maksimum dokumen (default 50)

    Returns:
        list of dict: Daftar aktivitas pada course tersebut
    """
    collection = get_collection(COLLECTION_NAME)

    cursor = collection.find(
        {'course_id': course_id},
        {'_id': 0}
    ).sort('timestamp', -1).limit(limit)

    return list(cursor)


def get_all_activities(limit: int = 100) -> list:
    """
    Mengambil semua aktivitas terbaru (untuk admin dashboard).

    Args:
        limit: Jumlah maksimum dokumen (default 100)

    Returns:
        list of dict: Daftar semua aktivitas terbaru
    """
    collection = get_collection(COLLECTION_NAME)

    cursor = collection.find(
        {},
        {'_id': 0}
    ).sort('timestamp', -1).limit(limit)

    return list(cursor)
