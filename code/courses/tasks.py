# courses/tasks.py
"""
Celery Tasks untuk Simple LMS.

Semua task didefinisikan dengan @shared_task agar dapat digunakan
tanpa mengimport langsung instance Celery app (menghindari circular import).

Rules:
- Parameter task HARUS berupa tipe JSON-serializable (int, str, list, dict)
- Jangan kirim Django model object sebagai parameter - kirim ID-nya saja
- Import model di DALAM fungsi task untuk menghindari circular import
"""
from celery import shared_task
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# Task: Enrollment Notification
# =============================================================================

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_enrollment_notification(self, user_id: int, course_id: int):
    """
    Kirim email notifikasi saat user mendaftar ke course.

    Dijalankan secara asynchronous sehingga user tidak perlu menunggu.
    Menggunakan retry mechanism: gagal → coba lagi setelah 60 detik
    (maksimal 3 kali percobaan).

    Args:
        user_id: ID user yang mendaftar (int, bukan object)
        course_id: ID course yang didaftar (int, bukan object)

    Returns:
        str: Pesan hasil pengiriman notifikasi
    """
    try:
        from django.contrib.auth.models import User
        from courses.models import Course

        user = User.objects.get(pk=user_id)
        course = Course.objects.get(pk=course_id)

        # Simulasi pengiriman email (di production gunakan django.core.mail.send_mail)
        logger.info(f"[Celery] Sending enrollment notification to {user.email}")
        logger.info(f"[Celery] Subject: Enrollment Confirmation - {course.name}")
        logger.info(f"[Celery] Body: Halo {user.first_name or user.username}, "
                    f"Anda berhasil mendaftar di course '{course.name}'.")

        # Contoh implementasi nyata:
        # from django.core.mail import send_mail
        # send_mail(
        #     subject=f"Enrollment: {course.name}",
        #     message=f"Halo {user.first_name}, Anda berhasil mendaftar di '{course.name}'.",
        #     from_email="noreply@lms.ac.id",
        #     recipient_list=[user.email],
        # )

        return f"Notification sent to {user.email} for course '{course.name}'"

    except Exception as exc:
        logger.error(f"[Celery] send_enrollment_notification failed: {exc}")
        raise self.retry(exc=exc)


# =============================================================================
# Task: Course Report Generation
# =============================================================================

@shared_task(bind=True, max_retries=2, default_retry_delay=30)
def generate_course_report(self, course_id: int):
    """
    Generate laporan statistik untuk sebuah course.

    Task ini bisa memakan waktu lama tergantung jumlah data,
    sehingga dijalankan secara asynchronous.

    Args:
        course_id: ID course yang akan di-generate reportnya

    Returns:
        dict: Laporan statistik course
    """
    try:
        from courses.models import Course, CourseMember, CourseContent, Comment

        course = Course.objects.get(pk=course_id)
        members_count = CourseMember.objects.filter(course_id=course).count()
        contents_count = CourseContent.objects.filter(course_id=course).count()
        comments_count = Comment.objects.filter(
            content_id__course_id=course
        ).count()

        report = {
            'course_id': course_id,
            'course_name': course.name,
            'total_members': members_count,
            'total_contents': contents_count,
            'total_comments': comments_count,
            'generated_at': datetime.now().isoformat(),
        }

        logger.info(f"[Celery] Report generated for course '{course.name}': {report}")

        # Opsional: simpan ke MongoDB untuk riwayat report
        # try:
        #     from utils.mongo_client import get_collection
        #     collection = get_collection('course_reports')
        #     collection.insert_one(report)
        # except Exception:
        #     pass  # MongoDB error tidak memblokir report

        return report

    except Exception as exc:
        logger.error(f"[Celery] generate_course_report failed for course {course_id}: {exc}")
        raise self.retry(exc=exc)


# =============================================================================
# Task: Periodic - Generate Daily Stats (Celery Beat)
# =============================================================================

@shared_task
def generate_daily_stats():
    """
    Generate statistik harian LMS.

    Dijadwalkan oleh Celery Beat untuk berjalan setiap hari pukul 00:00 WIB.
    Konfigurasi jadwal ada di settings.py (CELERY_BEAT_SCHEDULE).

    Returns:
        dict: Statistik hari ini
    """
    from django.contrib.auth.models import User
    from courses.models import Course, CourseMember

    total_courses = Course.objects.count()
    total_users = User.objects.count()
    total_enrollments = CourseMember.objects.count()

    stats = {
        'date': datetime.now().date().isoformat(),
        'total_courses': total_courses,
        'total_users': total_users,
        'total_enrollments': total_enrollments,
        'generated_at': datetime.now().isoformat(),
    }

    logger.info(f"[Celery Beat] Daily stats: {stats}")
    return stats


# =============================================================================
# Task: Periodic - Cleanup Old Logs (Celery Beat)
# =============================================================================

@shared_task
def cleanup_old_logs():
    """
    Hapus activity logs MongoDB yang sudah lebih dari 30 hari.

    Dijadwalkan oleh Celery Beat untuk berjalan setiap hari pukul 02:00 WIB.
    Konfigurasi jadwal ada di settings.py (CELERY_BEAT_SCHEDULE).

    Returns:
        dict: Informasi cleanup yang dilakukan
    """
    threshold = datetime.now() - timedelta(days=30)

    deleted_count = 0
    try:
        from utils.mongo_client import get_collection
        collection = get_collection('activity_logs')
        result = collection.delete_many({
            'timestamp': {'$lt': threshold}
        })
        deleted_count = result.deleted_count
        logger.info(f"[Celery Beat] Cleaned {deleted_count} old activity logs "
                    f"before {threshold.date()}")
    except Exception as e:
        logger.warning(f"[Celery Beat] MongoDB cleanup error (non-fatal): {e}")

    return {
        'cleaned_before': threshold.date().isoformat(),
        'deleted_count': deleted_count,
    }
