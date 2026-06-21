# tests/test_course_api.py
"""
Integration Tests untuk Course API endpoint di Simple LMS.

Menggunakan Django Ninja TestClient untuk menguji:
- Course CRUD (Create, Read, Update, Delete)
- Enrollment
- Authorization (pengujian negatif)
"""
from django.test import TestCase
from ninja.testing import TestClient
from django.contrib.auth.models import User
from courses.models import Course, CourseMember
from courses.apiv1 import apiv1


class TestCourseListAPI(TestCase):
    """Integration test untuk GET /courses/ (list)."""

    def setUp(self):
        self.client = TestClient(apiv1)
        self.teacher = User.objects.create_user(
            username='teacher1',
            password='testpass123'
        )
        self.course = Course.objects.create(
            name="Django Testing",
            description="Belajar automated testing",
            price=200000,
            teacher=self.teacher
        )

    def test_list_courses_returns_200(self):
        """Test GET /courses/ mengembalikan 200."""
        response = self.client.get("/courses/")
        self.assertEqual(response.status_code, 200)

    def test_list_courses_contains_course(self):
        """Test course yang dibuat muncul di list."""
        response = self.client.get("/courses/")
        data = response.json()
        self.assertGreater(data['count'], 0)

    def test_detail_course_returns_200(self):
        """Test GET /courses/{id} mengembalikan detail course."""
        response = self.client.get(f"/courses/{self.course.id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['name'], "Django Testing")

    def test_detail_course_not_found_returns_404(self):
        """Test GET /courses/{id} dengan id tidak ada mengembalikan 404."""
        response = self.client.get("/courses/99999")
        self.assertEqual(response.status_code, 404)


class TestCourseCreateAPI(TestCase):
    """Integration test untuk POST /courses/ (create)."""

    def setUp(self):
        self.client = TestClient(apiv1)
        self.teacher = User.objects.create_user(
            username='teacher2',
            password='testpass123'
        )

    def test_create_course_authenticated(self):
        """Test membuat course dengan user terautentikasi."""
        response = self.client.post(
            "/courses/",
            json={"name": "Kursus Baru", "description": "Desc", "price": 50000},
            user=self.teacher
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['name'], "Kursus Baru")
        self.assertEqual(Course.objects.filter(teacher=self.teacher).count(), 1)

    def test_create_course_unauthenticated_returns_401(self):
        """Test membuat course tanpa autentikasi mengembalikan 401."""
        response = self.client.post(
            "/courses/",
            json={"name": "Kursus Baru", "description": "Desc", "price": 50000}
        )
        self.assertEqual(response.status_code, 401)

    def test_create_course_negative_price_returns_400(self):
        """Test membuat course dengan harga negatif mengembalikan 400."""
        response = self.client.post(
            "/courses/",
            json={"name": "Kursus Test", "description": "Desc", "price": -100},
            user=self.teacher
        )
        self.assertEqual(response.status_code, 400)


class TestCourseUpdateDeleteAPI(TestCase):
    """Integration test untuk PUT dan DELETE /courses/{id}."""

    def setUp(self):
        self.client = TestClient(apiv1)
        self.teacher = User.objects.create_user(
            username='teacher3',
            password='testpass123'
        )
        self.other_user = User.objects.create_user(
            username='other_user',
            password='testpass123'
        )
        self.course = Course.objects.create(
            name="Kursus Lama",
            description="Desc Lama",
            price=100000,
            teacher=self.teacher
        )

    def test_update_course_by_owner(self):
        """Test update course oleh pemilik berhasil."""
        response = self.client.put(
            f"/courses/{self.course.id}",
            json={"name": "Kursus Update", "description": "Desc Baru", "price": 150000},
            user=self.teacher
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['name'], "Kursus Update")

    def test_update_course_by_non_owner_returns_403(self):
        """Test update course oleh bukan pemilik mengembalikan 403."""
        response = self.client.put(
            f"/courses/{self.course.id}",
            json={"name": "Kursus Hack", "description": "Desc Hack", "price": 0},
            user=self.other_user
        )
        self.assertEqual(response.status_code, 403)

    def test_delete_course_by_owner(self):
        """Test delete course oleh pemilik berhasil."""
        # Hapus dulu CourseMember jika ada, karena ada RESTRICT
        response = self.client.delete(
            f"/courses/{self.course.id}",
            user=self.teacher
        )
        self.assertEqual(response.status_code, 204)
        self.assertEqual(Course.objects.filter(id=self.course.id).count(), 0)

    def test_delete_course_by_non_owner_returns_403(self):
        """Test delete course oleh bukan pemilik mengembalikan 403."""
        response = self.client.delete(
            f"/courses/{self.course.id}",
            user=self.other_user
        )
        self.assertEqual(response.status_code, 403)


class TestCourseEnrollmentAPI(TestCase):
    """Integration test untuk enrollment Course."""

    def setUp(self):
        self.client = TestClient(apiv1)
        self.teacher = User.objects.create_user(
            username='teacher4',
            password='testpass123'
        )
        self.student = User.objects.create_user(
            username='student4',
            password='testpass123'
        )
        self.course = Course.objects.create(
            name="Kursus Enrollment",
            price=0,
            teacher=self.teacher
        )

    def test_enroll_course_authenticated(self):
        """Test mendaftar ke course dengan autentikasi berhasil."""
        response = self.client.post(
            f"/course/{self.course.id}/enroll/",
            user=self.student
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            CourseMember.objects.filter(
                user_id=self.student,
                course_id=self.course
            ).exists()
        )

    def test_enroll_course_unauthenticated_returns_401(self):
        """Test mendaftar ke course tanpa autentikasi mengembalikan 401."""
        response = self.client.post(f"/course/{self.course.id}/enroll/")
        self.assertEqual(response.status_code, 401)

    def test_enroll_twice_returns_400(self):
        """Test mendaftar dua kali ke course yang sama mengembalikan 400."""
        CourseMember.objects.create(
            user_id=self.student,
            course_id=self.course,
            roles='std'
        )
        response = self.client.post(
            f"/course/{self.course.id}/enroll/",
            user=self.student
        )
        self.assertEqual(response.status_code, 400)
