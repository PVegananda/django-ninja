# tests/test_models.py
from django.test import TestCase
from django.contrib.auth.models import User
from django.db import IntegrityError
from courses.models import Course, CourseMember, CourseContent, Comment, ROLE_OPTIONS


class TestCourseModel(TestCase):
    """Test cases untuk model Course."""

    def setUp(self):
        """Setup data yang digunakan di setiap test."""
        self.teacher = User.objects.create_user(
            username='teacher1',
            password='testpass123',
            email='teacher1@example.com'
        )

    def test_create_course(self):
        """Test membuat course baru."""
        course = Course.objects.create(
            name="Django for Beginners",
            description="Belajar Django dari nol",
            price=100000,
            teacher=self.teacher
        )
        self.assertEqual(course.name, "Django for Beginners")
        self.assertEqual(course.price, 100000)
        self.assertEqual(course.teacher, self.teacher)

    def test_course_str(self):
        """Test representasi string course."""
        course = Course.objects.create(
            name="Python Basics",
            teacher=self.teacher
        )
        self.assertEqual(str(course), "Python Basics")

    def test_course_default_price(self):
        """Test default price adalah 10000."""
        course = Course.objects.create(
            name="Free Course",
            teacher=self.teacher
        )
        self.assertEqual(course.price, 10000)

    def test_course_teacher_relationship(self):
        """Test relasi course dengan teacher."""
        Course.objects.create(name="Course A", teacher=self.teacher)
        Course.objects.create(name="Course B", teacher=self.teacher)
        # teacher adalah ForeignKey tanpa related_name, pakai default course_set
        self.assertEqual(self.teacher.course_set.count(), 2)

    def test_course_description_default(self):
        """Test default description adalah '-'."""
        course = Course.objects.create(
            name="Course Test",
            teacher=self.teacher
        )
        self.assertEqual(course.description, '-')


class TestCourseMemberModel(TestCase):
    """Test cases untuk model CourseMember."""

    def setUp(self):
        """Setup data yang digunakan di setiap test."""
        self.teacher = User.objects.create_user(
            username='teacher1',
            password='testpass123'
        )
        self.student = User.objects.create_user(
            username='student1',
            password='testpass123'
        )
        self.course = Course.objects.create(
            name="Django Course",
            price=150000,
            teacher=self.teacher
        )

    def test_create_course_member(self):
        """Test mendaftarkan member ke course."""
        member = CourseMember.objects.create(
            course_id=self.course,
            user_id=self.student,
            roles='std'
        )
        self.assertEqual(member.course_id, self.course)
        self.assertEqual(member.user_id, self.student)
        self.assertEqual(member.roles, 'std')

    def test_course_member_str(self):
        """Test representasi string course member."""
        member = CourseMember.objects.create(
            course_id=self.course,
            user_id=self.student,
            roles='std'
        )
        expected = f"{self.student} - {self.course} (std)"
        self.assertEqual(str(member), expected)

    def test_default_role_is_std(self):
        """Test default role adalah 'std' (student)."""
        member = CourseMember.objects.create(
            course_id=self.course,
            user_id=self.student
        )
        self.assertEqual(member.roles, 'std')

    def test_role_options_exist(self):
        """Test role options tersedia."""
        valid_roles = [role[0] for role in ROLE_OPTIONS]
        self.assertIn('std', valid_roles)
        self.assertIn('ast', valid_roles)

    def test_cascade_delete_user(self):
        """Test member tidak langsung dihapus jika user dihapus (RESTRICT)."""
        CourseMember.objects.create(
            course_id=self.course,
            user_id=self.student,
            roles='std'
        )
        self.assertEqual(CourseMember.objects.count(), 1)


class TestCourseContentModel(TestCase):
    """Test cases untuk model CourseContent."""

    def setUp(self):
        """Setup data untuk setiap test."""
        self.teacher = User.objects.create_user(
            username='teacher2',
            password='testpass123'
        )
        self.course = Course.objects.create(
            name="Python Course",
            teacher=self.teacher
        )

    def test_create_course_content(self):
        """Test membuat course content baru."""
        content = CourseContent.objects.create(
            name="Pengenalan Python",
            description="Materi dasar Python",
            course_id=self.course
        )
        self.assertEqual(content.name, "Pengenalan Python")
        self.assertEqual(content.course_id, self.course)

    def test_course_content_str(self):
        """Test representasi string course content."""
        content = CourseContent.objects.create(
            name="Bab 1 - Intro",
            course_id=self.course
        )
        self.assertEqual(str(content), "Bab 1 - Intro")

    def test_course_content_optional_video_url(self):
        """Test video_url boleh kosong."""
        content = CourseContent.objects.create(
            name="Bab 2",
            course_id=self.course,
            video_url=None
        )
        self.assertIsNone(content.video_url)
