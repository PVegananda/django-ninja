"""
Views untuk Simple LMS - Lab 05: Optimasi Database

File ini dibagi menjadi 3 bagian:

  BAGIAN 1 - Views dengan N+1 Problem
    Gunakan Django Silk (http://localhost:8000/silk/) untuk mengamati
    jumlah query yang dihasilkan oleh setiap endpoint.

  BAGIAN 2 - Views Teroptimasi (Referensi Solusi)
    Bandingkan jumlah query di Silk setelah mengakses endpoint ini.

  BAGIAN 3 - Statistik
    Contoh penggunaan aggregate() untuk kalkulasi di level database.

Petunjuk Lab:
  1. Jalankan python manage.py seed_data untuk mengisi data
  2. Akses endpoint BAGIAN 1, amati jumlah query di Silk
  3. Coba optimalkan sendiri sebelum melihat BAGIAN 2
  4. Bandingkan hasilnya
"""

from django.db.models import Avg, Count, Max, Min, Prefetch
from django.http import JsonResponse

from .models import Comment, Course, CourseContent, CourseMember
