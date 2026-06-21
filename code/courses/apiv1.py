"""
REST API v1 untuk Simple LMS menggunakan Django Ninja

Features:
- Type-safe dengan Python type hints
- Automatic Pydantic validation
- Auto-generated Swagger UI documentation
- CRUD operations untuk Course dan CourseContent
- Error handling dengan HttpError
- Query parameters untuk filtering & searching
- JWT Authentication dengan ninja-simple-jwt (Modul 07)
"""

from ninja import NinjaAPI, Query
from ninja.errors import HttpError
from ninja.pagination import paginate, PageNumberPagination
from django_ratelimit.decorators import ratelimit
from ninja_simple_jwt.auth.views.api import mobile_auth_router
from ninja_simple_jwt.auth.ninja_auth import HttpJwtAuth
from django.contrib.auth.models import User
from django.core.cache import cache  # Django Cache Framework (Redis)
from courses.models import Course, CourseContent, CourseMember, Comment
from courses.schemas import (
    CourseIn, CourseOut, DetailCourseOut,
    CourseContentIn, CourseContentOut,
    Register, UserOut, CommentIn, CommentOut, CommentUpdate,
    CourseMemberOut
)
from courses.filters import CourseFilter, CourseContentFilter
from utils.redis_client import update_course_popularity, get_top_courses, init_course_popularity
from analytics.activity_service import (
    log_activity, ACTION_VIEW_COURSE, ACTION_ENROLL
)  # MongoDB activity logging (Modul 11)
from courses.tasks import send_enrollment_notification  # Celery task (Modul 12)
from typing import List

# ============================================================================
# Rate Limiting
# ============================================================================

"""
Rate limiting menggunakan django-ratelimit decorator.

Format: @ratelimit(key='ip|user', rate='<count>/<period>', method='GET|POST|...', block=True)

Periods: s, m, h, d
Examples:
- '5/m'   = 5 requests per minute
- '100/h' = 100 requests per hour
- '10/d'  = 10 requests per day

Key types:
- 'ip':    Rate limit berdasarkan IP address (untuk anonymous users)
- 'user':  Rate limit berdasarkan user ID (untuk authenticated users)
"""

# ============================================================================
# API Instance
# ============================================================================

apiv1 = NinjaAPI(
    title="Simple LMS API",
    version="1.0.0",
    description="REST API untuk Simple Learning Management System - Modul 10 (NoSQL Redis)"
)

# Register authentication router dari ninja-simple-jwt
# Ini menyediakan endpoint:
#   - POST /api/v1/auth/sign-in  (login & mendapatkan token)
#   - POST /api/v1/auth/token-refresh (refresh access token)
apiv1.add_router("/auth/", mobile_auth_router)

# Inisialisasi JWT auth handler
# Digunakan sebagai parameter auth=apiAuth pada endpoint yang butuh authentication
apiAuth = HttpJwtAuth()


# ============================================================================
# Helper Functions
# ============================================================================

def get_object_or_404(model, **kwargs):
    """
    Mengambil satu object dari database.
    Raise HttpError 404 jika tidak ditemukan.
    
    Usage:
        course = get_object_or_404(Course, pk=id)
    """
    try:
        return model.objects.get(**kwargs)
    except model.DoesNotExist:
        model_name = model.__name__
        raise HttpError(404, f"{model_name} tidak ditemukan")


# ============================================================================
# AUTHENTICATION ENDPOINTS
# ============================================================================

@ratelimit(key='ip', rate='5/m', method='POST', block=True)
@apiv1.post('register/', response={201: UserOut}, tags=["Authentication"])
def register(request, data: Register):
    """
    Membuat akun user baru (registrasi).
    
    Rate limited dengan 5 attempts per minute untuk mencegah abuse dan brute force attack.

    Request body:
    - username: Username unik (wajib)
    - password: Password (akan di-hash otomatis) (wajib)
    - email: Email unik (wajib)
    - first_name: Nama depan (wajib)
    - last_name: Nama belakang (wajib)
    
    Response: Data user baru (tanpa password)
    Errors:
    - 400: Username atau email sudah digunakan
    - 429: Terlalu banyak request (rate limit)
    """
    # Cek apakah username sudah digunakan
    if User.objects.filter(username=data.username).exists():
        raise HttpError(400, "Username sudah digunakan")
    
    # Cek apakah email sudah digunakan
    if User.objects.filter(email=data.email).exists():
        raise HttpError(400, "Email sudah digunakan")
    
    # Buat user baru
    # create_user() otomatis melakukan hashing pada password
    new_user = User.objects.create_user(
        username=data.username,
        password=data.password,
        email=data.email,
        first_name=data.first_name,
        last_name=data.last_name
    )
    
    return 201, new_user


# ============================================================================
# COURSE ENDPOINTS - CRUD Operations
# ============================================================================

@apiv1.get('courses/', response=List[CourseOut], tags=["Courses"])
@paginate(PageNumberPagination, page_size=10)
def list_courses(
    request,
    filters: CourseFilter = Query(...),
    ordering: str = '-created_at',
):
    """
    Mengambil daftar semua course dengan filtering, sorting, dan pagination.

    Menggunakan Cache-Aside pattern:
    - Cache key: 'courses_list' (default ordering, no filters)
    - TTL: 5 menit
    - Cache di-invalidasi saat create/update/delete course

    Query Parameters:
    - search: Cari berdasarkan nama course atau deskripsi (case-insensitive)
    - price: Tampilkan course dengan harga di atas nilai ini
    - created_at: Tampilkan course yang dibuat setelah tanggal tertentu
    - ordering: Urutan hasil (name, -name, price, -price, created_at, -created_at) (default: -created_at)
    - page: Nomor halaman (default: 1, per-page: 10)
    """
    # Whitelist field yang boleh digunakan untuk sorting
    allowed_fields = ['name', 'price', 'created_at', '-name', '-price', '-created_at']
    if ordering not in allowed_fields:
        ordering = '-created_at'

    # Query dengan select_related untuk optimasi
    qs = Course.objects.select_related('teacher').all()

    # Terapkan filter
    qs = filters.filter(qs)

    # Terapkan sorting
    qs = qs.order_by(ordering)

    return qs


@apiv1.get('courses/popular/', response=list, tags=["Courses"])
def popular_courses(request):
    """
    Menampilkan top 10 course terpopuler berdasarkan jumlah enrollment.

    Menggunakan Redis Sorted Set (ZREVRANGE) untuk mendapatkan ranking
    course berdasarkan score (jumlah enrollment).

    Response: List of {course_id, name, enrollment_count}
    """
    top = get_top_courses(limit=10)
    result = []
    for member, score in top:
        # member format: 'course:ID'
        course_id = int(member.split(':')[1])
        try:
            course = Course.objects.get(pk=course_id)
            result.append({
                'course_id': course_id,
                'name': course.name,
                'enrollment_count': int(score)
            })
        except Course.DoesNotExist:
            pass
    return result


@apiv1.get('courses/{id}', response=DetailCourseOut, tags=["Courses"])
def detail_course(request, id: int):
    """
    Mengambil detail course beserta daftar kontennya.

    Menggunakan Cache-Aside pattern:
    - Cache key: 'course_detail:{id}'
    - TTL: 5 menit
    - Cache di-invalidasi saat update/delete course

    Path Parameters:
    - id: ID course yang akan diambil
    """
    # Cache-Aside: cek cache dulu
    cache_key = f'course_detail:{id}'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    # Cache miss - query database
    course = get_object_or_404(Course, pk=id)
    result = Course.objects.prefetch_related(
        'coursecontent_set'
    ).select_related('teacher').get(pk=id)

    # Simpan ke cache (TTL 5 menit)
    cache.set(cache_key, result, timeout=300)

    # Log aktivitas ke MongoDB (silent - tidak memblokir response jika error)
    try:
        if hasattr(request, 'user') and request.user and request.user.is_authenticated:
            log_activity(
                user_id=request.user.id,
                username=request.user.username,
                action=ACTION_VIEW_COURSE,
                course_id=id,
                course_name=result.name,
                metadata={'source': 'api_v1'}
            )
    except Exception:
        pass  # MongoDB error tidak boleh merusak response utama

    return result


@apiv1.post('courses/', response={201: CourseOut}, auth=apiAuth, tags=["Courses"])
def create_course(request, data: CourseIn):
    """
    Membuat course baru.
    
    Hanya user yang sudah login yang bisa membuat course.
    User yang membuat otomatis menjadi teacher dari course ini.

    Request Body (JSON):
    {
        "name": "Pemrograman Web",
        "description": "Belajar membuat aplikasi web dengan Django",
        "price": 50000
    }

    Response: 201 Created dengan data course yang dibuat
    
    Authentication: Wajib login (Bearer token)
    """
    if data.price < 0:
        raise HttpError(400, "Harga tidak boleh negatif")

    # Ambil user dari request (sudah terautentikasi)
    teacher = User.objects.get(pk=request.user.id)

    course = Course.objects.create(**data.dict(), teacher=teacher)

    # Write-Through: invalidasi cache list karena ada data baru
    cache.delete('courses_list')

    # Inisialisasi leaderboard dengan score 0
    init_course_popularity(course.id, 0)

    return 201, course


@apiv1.put('courses/{id}', response=CourseOut, auth=apiAuth, tags=["Courses"])
def update_course(request, id: int, data: CourseIn):
    """
    Mengupdate data course secara keseluruhan (PUT).
    
    Hanya pemilik course yang boleh mengedit.

    Path Parameters:
    - id: ID course yang akan diupdate

    Request Body (JSON):
    {
        "name": "Pemrograman Web Lanjut",
        "description": "Belajar Django advanced",
        "price": 75000
    }

    Response: 200 OK dengan data course yang sudah diupdate
    Errors:
    - 403: User bukan pemilik course
    - 404: Course tidak ditemukan
    
    Authentication: Wajib login (Bearer token)
    """
    if data.price < 0:
        raise HttpError(400, "Harga tidak boleh negatif")

    user = User.objects.get(pk=request.user.id)
    course = get_object_or_404(Course, pk=id)
    
    # Authorization check: hanya course owner yang boleh edit
    if course.teacher != user:
        raise HttpError(403, "Hanya pemilik course yang dapat mengedit")

    for attr, value in data.dict().items():
        setattr(course, attr, value)
    course.save()

    # Write-Through: invalidasi cache list dan detail
    cache.delete('courses_list')
    cache.delete(f'course_detail:{id}')

    return course


@apiv1.delete('courses/{id}', response={204: None}, auth=apiAuth, tags=["Courses"])
def delete_course(request, id: int):
    """
    Menghapus course.
    
    Hanya pemilik course dan superadmin yang boleh menghapus.

    Path Parameters:
    - id: ID course yang akan dihapus

    Response: 204 No Content (tanpa body)
    Errors:
    - 403: User tidak memiliki izin untuk menghapus
    - 404: Course tidak ditemukan
    
    Authentication: Wajib login (Bearer token)
    """
    user = User.objects.get(pk=request.user.id)
    course = get_object_or_404(Course, pk=id)
    
    # Authorization check: course owner ATAU superadmin
    if course.teacher != user and not user.is_superuser:
        raise HttpError(403, "Anda tidak memiliki izin untuk menghapus course ini")

    try:
        course.delete()
        # Write-Through: invalidasi semua cache terkait course
        cache.delete('courses_list')
        cache.delete(f'course_detail:{id}')
        return 204, None
    except Exception:
        raise HttpError(
            400,
            "Course tidak bisa dihapus karena masih memiliki member atau konten"
        )


@apiv1.post('course/{id}/enroll/', auth=apiAuth, response=CourseMemberOut, tags=["Courses"])
def course_enrollment(request, id: int):
    """
    Mendaftarkan user saat ini ke sebuah course.
    
    User akan mendapatkan role 'std' (student) secara default.

    Path Parameters:
    - id: ID course yang akan diikuti

    Response: Data enrollment (CourseMember) yang baru dibuat
    Errors:
    - 400: User sudah terdaftar di course ini
    - 404: Course tidak ditemukan
    
    Authentication: Wajib login (Bearer token)
    """
    user = User.objects.get(pk=request.user.id)
    course = get_object_or_404(Course, pk=id)
    
    # Cek apakah sudah terdaftar
    if CourseMember.objects.filter(user_id=user, course_id=course).exists():
        raise HttpError(400, "Anda sudah terdaftar di course ini")
    
    enrollment = CourseMember.objects.create(
        user_id=user,
        course_id=course,
        roles='std'  # Default role: student
    )

    # Update leaderboard popularity score saat ada enrollment baru
    update_course_popularity(id, score_increment=1)

    # Log aktivitas enrollment ke MongoDB (silent)
    try:
        log_activity(
            user_id=user.id,
            username=user.username,
            action=ACTION_ENROLL,
            course_id=id,
            course_name=course.name,
            metadata={'source': 'api_v1'}
        )
    except Exception:
        pass  # MongoDB error tidak boleh merusak response utama

    # Kirim notifikasi enrollment via Celery (asynchronous, non-blocking)
    # User langsung dapat response tanpa menunggu email terkirim
    try:
        send_enrollment_notification.delay(user.id, id)
    except Exception:
        pass  # Celery error tidak boleh merusak response utama

    return enrollment


@apiv1.get('mycourses/', auth=apiAuth, response=List[CourseMemberOut], tags=["Courses"])
def get_my_courses(request):
    """
    Mengambil daftar course yang diikuti oleh user saat ini.
    
    Menampilkan semua course yang sudah di-enroll dengan role user
    di setiap course.

    Response: List CourseMember berisi data course yang diikuti
    
    Authentication: Wajib login (Bearer token)
    """
    user = User.objects.get(pk=request.user.id)
    mycourses = CourseMember.objects.filter(
        user_id=user
    ).select_related('course_id', 'user_id')
    return mycourses


# ============================================================================
# COURSE CONTENT ENDPOINTS - CRUD Operations
# ============================================================================

@apiv1.get('contents/', response=List[CourseContentOut], tags=["Contents"])
def list_contents(
    request,
    course_id: int = None,
    search: str = None,
    ordering: str = '-created_at',
):
    """
    Mengambil daftar course content dengan filter opsional.

    Query Parameters:
    - course_id: Filter berdasarkan ID course
    - search: Cari berdasarkan nama content
    - ordering: Urutan (default: -created_at = terbaru)

    Contoh:
    - GET /api/v1/contents/?course_id=1
    - GET /api/v1/contents/?search=Django&ordering=name
    """
    qs = CourseContent.objects.all()

    if course_id is not None:
        qs = qs.filter(course_id_id=course_id)
    if search:
        qs = qs.filter(name__icontains=search)

    return qs.order_by(ordering)


@apiv1.get('contents/{id}', response=CourseContentOut, tags=["Contents"])
def detail_content(request, id: int):
    """
    Mengambil detail satu course content.

    Path Parameters:
    - id: ID course content yang akan diambil
    """
    return get_object_or_404(CourseContent, pk=id)


@apiv1.post('contents/', response={201: CourseContentOut}, auth=apiAuth, tags=["Contents"])
def create_content(request, data: CourseContentIn):
    """
    Membuat course content baru.
    
    Hanya pemilik course yang boleh membuat content di course-nya.

    Request Body (JSON):
    {
        "name": "Pengenalan Django",
        "description": "Materi dasar Django",
        "video_url": "https://youtube.com/watch?v=...",
        "course_id": 1,
        "parent_id": null
    }

    Response: 201 Created dengan data content yang dibuat
    Errors:
    - 403: User bukan pemilik course
    - 404: Course atau parent content tidak ditemukan
    
    Authentication: Wajib login (Bearer token)
    """
    user = User.objects.get(pk=request.user.id)
    course = get_object_or_404(Course, pk=data.course_id)
    
    # Authorization: hanya course owner yang boleh membuat content
    if course.teacher != user:
        raise HttpError(403, "Hanya pemilik course yang dapat membuat content")

    if data.parent_id:
        get_object_or_404(CourseContent, pk=data.parent_id)

    # Convert course_id dan parent_id to use Django's ForeignKey naming (_id suffix)
    content_data = data.dict()
    if content_data.get('course_id'):
        content_data['course_id_id'] = content_data.pop('course_id')
    if content_data.get('parent_id'):
        content_data['parent_id_id'] = content_data.pop('parent_id')
    
    content = CourseContent.objects.create(**content_data)
    return 201, content


@apiv1.put('contents/{id}', response=CourseContentOut, auth=apiAuth, tags=["Contents"])
def update_content(request, id: int, data: CourseContentIn):
    """
    Mengupdate data course content secara keseluruhan (PUT).
    
    Hanya pemilik course yang boleh mengedit content.

    Path Parameters:
    - id: ID course content yang akan diupdate

    Request Body (JSON):
    {
        "name": "Django Basics - Updated",
        "description": "Materi dasar Django yang sudah diperbaharui",
        "video_url": "https://youtube.com/watch?v=...",
        "course_id": 1,
        "parent_id": null
    }

    Response: 200 OK dengan data content yang sudah diupdate
    Errors:
    - 403: User bukan pemilik course
    - 404: Content atau course tidak ditemukan
    
    Authentication: Wajib login (Bearer token)
    """
    user = User.objects.get(pk=request.user.id)
    course = get_object_or_404(Course, pk=data.course_id)
    
    # Authorization: hanya course owner yang boleh edit content
    if course.teacher != user:
        raise HttpError(403, "Hanya pemilik course yang dapat mengedit content")

    if data.parent_id:
        get_object_or_404(CourseContent, pk=data.parent_id)

    content = get_object_or_404(CourseContent, pk=id)

    # Handle ForeignKey field naming
    update_data = data.dict()
    if update_data.get('course_id'):
        update_data['course_id_id'] = update_data.pop('course_id')
    if update_data.get('parent_id'):
        update_data['parent_id_id'] = update_data.pop('parent_id')
    
    for attr, value in update_data.items():
        setattr(content, attr, value)
    content.save()

    return content


@apiv1.delete('contents/{id}', response={204: None}, auth=apiAuth, tags=["Contents"])
def delete_content(request, id: int):
    """
    Menghapus course content.
    
    Bisa dihapus oleh:
    - Pemilik course (teacher)
    - Superadmin

    Path Parameters:
    - id: ID course content yang akan dihapus

    Response: 204 No Content
    Errors:
    - 403: User tidak memiliki izin untuk menghapus
    - 404: Content tidak ditemukan
    
    Authentication: Wajib login (Bearer token)
    """
    user = User.objects.get(pk=request.user.id)
    content = CourseContent.objects.select_related('course_id').filter(id=id).first()
    
    if content is None:
        raise HttpError(404, "Content tidak ditemukan")
    
    # Authorization: course owner ATAU superadmin
    course = content.course_id
    if course.teacher != user and not user.is_superuser:
        raise HttpError(403, "Anda tidak memiliki izin untuk menghapus content ini")

    try:
        content.delete()
        return 204, None
    except Exception:
        raise HttpError(400, "Content tidak bisa dihapus")


# ============================================================================
# COMMENT ENDPOINTS - with Authorization
# ============================================================================

@apiv1.post('comments/', auth=apiAuth, response=dict, tags=["Comments"])
def post_comment(request, data: CommentIn):
    """
    Membuat komentar pada course content.
    
    Hanya user yang terdaftar (enrolled) di course ini yang boleh komentar.

    Request Body:
    {
        "comment": "Konten ini sangat bermanfaat!",
        "content_id": 1
    }

    Response: Success message
    Errors:
    - 403: User tidak terdaftar di course ini
    - 404: Content tidak ditemukan
    
    Authentication: Wajib login (Bearer token)
    """
    user = User.objects.get(pk=request.user.id)
    content = CourseContent.objects.filter(id=data.content_id).first()
    
    if content is None:
        raise HttpError(404, "Content tidak ditemukan")
    
    # Authorization check: apakah user terdaftar di course ini?
    course_member = CourseMember.objects.filter(
        user_id=user,
        course_id=content.course_id
    )
    
    if course_member.exists():
        Comment.objects.create(
            comment=data.comment,
            user_id=user,
            content_id=content
        )
        return {"message": "Komentar berhasil ditambahkan"}
    else:
        raise HttpError(403, "Anda tidak terdaftar di course ini")


@apiv1.put('comments/{id}', auth=apiAuth, response=dict, tags=["Comments"])
def update_comment(request, id: int, data: CommentUpdate):
    """
    Mengupdate komentar.
    
    Hanya pemilik komentar yang boleh mengedit.

    Path Parameters:
    - id: ID komentar yang akan diupdate

    Request Body:
    {
        "comment": "Konten ini sangat bermanfaat! Terimakasih!"
    }

    Response: Success message
    Errors:
    - 403: User bukan pemilik komentar
    - 404: Komentar tidak ditemukan
    
    Authentication: Wajib login (Bearer token)
    """
    user = User.objects.get(pk=request.user.id)
    comment = Comment.objects.filter(id=id).first()
    
    if comment is None:
        raise HttpError(404, "Komentar tidak ditemukan")
    
    # Authorization check: apakah user adalah pemilik komentar?
    if comment.user_id != user:
        raise HttpError(403, "Anda tidak memiliki izin untuk mengedit komentar ini")
    
    comment.comment = data.comment
    comment.save()
    return {"message": "Komentar berhasil diperbarui"}


@apiv1.delete('comments/{id}', auth=apiAuth, response={204: None}, tags=["Comments"])
def delete_comment(request, id: int):
    """
    Menghapus komentar.
    
    Bisa dihapus oleh:
    - Pemilik komentar
    - Pemilik course (teacher)
    - Superadmin

    Path Parameters:
    - id: ID komentar yang akan dihapus

    Response: 204 No Content
    Errors:
    - 403: User tidak memiliki izin untuk menghapus
    - 404: Komentar tidak ditemukan
    
    Authentication: Wajib login (Bearer token)
    """
    user = User.objects.get(pk=request.user.id)
    comment = Comment.objects.select_related('content_id__course_id').filter(id=id).first()
    
    if comment is None:
        raise HttpError(404, "Komentar tidak ditemukan")
    
    # Cek apakah user adalah pemilik komentar
    is_comment_owner = (comment.user_id == user)
    
    # Cek apakah user adalah pemilik course
    course = comment.content_id.course_id
    is_course_owner = (course.teacher == user)
    
    # Cek apakah user adalah superadmin
    is_superadmin = user.is_superuser
    
    if is_comment_owner or is_course_owner or is_superadmin:
        comment.delete()
        return 204, None
    else:
        raise HttpError(403, "Anda tidak memiliki izin untuk menghapus komentar ini")


# ============================================================================
# SESSION ENDPOINTS - Course Visit History (Redis Session)
# ============================================================================

@apiv1.post('courses/{id}/visit/', auth=apiAuth, tags=["Session"])
def visit_course(request, id: int):
    """
    Mencatat kunjungan user ke halaman course.

    Menggunakan Django session (disimpan di Redis) untuk tracking kunjungan.
    Data disimpan per-user dan expire sesuai SESSION_COOKIE_AGE (24 jam).

    Path Parameters:
    - id: ID course yang dikunjungi

    Response: Daftar course yang sudah dikunjungi

    Authentication: Wajib login (Bearer token)
    """
    # Pastikan course ada
    get_object_or_404(Course, pk=id)

    # Ambil daftar course yang sudah dikunjungi dari session
    visited = request.session.get('visited_courses', [])

    if id not in visited:
        visited.append(id)
        request.session['visited_courses'] = visited
        request.session.modified = True

    return {
        "course_id": id,
        "total_visited": len(visited),
        "visited_courses": visited
    }


@apiv1.get('my-history/', auth=apiAuth, tags=["Session"])
def get_visit_history(request):
    """
    Mengambil histori kunjungan course dari session user saat ini.

    Data diambil dari Redis session yang sudah dikonfigurasi.
    Session expire setelah 24 jam (SESSION_COOKIE_AGE).

    Response:
    - total_visited: Jumlah course yang pernah dikunjungi
    - visited_courses: List ID course yang pernah dikunjungi

    Authentication: Wajib login (Bearer token)
    """
    visited = request.session.get('visited_courses', [])
    return {
        "total_visited": len(visited),
        "visited_courses": visited
    }


# ============================================================================
# TEST ENDPOINT
# ============================================================================

@apiv1.get('hello/', tags=["Test"])
def hello_api(request):
    """Test endpoint untuk memastikan API berjalan dengan baik."""
    return "Menyala abangkuh ..."


# ============================================================================
# CELERY TASK ENDPOINTS - Modul 12: Message Brokers
# ============================================================================

@apiv1.post('reports/generate/{course_id}/', auth=apiAuth, tags=["Reports"])
def generate_report(request, course_id: int):
    """
    Trigger pembuatan report course secara asynchronous.

    Report akan dibuat di background oleh Celery Worker.
    Client mendapatkan task_id untuk melakukan polling status.

    Path Parameters:
    - course_id: ID course yang akan di-generate reportnya

    Response:
    - task_id: UUID untuk cek status report
    - status: 'processing' (langsung, tidak menunggu selesai)

    Authentication: Wajib login (Bearer token)

    Flow:
    1. POST /api/v1/reports/generate/1/  → dapat task_id
    2. GET  /api/v1/reports/status/{task_id}/  → polling hingga SUCCESS
    """
    course = get_object_or_404(Course, pk=course_id)

    # Import task di sini untuk menghindari circular import saat startup
    from courses.tasks import generate_course_report

    # Kirim task ke Celery (non-blocking)
    task = generate_course_report.delay(course_id)

    return {
        'task_id': task.id,
        'status': 'processing',
        'message': f"Report untuk course '{course.name}' sedang dibuat di background.",
        'check_status_url': f"/api/v1/reports/status/{task.id}/"
    }


@apiv1.get('reports/status/{task_id}/', tags=["Reports"])
def report_status(request, task_id: str):
    """
    Cek status Celery task report generation.

    Gunakan endpoint ini untuk polling setelah memanggil
    POST /api/v1/reports/generate/{course_id}/.

    Path Parameters:
    - task_id: UUID task yang didapat dari endpoint generate

    Response:
    - status: PENDING | STARTED | SUCCESS | FAILURE | RETRY
    - result: Data report (hanya ada jika status SUCCESS)
    - message: Info tambahan (saat masih PENDING/STARTED)

    Status Lifecycle:
        PENDING → STARTED → SUCCESS (atau FAILURE)
    """
    from celery.result import AsyncResult

    result = AsyncResult(task_id)

    response = {
        'task_id': task_id,
        'status': result.status,
    }

    if result.ready():
        if result.successful():
            response['result'] = result.result
        else:
            # Jika gagal, tampilkan pesan error
            response['error'] = str(result.result)
    else:
        response['message'] = 'Task masih dalam proses, coba lagi beberapa saat...'

    return response