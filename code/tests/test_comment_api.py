# tests/test_comment_api.py
"""
Integration Tests untuk Comment API endpoint di Simple LMS.

Menguji:
- POST /comments/ (tambah komentar)
- PUT /comments/{id} (edit komentar)
- DELETE /comments/{id} (hapus komentar)
- Authorization (pengujian negatif)
"""
from django.test import TestCase
from ninja.testing import TestClient
from django.contrib.auth.models import User
from courses.models import Course, CourseMember, CourseContent, Comment
from courses.apiv1 import apiv1


class TestCommentAPI(TestCase):
    """Integration test untuk Comment endpoint."""

    def setUp(self):
        self.client = TestClient(apiv1)

        # Setup users
        self.teacher = User.objects.create_user(
            username='teacher_comment',
            password='testpass123'
        )
        self.student = User.objects.create_user(
            username='student_comment',
            password='testpass123'
        )
        self.non_member = User.objects.create_user(
            username='nonmember_comment',
            password='testpass123'
        )

        # Setup course
        self.course = Course.objects.create(
            name="Course for Comment Test",
            price=0,
            teacher=self.teacher
        )

        # Setup course content
        self.content = CourseContent.objects.create(
            name="Materi 1",
            description="Deskripsi Materi",
            course_id=self.course
        )

        # Daftarkan student sebagai member
        CourseMember.objects.create(
            course_id=self.course,
            user_id=self.student,
            roles='std'
        )

    def test_post_comment_by_enrolled_student(self):
        """Test student yang terdaftar bisa membuat komentar."""
        response = self.client.post(
            "/comments/",
            json={"comment": "Materi ini sangat bagus!", "content_id": self.content.id},
            user=self.student
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("message", response.json())

    def test_post_comment_by_non_member_returns_403(self):
        """Test user yang tidak terdaftar tidak bisa membuat komentar."""
        response = self.client.post(
            "/comments/",
            json={"comment": "Komentar tidak sah!", "content_id": self.content.id},
            user=self.non_member
        )
        self.assertEqual(response.status_code, 403)

    def test_post_comment_unauthenticated_returns_401(self):
        """Test komentar tanpa autentikasi mengembalikan 401."""
        response = self.client.post(
            "/comments/",
            json={"comment": "Komentar tanpa auth", "content_id": self.content.id}
        )
        self.assertEqual(response.status_code, 401)

    def test_post_comment_invalid_content_returns_404(self):
        """Test komentar pada content yang tidak ada mengembalikan 404."""
        response = self.client.post(
            "/comments/",
            json={"comment": "Komentar", "content_id": 99999},
            user=self.student
        )
        self.assertEqual(response.status_code, 404)

    def test_update_comment_by_owner(self):
        """Test pemilik komentar bisa mengedit komentarnya."""
        comment = Comment.objects.create(
            comment="Komentar Awal",
            user_id=self.student,
            content_id=self.content
        )
        response = self.client.put(
            f"/comments/{comment.id}",
            json={"comment": "Komentar Diupdate"},
            user=self.student
        )
        self.assertEqual(response.status_code, 200)
        comment.refresh_from_db()
        self.assertEqual(comment.comment, "Komentar Diupdate")

    def test_update_comment_by_non_owner_returns_403(self):
        """Test bukan pemilik komentar tidak bisa mengedit."""
        comment = Comment.objects.create(
            comment="Komentar Awal",
            user_id=self.student,
            content_id=self.content
        )
        response = self.client.put(
            f"/comments/{comment.id}",
            json={"comment": "Komentar Dimanipulasi"},
            user=self.non_member
        )
        self.assertEqual(response.status_code, 403)

    def test_delete_comment_by_owner(self):
        """Test pemilik komentar bisa menghapus komentarnya."""
        comment = Comment.objects.create(
            comment="Komentar Hapus",
            user_id=self.student,
            content_id=self.content
        )
        response = self.client.delete(
            f"/comments/{comment.id}",
            user=self.student
        )
        self.assertEqual(response.status_code, 204)
        self.assertEqual(Comment.objects.filter(id=comment.id).count(), 0)

    def test_delete_comment_by_course_teacher(self):
        """Test teacher pemilik course bisa menghapus komentar apapun."""
        comment = Comment.objects.create(
            comment="Komentar Student",
            user_id=self.student,
            content_id=self.content
        )
        response = self.client.delete(
            f"/comments/{comment.id}",
            user=self.teacher
        )
        self.assertEqual(response.status_code, 204)

    def test_delete_comment_by_non_owner_returns_403(self):
        """Test non-owner tidak bisa menghapus komentar."""
        comment = Comment.objects.create(
            comment="Komentar Protected",
            user_id=self.student,
            content_id=self.content
        )
        response = self.client.delete(
            f"/comments/{comment.id}",
            user=self.non_member
        )
        self.assertEqual(response.status_code, 403)

    def test_delete_comment_not_found_returns_404(self):
        """Test menghapus komentar yang tidak ada mengembalikan 404."""
        response = self.client.delete(
            "/comments/99999",
            user=self.student
        )
        self.assertEqual(response.status_code, 404)
