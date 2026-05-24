"""
REST API v2 untuk Simple LMS menggunakan Django Ninja

API v2 menyediakan response yang lebih detail dibandingkan v1:

Perbedaan v1 vs v2:
- Course.teacher: string (username) → object dengan id, username, full_name
- Ditambahkan field: member_count, created_at, updated_at untuk Course
- Ditambahkan field item_count untuk CourseContent

Strategi versioning: URL Path Versioning
- v1: /api/v1/...
- v2: /api/v2/...

Keuntungan:
- Client dapat memilih versi API
- Backward compatibility terjaga
- Mudah untuk migrasi ke versi baru
"""

from ninja import NinjaAPI
from django.db.models import Count
from ninja_simple_jwt.auth.ninja_auth import HttpJwtAuth
from ninja.errors import HttpError
from django.contrib.auth.models import User
from courses.models import Course, CourseContent, CourseMember, Comment
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

# ============================================================================
# API v2 Instance
# ============================================================================

apiv2 = NinjaAPI(
    version="2.0.0",
    urls_namespace='v2',
    title="Simple LMS API v2",
    description="REST API v2 untuk Simple Learning Management System - Enhanced with detailed responses"
)

# Inisialisasi JWT auth handler
apiAuth = HttpJwtAuth()


# ============================================================================
# Response Schemas untuk API v2 (Enhanced)
# ============================================================================

class UserOutV2(BaseModel):
    """User schema dengan informasi lengkap user"""
    id: int
    username: str
    email: str
    first_name: str
    last_name: str
    
    class Config:
        from_attributes = True


class CourseOutV2(BaseModel):
    """Course schema v2 dengan teacher sebagai object dan member_count"""
    id: int
    name: str
    description: str
    price: int
    teacher: UserOutV2
    member_count: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class CourseContentOutV2(BaseModel):
    """CourseContent schema v2 dengan item_count"""
    id: int
    name: str
    description: str
    video_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class DetailCourseOutV2(BaseModel):
    """Detail course dengan list konten"""
    id: int
    name: str
    description: str
    price: int
    teacher: UserOutV2
    member_count: int
    contents_count: int  # Jumlah konten di course ini
    created_at: datetime
    updated_at: datetime
    contents: List[CourseContentOutV2]
    
    class Config:
        from_attributes = True


# ============================================================================
# Helper Functions
# ============================================================================

def get_object_or_404(model, **kwargs):
    """Mengambil satu object atau raise HttpError 404"""
    try:
        return model.objects.get(**kwargs)
    except model.DoesNotExist:
        model_name = model.__name__
        raise HttpError(404, f"{model_name} tidak ditemukan")


# ============================================================================
# COURSE ENDPOINTS - API v2
# ============================================================================

@apiv2.get('courses/{id}/', response=DetailCourseOutV2, auth=apiAuth, tags=["Courses"])
def get_course_v2(request, id: int):
    """
    Mengambil detail course dengan informasi lengkap (API v2).

    Perbedaan dengan v1:
    - teacher field berupa object (id, username, email, full_name)
    - ditambahkan member_count (jumlah member terdaftar)
    - ditambahkan contents_count (jumlah konten di course)
    - ditambahkan created_at dan updated_at

    Path Parameters:
    - id: ID course yang akan diambil

    Response menampilkan:
    - Detail course dengan teacher info lengkap
    - Jumlah member dan konten
    - List konten dengan detail lengkap

    Authentication: Wajib login (Bearer token)
    """
    course = get_object_or_404(Course, pk=id)
    
    # Annotate member_count dan prefetch contents
    course = Course.objects.prefetch_related('coursecontent_set').select_related('teacher').annotate(
        member_count=Count('coursemember')
    ).get(pk=id)
    
    # Convert ke response format
    contents = list(course.coursecontent_set.all())
    return {
        "id": course.id,
        "name": course.name,
        "description": course.description,
        "price": course.price,
        "teacher": {
            "id": course.teacher.id,
            "username": course.teacher.username,
            "email": course.teacher.email,
            "first_name": course.teacher.first_name,
            "last_name": course.teacher.last_name,
        },
        "member_count": course.member_count,
        "contents_count": len(contents),
        "contents": contents,
        "created_at": course.created_at,
        "updated_at": course.updated_at,
    }


@apiv2.get('courses/', response=List[CourseOutV2], auth=apiAuth, tags=["Courses"])
def list_courses_v2(request):
    """
    Mengambil daftar semua course dengan detail lengkap (API v2).

    Perbedaan dengan v1:
    - teacher field berupa object (id, username, email, full_name)
    - ditambahkan member_count
    - ditambahkan created_at dan updated_at

    Authentication: Wajib login (Bearer token)
    """
    courses = Course.objects.select_related('teacher').annotate(
        member_count=Count('coursemember')
    ).all()
    
    return [
        {
            "id": course.id,
            "name": course.name,
            "description": course.description,
            "price": course.price,
            "teacher": {
                "id": course.teacher.id,
                "username": course.teacher.username,
                "email": course.teacher.email,
                "first_name": course.teacher.first_name,
                "last_name": course.teacher.last_name,
            },
            "member_count": course.member_count,
            "created_at": course.created_at,
            "updated_at": course.updated_at,
        }
        for course in courses
    ]
