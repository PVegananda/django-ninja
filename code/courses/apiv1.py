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
from django.http import HttpRequest, FileResponse
from courses.models import Course, CourseContent, CourseMember, Comment
from courses.schemas import (
    CourseIn, CourseOut, DetailCourseOut,
    CourseContentIn, CourseContentOut,
    Register, UserOut, CommentIn, CommentOut, CommentUpdate,
    CourseMemberOut, CourseUpdate, ContentUpdate
)
from courses.filters import CourseFilter, CourseContentFilter
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
    description="REST API untuk Simple Learning Management System - Modul 08 (Advanced API Features)"
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

    Query Parameters:
    - search: Cari berdasarkan nama course atau deskripsi (case-insensitive)
    - price: Tampilkan course dengan harga di atas nilai ini
    - created_at: Tampilkan course yang dibuat setelah tanggal tertentu
    - ordering: Urutan hasil (name, -name, price, -price, created_at, -created_at) (default: -created_at)
    - page: Nomor halaman (default: 1, per-page: 10)

    Contoh:
    - GET /api/v1/courses/
    - GET /api/v1/courses/?search=python
    - GET /api/v1/courses/?price=50000&ordering=-price
    - GET /api/v1/courses/?search=web&ordering=price&page=2

    Response dengan pagination:
    {
        "items": [
            {"id": 1, "name": "Belajar Python Dasar", "price": 75000, ...},
            ...
        ],
        "count": 15
    }
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


@apiv1.get('courses/{id}', response=DetailCourseOut, tags=["Courses"])
def detail_course(request, id: int):
    """
    Mengambil detail course beserta daftar kontennya.

    Path Parameters:
    - id: ID course yang akan diambil

    Response menampilkan:
    - Semua data course (name, description, price, teacher, etc)
    - List konten yang ada di course ini

    Contoh:
    - GET /api/v1/courses/1
    """
    course = get_object_or_404(Course, pk=id)
    return Course.objects.prefetch_related(
        'coursecontent_set'
    ).select_related('teacher').get(pk=id)


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


# ============================================================================# FILE UPLOAD ENDPOINTS - Modul 08
# ============================================================================

@apiv1.post('courses/{id}/upload-image/', auth=apiAuth, tags=["File Upload"])
def upload_course_image(request, id: int):
    """
    Upload gambar thumbnail untuk course.
    
    Hanya teacher pemilik course yang boleh mengupload gambar.
    
    Path Parameters:
    - id: ID course
    
    Form Parameters:
    - file: File gambar (JPEG, PNG, WebP)
    
    Validasi:
    - Ukuran maksimal: 2MB
    - Tipe file: image/jpeg, image/png, image/webp
    
    Response: {\"message\": \"Image berhasil diupload.\", \"filename\": \"...\"}
    
    Authentication: Wajib login (Bearer token)
    """
    # Get file from request
    if 'file' not in request.FILES:
        raise HttpError(400, "File tidak diberikan")
    
    file = request.FILES['file']
    user = User.objects.get(pk=request.user.id)
    course = get_object_or_404(Course, pk=id)
    
    # Validasi: hanya teacher pemilik course
    if course.teacher != user:
        raise HttpError(403, "Hanya teacher pemilik course yang boleh mengupload gambar")
    
    # Validasi ukuran file (maks 2MB)
    if file.size > 2 * 1024 * 1024:
        raise HttpError(400, "Ukuran file maksimal 2MB")
    
    # Validasi tipe file
    allowed_types = ['image/jpeg', 'image/png', 'image/webp']
    if file.content_type not in allowed_types:
        raise HttpError(400, "Tipe file harus JPEG, PNG, atau WebP")
    
    # Simpan file
    course.image = file
    course.save()
    
    return {"message": "Image berhasil diupload", "filename": file.name}


@apiv1.post('contents/{id}/upload-attachment/', auth=apiAuth, tags=["File Upload"])
def upload_content_attachment(request, id: int):
    """
    Upload file attachment (materi) untuk CourseContent.
    
    Hanya teacher pemilik course yang boleh mengupload attachment.
    
    Path Parameters:
    - id: ID course content
    
    Form Parameters:
    - file: File attachment (PDF, DOCX, PPTX, ZIP)
    
    Validasi:
    - Ukuran maksimal: 10MB
    - Tipe file: application/pdf, application/vnd.openxmlformats-officedocument.wordprocessingml.document, dll
    
    Response: {\"message\": \"Attachment berhasil diupload.\", \"filename\": \"...\"}
    
    Authentication: Wajib login (Bearer token)
    """
    # Get file from request
    if 'file' not in request.FILES:
        raise HttpError(400, "File tidak diberikan")
    
    file = request.FILES['file']
    user = User.objects.get(pk=request.user.id)
    content = get_object_or_404(CourseContent, pk=id)
    
    # Validasi: hanya teacher pemilik course
    if content.course_id.teacher != user:
        raise HttpError(403, "Hanya teacher pemilik course yang boleh mengupload attachment")
    
    # Validasi ukuran file (maks 10MB)
    if file.size > 10 * 1024 * 1024:
        raise HttpError(400, "Ukuran file maksimal 10MB")
    
    # Validasi tipe file
    allowed_types = [
        'application/pdf',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',  # .docx
        'application/vnd.openxmlformats-officedocument.presentationml.presentation',  # .pptx
        'application/zip',
    ]
    if file.content_type not in allowed_types:
        raise HttpError(400, f"Tipe file harus PDF, DOCX, PPTX, atau ZIP. Diterima: {file.content_type}")
    
    # Simpan file
    content.file_attachment = file
    content.save()
    
    return {"message": "Attachment berhasil diupload", "filename": file.name}


# ============================================================================
# FILE DOWNLOAD ENDPOINTS - Modul 08
# ============================================================================

@apiv1.get('contents/{id}/download/', auth=apiAuth, tags=["File Download"])
def download_attachment(request, id: int):
    """
    Download file attachment dari course content.
    
    Hanya member course yang boleh mendownload file.
    
    Path Parameters:
    - id: ID course content
    
    Response: File download dengan proper headers
    
    Authentication: Wajib login (Bearer token)
    """
    user = User.objects.get(pk=request.user.id)
    content = get_object_or_404(CourseContent, pk=id)
    
    # Validasi: user harus terdaftar sebagai member course
    is_member = CourseMember.objects.filter(
        course_id=content.course_id,
        user_id=user
    ).exists()
    
    # Allow course owner (teacher) to download their content
    is_course_owner = (content.course_id.teacher == user)
    
    if not (is_member or is_course_owner):
        raise HttpError(403, "Anda harus terdaftar di course ini untuk mendownload file")
    
    # Cek apakah file ada
    if not content.file_attachment:
        raise HttpError(404, "Content ini tidak memiliki file attachment")
    
    # Return file response
    filename = content.file_attachment.name.split('/')[-1]
    response = FileResponse(
        content.file_attachment.open(),
        as_attachment=True,
        filename=filename,
        content_type='application/octet-stream'
    )
    return response


# ============================================================================
# PARTIAL UPDATE ENDPOINTS (PATCH) - Modul 08
# ============================================================================

@apiv1.patch('courses/{id}/', response=CourseOut, auth=apiAuth, tags=["Courses"])
def patch_course(request, id: int, data: CourseUpdate):
    """
    Partial update course (PATCH method).
    
    Hanya pemilik course yang boleh mengupdate. Hanya field yang dikirim yang akan diubah.
    
    Path Parameters:
    - id: ID course yang akan diupdate
    
    Request Body (JSON):
    - name: (opsional) Nama course baru
    - description: (opsional) Deskripsi baru
    - price: (opsional) Harga baru
    
    Key difference from PUT:
    - PUT: harus mengirim SEMUA field (full replacement)
    - PATCH: hanya mengirim field yang ingin diubah (partial update)
    
    Contoh:
    - Hanya ubah harga: {\"price\": 50000}
    - Hanya ubah nama: {\"name\": \"Python Lanjut\"}
    - Ubah multiple fields: {\"name\": \"...\", \"price\": 75000}
    
    Field yang tidak dikirim TIDAK akan berubah (tetap nilai lama).
    
    Response: 200 OK dengan data course yang sudah diupdate
    Errors:
    - 403: User bukan pemilik course
    - 404: Course tidak ditemukan
    
    Authentication: Wajib login (Bearer token)
    """
    user = User.objects.get(pk=request.user.id)
    course = get_object_or_404(Course, pk=id)
    
    # Authorization check
    if course.teacher != user:
        raise HttpError(403, "Hanya pemilik course yang dapat mengedit")
    
    # Update only fields that were provided (exclude_unset=True)
    update_data = data.dict(exclude_unset=True)
    for attr, value in update_data.items():
        setattr(course, attr, value)
    
    course.save()
    return course


@apiv1.patch('contents/{id}/', response=CourseContentOut, auth=apiAuth, tags=["Course Content"])
def patch_content(request, id: int, data: ContentUpdate):
    """
    Partial update course content (PATCH method).
    
    Hanya pemilik course yang boleh mengupdate. Hanya field yang dikirim yang akan diubah.
    
    Path Parameters:
    - id: ID course content yang akan diupdate
    
    Request Body (JSON):
    - name: (opsional) Nama konten baru
    - description: (opsional) Deskripsi baru
    - video_url: (opsional) URL video baru
    
    Contoh:
    - Hanya update URL video: {\"video_url\": \"https://...\"}
    - Ubah nama dan deskripsi: {\"name\": \"Topik Baru\", \"description\": \"...\"}
    
    Field yang tidak dikirim TIDAK akan berubah.
    
    Response: 200 OK dengan data content yang sudah diupdate
    Errors:
    - 403: User bukan pemilik course parent
    - 404: Content tidak ditemukan
    
    Authentication: Wajib login (Bearer token)
    """
    user = User.objects.get(pk=request.user.id)
    content = get_object_or_404(CourseContent, pk=id)
    
    # Authorization check
    if content.course_id.teacher != user:
        raise HttpError(403, "Hanya pemilik course yang dapat mengedit konten")
    
    # Update only fields that were provided (exclude_unset=True)
    update_data = data.dict(exclude_unset=True)
    for attr, value in update_data.items():
        setattr(content, attr, value)
    
    content.save()
    return content


# ============================================================================# TEST ENDPOINT
# ============================================================================

@apiv1.get('hello/', tags=["Test"])
def hello_api(request):
    """Test endpoint untuk memastikan API berjalan dengan baik."""
    return "Menyala abangkuh ..."