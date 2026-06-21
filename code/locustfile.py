# locustfile.py
"""
Load Testing dengan Locust untuk Simple LMS API.

Cara menjalankan:
    locust -f locustfile.py --host=http://localhost:8000

Atau headless (tanpa UI):
    locust -f locustfile.py --host=http://localhost:8000 \
        --users 10 --spawn-rate 2 --run-time 30s --headless

Atau via Docker:
    docker-compose exec app locust -f locustfile.py --host=http://app:8000
"""
import random
from locust import HttpUser, task, between


class LMSUser(HttpUser):
    """
    Simulasi user yang mengakses Simple LMS API.

    Skenario:
    - GET /api/v1/courses/ (weight 5: paling sering diakses)
    - GET /api/v1/courses/{id} (weight 3: sering diakses)
    - GET /api/v1/contents/ (weight 2: kadang diakses)
    """

    # Waktu tunggu antara setiap request (1-3 detik)
    wait_time = between(1, 3)

    # Daftar course_id yang akan dicoba (diisi setelah on_start)
    course_ids = [1, 2, 3, 4, 5]

    @task(5)
    def list_courses(self):
        """
        GET /api/v1/courses/ - Daftar semua course.
        Weight 5: task ini dipanggil 5x lebih sering dari task weight 1.
        """
        with self.client.get(
            "/api/v1/courses/",
            name="/api/v1/courses/ [LIST]",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status code: {response.status_code}")

    @task(3)
    def detail_course(self):
        """
        GET /api/v1/courses/{id} - Detail satu course.
        Weight 3: task ini dipanggil 3x lebih sering dari task weight 1.
        """
        course_id = random.choice(self.course_ids)
        with self.client.get(
            f"/api/v1/courses/{course_id}",
            name="/api/v1/courses/[id] [DETAIL]",
            catch_response=True
        ) as response:
            if response.status_code in [200, 404]:
                response.success()
            else:
                response.failure(f"Status code: {response.status_code}")

    @task(2)
    def list_contents(self):
        """
        GET /api/v1/contents/ - Daftar course content.
        Weight 2: task ini dipanggil 2x lebih sering dari task weight 1.
        """
        course_id = random.choice(self.course_ids)
        with self.client.get(
            f"/api/v1/contents/?course_id={course_id}",
            name="/api/v1/contents/ [LIST]",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status code: {response.status_code}")
