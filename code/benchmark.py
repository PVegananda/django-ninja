# benchmark.py
"""
Script Benchmark untuk mengukur peningkatan performa API Simple LMS.

Membandingkan response time endpoint sebelum dan sesudah caching Redis.

Cara menjalankan (dari dalam Docker):
    docker-compose exec app python benchmark.py

Atau dari host setelah Docker jalan:
    python benchmark.py
"""
import requests
import time

BASE_URL = "http://localhost:8000/api/v1"
ITERATIONS = 100


def benchmark_endpoint(url, label):
    """
    Mengukur rata-rata response time sebuah endpoint.

    Args:
        url: URL endpoint yang akan di-benchmark
        label: Label untuk tampilan hasil

    Returns:
        float: Rata-rata response time dalam ms
    """
    times = []
    print(f"\nBenchmarking: {label}")
    print(f"  URL: {url}")
    print(f"  Iterasi: {ITERATIONS}")

    for i in range(ITERATIONS):
        start = time.time()
        try:
            response = requests.get(url, timeout=10)
            elapsed = (time.time() - start) * 1000  # Konversi ke ms
            times.append(elapsed)
        except requests.exceptions.ConnectionError:
            print(f"  ❌ Koneksi gagal! Pastikan server berjalan di {BASE_URL}")
            return None
        except Exception as e:
            print(f"  ❌ Error: {e}")
            return None

    avg_time = sum(times) / len(times)
    min_time = min(times)
    max_time = max(times)
    p95_time = sorted(times)[int(0.95 * len(times))]

    print(f"\n  Hasil:")
    print(f"  ├─ Rata-rata  : {avg_time:.2f} ms")
    print(f"  ├─ Minimum   : {min_time:.2f} ms")
    print(f"  ├─ Maksimum  : {max_time:.2f} ms")
    print(f"  └─ P95       : {p95_time:.2f} ms")

    return avg_time


def main():
    print("=" * 60)
    print("BENCHMARK: Simple LMS API Performance")
    print("=" * 60)
    print(f"Target: {BASE_URL}")
    print()
    print("CATATAN:")
    print("  - Jalankan pertama kali untuk mengisi cache (cache miss)")
    print("  - Jalankan kedua kali untuk mengukur dengan cache (cache hit)")
    print("  - Perbedaan antara keduanya menunjukkan peningkatan Redis")
    print()

    # Benchmark endpoint list courses
    avg_courses = benchmark_endpoint(
        f"{BASE_URL}/courses/",
        "GET /courses/ (list semua course)"
    )

    # Benchmark endpoint detail course (ID 1)
    avg_detail = benchmark_endpoint(
        f"{BASE_URL}/courses/1",
        "GET /courses/1 (detail course)"
    )

    # Benchmark endpoint popular courses (Redis Sorted Set)
    avg_popular = benchmark_endpoint(
        f"{BASE_URL}/courses/popular/",
        "GET /courses/popular/ (leaderboard Redis)"
    )

    # Ringkasan
    print("\n" + "=" * 60)
    print("RINGKASAN")
    print("=" * 60)
    if avg_courses:
        print(f"  GET /courses/          : {avg_courses:.2f} ms")
    if avg_detail:
        print(f"  GET /courses/1         : {avg_detail:.2f} ms")
    if avg_popular:
        print(f"  GET /courses/popular/  : {avg_popular:.2f} ms")
    print()
    print("Tips: Bandingkan hasil sebelum dan sesudah Redis aktif!")
    print("=" * 60)


if __name__ == "__main__":
    main()
