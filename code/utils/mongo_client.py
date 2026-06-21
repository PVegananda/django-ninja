# utils/mongo_client.py
"""
MongoDB Client untuk Simple LMS Analytics.

Menyediakan koneksi dan fungsi utility untuk menyimpan dan mengambil
data analytics dari MongoDB. MongoDB digunakan sebagai pelengkap PostgreSQL
untuk menyimpan data semi-structured seperti activity logs.

Arsitektur:
    PostgreSQL  → Data utama (users, courses, enrollments)
    Redis       → Caching & session
    MongoDB     → Analytics & activity logs (modul ini)
"""
import os
from datetime import datetime, timezone
from pymongo import MongoClient

# URI koneksi dari environment variable (diset di docker-compose.yml)
# Fallback ke localhost jika tidak ada (misalnya untuk testing lokal)
MONGO_URI = os.environ.get(
    "MONGO_URI",
    "mongodb://admin:password123@localhost:27017/lms_analytics?authSource=admin"
)

# Lazy singleton connection - koneksi dibuat satu kali, digunakan berulang
_client = None
_db = None


def get_mongo_db():
    """
    Mengembalikan instance database MongoDB (singleton pattern).
    Koneksi dibuat saat pertama kali dipanggil (lazy initialization).

    Returns:
        pymongo.database.Database: Instance database 'lms_analytics'
    """
    global _client, _db
    if _client is None:
        _client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        _db = _client['lms_analytics']
    return _db


def get_collection(collection_name: str):
    """
    Helper untuk mengambil collection dari database.

    Args:
        collection_name: Nama collection (misal: 'activity_logs', 'course_stats')

    Returns:
        pymongo.collection.Collection
    """
    db = get_mongo_db()
    return db[collection_name]
