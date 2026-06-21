# analytics/management/commands/seed_analytics.py
"""
Django Management Command untuk mengisi data sample ke MongoDB.

Digunakan untuk demo dan testing aggregation pipeline.

Cara menjalankan:
    docker-compose exec app python manage.py seed_analytics
    docker-compose exec app python manage.py seed_analytics --count 200
"""
import random
from datetime import datetime, timezone, timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from courses.models import Course
from analytics.activity_service import (
    log_activity,
    ACTION_VIEW_COURSE, ACTION_ENROLL, ACTION_POST_COMMENT,
    ACTION_VIEW_CONTENT, ACTION_LOGIN
)


BROWSERS = ['Chrome', 'Firefox', 'Safari', 'Edge', 'Brave']
IPS = ['192.168.1.1', '10.0.0.1', '172.16.0.1', '127.0.0.1']


class Command(BaseCommand):
    help = 'Seed MongoDB dengan data sample activity logs untuk demo analytics'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=100,
            help='Jumlah activity logs yang akan dibuat (default: 100)'
        )

    def handle(self, *args, **options):
        count = options['count']

        self.stdout.write(self.style.MIGRATE_HEADING(
            f'\n🌱 Seeding MongoDB dengan {count} activity logs...'
        ))

        # Ambil users dan courses dari PostgreSQL
        users = list(User.objects.all()[:20])
        courses = list(Course.objects.all()[:10])

        if not users:
            self.stdout.write(self.style.ERROR(
                '❌ Tidak ada user di database! Buat user terlebih dahulu.'
            ))
            return

        if not courses:
            self.stdout.write(self.style.WARNING(
                '⚠️  Tidak ada course di database. Activity log tidak akan punya course_id.'
            ))

        actions = [
            ACTION_VIEW_COURSE,
            ACTION_ENROLL,
            ACTION_POST_COMMENT,
            ACTION_VIEW_CONTENT,
            ACTION_LOGIN,
        ]
        # Weight: view_course lebih sering terjadi
        action_weights = [40, 10, 20, 25, 5]

        inserted = 0
        for _ in range(count):
            user = random.choice(users)
            action = random.choices(actions, weights=action_weights, k=1)[0]

            course_id = None
            course_name = None
            if courses and action in [ACTION_VIEW_COURSE, ACTION_ENROLL,
                                       ACTION_POST_COMMENT, ACTION_VIEW_CONTENT]:
                course = random.choice(courses)
                course_id = course.id
                course_name = course.name

            metadata = {
                'browser': random.choice(BROWSERS),
                'ip': random.choice(IPS),
                'source': 'seed_command'
            }

            if action == ACTION_VIEW_COURSE:
                metadata['duration_seconds'] = random.randint(30, 3600)
            elif action == ACTION_VIEW_CONTENT:
                metadata['progress_percent'] = random.randint(0, 100)

            log_activity(
                user_id=user.id,
                username=user.username,
                action=action,
                course_id=course_id,
                course_name=course_name,
                metadata=metadata
            )
            inserted += 1

        self.stdout.write(self.style.SUCCESS(
            f'\n✅ Berhasil menyimpan {inserted} activity logs ke MongoDB!'
        ))
        self.stdout.write(self.style.NOTICE(
            '\nCek hasilnya di:\n'
            '  GET /api/analytics/stats/action-summary/\n'
            '  GET /api/analytics/stats/active-users/\n'
            '  GET /api/analytics/stats/popular-courses/\n'
            '  GET /api/analytics/stats/daily/\n'
        ))
