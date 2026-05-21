"""
Schema Pydantic untuk validasi input/output API
Digunakan oleh Django Ninja untuk serialisasi dan dokumentasi otomatis

Skema terbagi menjadi:
- Input Schema (CourseIn, CourseContentIn) - untuk request body
- Output Schema (CourseOut, ContentTitleOut) - untuk response body
"""

from ninja import Schema, Field
from datetime import datetime
from typing import Optional, List
from pydantic import field_validator


class UserOut(Schema):
    """Schema untuk data User yang dikembalikan dalam response."""
    id: int
    username: str
    first_name: str
    last_name: str
    email: str


class Register(Schema):
    """
    Schema untuk registrasi user baru.
    
    Field yang diminta saat register:
    - username: Username unik
    - password: Password (akan di-hash otomatis)
    - email: Email unik
    - first_name: Nama depan
    - last_name: Nama belakang
    """
    username: str
    password: str
    email: str
    first_name: str
    last_name: str


class CourseIn(Schema):
    """
    Schema untuk input saat membuat/mengupdate Course.
    
    Field yang dikirim client:
    - name: Nama course (wajib)
    - description: Deskripsi course (opsional, default: '-')
    - price: Harga course dalam rupiah (opsional, default: 10000)
    """
    name: str
    description: str = '-'
    price: int = 10000


class CourseOut(Schema):
    """
    Schema untuk output data Course.
    
    Berisi semua field termasuk yang di-generate server (id, timestamps, teacher).
    Field teacher adalah nested schema (one-to-many relationship).
    """
    id: int
    name: str
    description: str
    price: int
    image: Optional[str] = ''
    teacher: UserOut
    created_at: datetime
    updated_at: datetime


class ContentTitleOut(Schema):
    """Schema untuk menampilkan judul konten saja (simplified)."""
    id: int
    name: str


class DetailCourseOut(CourseOut):
    """
    Schema untuk detail Course beserta daftar konten.
    
    Mewarisi semua field dari CourseOut dan menambahkan:
    - contents: List dari ContentTitleOut (dari reverse relation coursecontent_set)
    
    Field(..., alias="coursecontent_set") memetakan Django reverse relation
    ke field contents di schema.
    """
    contents: List[ContentTitleOut] = Field(
        ..., alias="coursecontent_set"
    )


class CourseContentIn(Schema):
    """
    Schema untuk input saat membuat/mengupdate CourseContent.
    
    Field yang dikirim client:
    - name: Judul konten (wajib)
    - description: Deskripsi konten (opsional, default: '-')
    - video_url: URL video (opsional)
    - course_id: ID course parent (wajib)
    - parent_id: ID konten parent untuk nested content (opsional)
    """
    name: str
    description: str = '-'
    video_url: Optional[str] = None
    course_id: int
    parent_id: Optional[int] = None


class CourseContentOut(Schema):
    """
    Schema untuk output data CourseContent.
    
    Berisi semua field termasuk timestamps.
    Note: Uses course_id_id (Django ForeignKey naming) mapped to course_id for API
    """
    id: int
    name: str
    description: str
    video_url: Optional[str] = None
    course_id: int = Field(..., alias='course_id_id')
    parent_id: Optional[int] = Field(None, alias='parent_id_id')
    created_at: datetime
    updated_at: datetime
    
    class Config:
        populate_by_name = True


class CourseMemberIn(Schema):
    """Schema untuk input saat membuat/mengupdate CourseMember."""
    course_id: int
    user_id: int
    roles: str = 'std'  # 'std' = Siswa, 'ast' = Asisten


class CourseMemberOut(Schema):
    """Schema untuk output data CourseMember."""
    id: int
    course_id: int
    user_id: int
    roles: str
    created_at: datetime


class CommentIn(Schema):
    """Schema untuk input saat membuat komentar."""
    comment: str
    content_id: int


class CommentUpdate(Schema):
    """Schema untuk update komentar."""
    comment: str


class CommentOut(Schema):
    """Schema untuk output data komentar."""
    id: int
    comment: str
    user_id: int
    content_id: int
    created_at: datetime
    updated_at: datetime
