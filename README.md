![Django](https://img.shields.io/badge/Django-5.0-darkgreen?style=for-the-badge&logo=django)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-blue?style=for-the-badge&logo=postgresql)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker)
![Python](https://img.shields.io/badge/Python-3.11-blue?style=for-the-badge&logo=python)

# Django Ninja - Simple LMS API

REST API untuk Simple Learning Management System menggunakan Django Ninja. Project ini adalah praktik modul 06-08 dari Pemrograman Sisi Server.

## Apa ini?

Ini project untuk belajar cara bikin REST API yang production-ready. Pake Django Ninja yang lebih modern dibanding DRF, dengan type hints, otomatis documentation, dan advanced features seperti filtering, pagination, rate limiting, API versioning, file operations, dan partial updates.

## Setup

### Prerequisites
- Docker & Docker Compose
- MacBook Air M2 (atau linux/windows dengan docker)

### Jalanin Project

```bash
# Build docker image
docker-compose build

# Start containers
docker-compose up -d

# Run migrations
docker-compose exec app python manage.py migrate

# Seed database (optional, tapi ada 100 courses ready)
docker-compose exec app python manage.py seed_data
```

Server siap di `http://localhost:8000`

## API Endpoints

### Courses (v1 - Basic)
- `GET /api/v1/courses/` - List semua courses dengan filtering & pagination
- `GET /api/v1/courses/{id}` - Detail course + contents
- `POST /api/v1/courses/` - Buat course baru
- `PUT /api/v1/courses/{id}` - Update course (full replacement)
- `PATCH /api/v1/courses/{id}` - Partial update course (hanya field yang dikirim)
- `DELETE /api/v1/courses/{id}` - Hapus course
- `POST /api/v1/courses/{id}/upload-image/` - Upload course thumbnail
- `POST /api/v1/course/{id}/enroll/` - Daftar ke course

### Courses - Advanced Filtering & Sorting
Query parameters untuk `/api/v1/courses/`:
- `?search=python` - Cari di nama atau deskripsi (case-insensitive)
- `?price=50000` - Tampilkan course dengan harga di atas nilai (custom filter)
- `?created_at=2024-01-01T00:00:00` - Filter course setelah tanggal tertentu
- `?ordering=name` - Urutkan by name (asc), `-name` (desc)
- `?ordering=-price` - Urutkan harga termahal dulu
- `?ordering=-created_at` - Urutkan terbaru dulu (default)
- `?page=2` - Pagination (10 items per page)

Contoh kombinasi:
```
GET /api/v1/courses/?search=python&price=50000&ordering=-price&page=1
```

### Courses v2 - Enhanced Response
```
GET /api/v2/courses/` - List dengan member_count & timestamps
GET /api/v2/courses/{id}/` - Detail dengan teacher object lengkap
```

**Perbedaan v1 vs v2:**
- v1 teacher: `"teacher": "dosen01"` (string username)
- v2 teacher: `"teacher": {id, username, email, first_name, last_name}` (full object)

### Contents
- `GET /api/v1/contents/` - List contents dengan filtering
- `GET /api/v1/contents/{id}` - Detail content
- `POST /api/v1/contents/` - Buat content
- `PUT /api/v1/contents/{id}` - Update content
- `PATCH /api/v1/contents/{id}` - Partial update content
- `DELETE /api/v1/contents/{id}` - Hapus content
- `POST /api/v1/contents/{id}/upload-attachment/` - Upload file materi
- `GET /api/v1/contents/{id}/download/` - Download attachment (member only)

### Authentication & Authorization
- `POST /api/v1/register/` - Registrasi user baru (rate limited: 5/min)
- `POST /api/v1/auth/sign-in` - Login & dapat token
- `POST /api/v1/auth/token-refresh` - Refresh access token
- `POST /api/v1/mycourses/` - List course yang diikuti (auth required)

### Comments
- `GET /api/v1/comments/` - List komentar
- `POST /api/v1/comments/` - Buat komentar (auth required)
- `PUT /api/v1/comments/{id}` - Edit komentar (owner only)
- `DELETE /api/v1/comments/{id}` - Hapus komentar (owner/teacher/admin)

### Documentation
- `GET /api/v1/docs` - Swagger UI (v1)
- `GET /api/v2/docs` - Swagger UI (v2)
- `GET /api/v1/openapi.json` - OpenAPI schema v1
- `GET /api/v2/openapi.json` - OpenAPI schema v2

### Test
- `GET /api/v1/hello/` - Sanity check

## Test Endpoints

### Via curl
```bash
# List courses
curl http://localhost:8000/api/v1/courses/

# Search courses
curl "http://localhost:8000/api/v1/courses/?search=Pemrograman"

# Detail course
curl http://localhost:8000/api/v1/courses/1

# Create course
curl -X POST http://localhost:8000/api/v1/courses/ \
  -H "Content-Type: application/json" \
  -d '{"name":"My Course","description":"Cool stuff","price":99999}'

# List contents
curl http://localhost:8000/api/v1/contents/

# Filter contents by course
curl "http://localhost:8000/api/v1/contents/?course_id=1"
```

### Via Swagger UI
Buka browser ke `http://localhost:8000/api/v1/docs` dan test langsung dari sana. Jauh lebih enak.

## Project Structure

```
code/
├── courses/
│   ├── apiv1.py          # API v1 endpoints (CRUD + Auth + Advanced)
│   ├── apiv2.py          # API v2 endpoints (enhanced responses)
│   ├── filters.py        # FilterSchema untuk advanced queries
│   ├── schemas.py        # Pydantic schemas (input/output validation)
│   ├── models.py         # Django models (Course, Content, User, etc)
│   ├── views.py          # Django views (from previous modules)
│   ├── urls.py           # Course app URLs
│   ├── admin.py          # Django admin
│   ├── tests.py
│   └── migrations/       # Database migrations
├── lms/
│   ├── urls.py           # Main URL config (API routes registered here)
│   ├── settings.py       # Django settings
│   ├── wsgi.py
│   └── asgi.py
├── manage.py
└── requirements.txt

docker-compose.yml       # Docker configuration
Dockerfile              # Python + PostgreSQL setup
```

## Key Features

✅ **Type-Safe** - Python type hints everywhere  
✅ **Auto Docs** - Swagger UI generated otomatis (v1 & v2)  
✅ **Validation** - Pydantic schemas handle validation  
✅ **CRUD Ready** - 20+ endpoints siap pakai  
✅ **Query Params** - Search, filter, sorting dengan whitelist  
✅ **Pagination** - PageNumberPagination (10 items/page)  
✅ **Rate Limiting** - 5/min on register endpoint (brute force protection)  
✅ **API Versioning** - v1 & v2 dengan enhanced responses  
✅ **File Operations** - Upload images & attachments, download files  
✅ **Partial Updates** - PATCH untuk update hanya field tertentu  
✅ **Error Handling** - Proper HTTP status codes & messages  
✅ **Optimized** - select_related & prefetch_related  
✅ **Nested Data** - Relasi Course → Teacher, Course → Contents  
✅ **Authentication** - JWT token-based (access + refresh)  
✅ **Authorization** - RBAC (Role-Based Access Control)  

## Database

PostgreSQL running di container. Default credentials di `docker-compose.yml`:
- User: `postgres`
- Password: `postgres`
- Database: `lms_db`
- Port: `5436`

Sudah ada 100+ courses dengan teacher dan content data ready.

## Modul 08: Advanced API Features

Fitur-fitur production-ready untuk membuat API yang scalable dan robust.

### Step 1: Filtering, Sorting & Pagination ✅
**Query Parameter Examples:**
```bash
# Search courses
GET /api/v1/courses/?search=python

# Filter by price (courses with price > 50000)
GET /api/v1/courses/?price=50000

# Sort by price (descending)
GET /api/v1/courses/?ordering=-price

# Sort by creation date (newest first)
GET /api/v1/courses/?ordering=-created_at

# Pagination (10 items per page)
GET /api/v1/courses/?page=2

# Combine all
GET /api/v1/courses/?search=python&price=50000&ordering=-price&page=1
```

**Whitelisted Sorting Fields:** `name`, `-name`, `price`, `-price`, `created_at`, `-created_at`

### Step 2: Rate Limiting ✅
Proteksi endpoint register dari brute force attacks.
- 5 attempts per minute dari setiap IP address
- Mengembalikan HTTP 429 ketika limit terlampaui
- Retry-After header menunjukkan waktu tunggu

### Step 3: API Versioning (v2) ✅
Dua versi API untuk backward compatibility:

**v1 Response (Simple):**
```json
{
  "id": 1,
  "name": "Python Basics",
  "teacher": "dosen01"
}
```

**v2 Response (Enhanced):**
```json
{
  "id": 1,
  "name": "Python Basics",
  "teacher": {
    "id": 1,
    "username": "dosen01",
    "email": "dosen@example.com",
    "first_name": "Dosen",
    "last_name": "Satu"
  },
  "member_count": 25,
  "created_at": "2024-03-15T10:30:00Z",
  "updated_at": "2024-06-20T14:00:00Z"
}
```

### Step 4: File Upload ✅
**Course Image:**
```bash
POST /api/v1/courses/{id}/upload-image/
- Max size: 2MB
- Types: JPEG, PNG, WebP
- Authorization: course owner only
```

**Content Attachment:**
```bash
POST /api/v1/contents/{id}/upload-attachment/
- Max size: 10MB
- Types: PDF, DOCX, PPTX, ZIP
- Authorization: course owner only
```

### Step 5: File Download ✅
```bash
GET /api/v1/contents/{id}/download/
- Authorization: course members + course owner
- Response: File dengan Content-Disposition header
- Browser: Automatic download
```

### Step 6: Partial Update (PATCH) ✅
Update hanya field yang dikirm tanpa merubah yang lain:

```bash
# Update hanya price (name/description tetap)
PATCH /api/v1/courses/1/
{"price": 50000}

# Update multiple fields
PATCH /api/v1/courses/1/
{"name": "Python Advanced", "price": 75000}

# Update content video URL
PATCH /api/v1/contents/5/
{"video_url": "https://youtube.com/watch?v=..."}
```

## Modul 07: Authentication & Authorization

### Fitur Baru (JWT Token-Based)
- User registration dengan validasi duplikasi
- Login & token generation (access + refresh token)
- Token refresh tanpa login ulang
- Protected endpoints dengan Bearer token
- Role-Based Access Control (RBAC)
- Authorization checks pada setiap endpoint

### Auth Endpoints
- `POST /api/v1/register/` - Daftar user baru
- `POST /api/v1/auth/sign-in` - Login & dapat token
- `POST /api/v1/auth/token-refresh` - Refresh access token

### User Functions
- `POST /api/v1/course/{id}/enroll/` - Daftar ke course (auth required)
- `GET /api/v1/mycourses/` - List course yang diikuti (auth required)

### Comment Management (dengan Authorization)
- `POST /api/v1/comments/` - Buat komentar (hanya member)
- `PUT /api/v1/comments/{id}` - Edit komentar (hanya owner)
- `DELETE /api/v1/comments/{id}` - Hapus komentar (owner/teacher/admin)

### Protected Endpoints
- `POST /api/v1/courses/` - Buat course (auth + auto teacher)
- `PUT /api/v1/courses/{id}` - Edit course (auth + owner only)
- `DELETE /api/v1/courses/{id}` - Hapus course (owner/admin)
- Content CRUD juga dilindungi (owner only)

### Test di Swagger UI
1. Register user: `POST /register/` → dapat user ID
2. Login: `POST /auth/sign-in` → dapat tokens
3. Klik "Authorize" di Swagger → masukkan access token
4. Semua request otomatis include token

## Modul 06: Basic CRUD

Foundation dari API dengan standard REST operations untuk Course dan Content.

## Commits

Project ini dibuat step-by-step dengan jelas commit history:

**Modul 08: Advanced API Features** (6 commits)
```
fcedf9d - Step 6: Partial Update (PATCH) endpoints
9fce306 - Step 5: File Download dengan authorization
c1ce1b4 - Step 4: File Upload dengan validasi
cc866a8 - Step 3: API v2 versioning dengan enhanced responses
680967f - Step 2: Rate Limiting (django-ratelimit)
06c709b - Step 1: Filtering, Sorting & Pagination (FilterSchema)
```

**Modul 07: Authentication & Authorization** (9 commits)
```
aa7348d - 9: Setup script untuk migrations & seed data
84207cc - 8.1-8.3: Proteksi Content CRUD (owner only)
fad76ca - 7.1-7.3: Comment CRUD dengan full authorization
487143f - 6.1-6.2: Course enrollment & mycourses endpoints
a80ef43 - 5.1-5.3: Proteksi Course CRUD (auth + owner checks)
6182f08 - 4.1-4.5: Register endpoint dengan validasi
fa49f4a - 3.1-3.3: Schemas untuk auth & comments
346cb4f - 2: Auth router & HttpJwtAuth
115c488 - 1.1-1.2: Setup JWT (requirements + INSTALLED_APPS)
```

Plus Modul 06 commits untuk CRUD endpoints dasar.

## Apa yang Dipelajari

- Web Service vs Web Application
- REST principles & HTTP methods
- Pydantic schemas untuk validation
- CRUD operations
- Query parameters & filtering
- Error handling
- **JWT Token-based Authentication** (Modul 07)
- **Authorization & Access Control** (Modul 07)
- **RBAC - Role-Based Access Control** (Modul 07)
- Auto-generated API documentation
- Django Ninja basics

## Next Steps

- Modul 07: Authentication & Authorization (JWT tokens)
- Modul 08: Advanced filtering & pagination
- Modul 09: Rate limiting & caching
- Deployment ke production

## Troubleshooting

### Container error?
```bash
docker-compose logs app
```

### Migrations failed?
```bash
docker-compose exec app python manage.py migrate --fake-initial
```

### Perlu seed data lagi?
```bash
docker-compose exec app python manage.py seed_data
```

### API tidak respond?
```bash
docker-compose restart app
sleep 5
curl http://localhost:8000/api/v1/hello/
```

## Notes

- Teacher di-hardcode ke user pertama (di Modul 07 akan pakai authentication)
- Ini project belajar, jadi tidak untuk production
- Database di-reset setiap kali docker rebuild
- Linux/Windows user harus adjust docker-compose.yml untuk volume paths

---

**Made for learning. Reference from:** https://classroom.fahrifirdaus.my.id/book/pemrograman-sisi-server/chapter/06-rest-api-dasar/
