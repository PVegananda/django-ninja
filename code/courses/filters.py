"""
FilterSchema untuk Simple LMS - Modul 08: Advanced API Features

File ini mendefinisikan filter schemas untuk query parameters yang digunakan
pada endpoint list. FilterSchema secara otomatis memvalidasi parameter dan 
menerapkannya ke QuerySet.

Fitur:
- FilterSchema untuk Course (search, price filtering)
- FilterSchema untuk CourseContent (search, course_id filtering)
- Custom filter methods untuk logika kompleks
"""

from ninja import FilterSchema, Field
from typing import Optional
from datetime import datetime
from django.db.models import Q


class CourseFilter(FilterSchema):
    """
    Filter schema untuk Course.objects.all()
    
    Query Parameters:
    - search: Pencarian di field name dan description (case-insensitive)
    - price: Tampilkan course dengan harga di atas nilai ini
    - created_at: Tampilkan course yang dibuat setelah tanggal ini
    """
    # Search di multiple fields menggunakan 'q' parameter
    search: Optional[str] = Field(
        None,
        description="Cari berdasarkan nama course atau deskripsi",
        q=['name__icontains', 'description__icontains']
    )
    
    # Filter berdasarkan harga (custom filter method)
    price: Optional[int] = Field(
        0,
        description="Tampilkan course dengan harga di atas nilai ini"
    )
    
    # Filter berdasarkan tanggal (custom filter method)
    created_at: Optional[datetime] = Field(
        None,
        description="Tampilkan course yang dibuat setelah tanggal ini"
    )

    def filter_price(self, value: int) -> Q:
        """
        Custom filter: menampilkan course dengan harga di atas value.
        
        Jika value adalah 0 (default), tidak ada filter (kembalikan Q kosong).
        """
        if value > 0:
            return Q(price__gt=value)
        return Q()

    def filter_created_at(self, value: datetime) -> Q:
        """
        Custom filter: menampilkan course yang dibuat setelah tanggal tertentu.
        
        Jika value adalah None, tidak ada filter.
        """
        if value:
            return Q(created_at__gt=value)
        return Q()


class CourseContentFilter(FilterSchema):
    """
    Filter schema untuk CourseContent.objects.all()
    
    Query Parameters:
    - search: Pencarian di field name dan description (case-insensitive)
    - course_id: Filter berdasarkan course tertentu
    """
    # Search di multiple fields
    search: Optional[str] = Field(
        None,
        description="Cari berdasarkan nama atau deskripsi content",
        q=['name__icontains', 'description__icontains']
    )
    
    # Filter berdasarkan course
    course_id: Optional[int] = Field(
        None,
        description="Filter berdasarkan course ID"
    )

    def filter_course_id(self, value: int) -> Q:
        """
        Custom filter untuk course_id.
        Jika value adalah None, tidak ada filter.
        """
        if value:
            return Q(course_id=value)
        return Q()
"""
FilterSchema untuk Advanced API Features (Modul 08)

Mendefinisikan filter yang bisa digunakan pada endpoint list dengan
query parameters. FilterSchema otomatis memvalidasi dan menerapkan filter.
"""

from ninja import FilterSchema, Field
from typing import Optional
from datetime import datetime
from django.db.models import Q


class CourseFilter(FilterSchema):
    """
    Filter untuk Course list endpoint.
    
    Query Parameters:
    - search: Pencarian di field name dan description (case-insensitive)
    - price: Tampilkan course dengan harga di atas nilai ini (filter_price custom)
    - created_at: Tampilkan course yang dibuat setelah tanggal ini
    """
    search: Optional[str] = Field(
        None,
        q=['name__icontains', 'description__icontains']
    )
    price: Optional[int] = None
    created_at: Optional[datetime] = None
    
    def filter_price(self, value: int) -> Q:
        """Custom filter: menampilkan course dengan harga di atas value."""
        if value:
            return Q(price__gte=value)
        return Q()
    
    def filter_created_at(self, value: datetime) -> Q:
        """Custom filter: menampilkan course yang dibuat setelah tanggal tertentu."""
        if value:
            return Q(created_at__gt=value)
        return Q()


class CourseContentFilter(FilterSchema):
    """
    Filter untuk CourseContent list endpoint.
    
    Query Parameters:
    - search: Pencarian di field name dan description
    - course_id: Filter berdasarkan course tertentu
    - created_at: Tampilkan content yang dibuat setelah tanggal ini
    """
    search: Optional[str] = Field(
        None,
        q=['name__icontains', 'description__icontains']
    )
    course_id: Optional[int] = None
    created_at: Optional[datetime] = None
    
    def filter_course_id(self, value: int) -> Q:
        """Custom filter: tampilkan content dari course tertentu."""
        if value:
            return Q(course_id_id=value)
        return Q()
    
    def filter_created_at(self, value: datetime) -> Q:
        """Custom filter: tampilkan content setelah tanggal tertentu."""
        if value:
            return Q(created_at__gt=value)
        return Q()
