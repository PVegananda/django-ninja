![Django](https://img.shields.io/badge/Django-5.0-darkgreen?style=for-the-badge&logo=django)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-blue?style=for-the-badge&logo=postgresql)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker)
![Python](https://img.shields.io/badge/Python-3.11-blue?style=for-the-badge&logo=python)

# Django Ninja - Simple LMS API

REST API untuk Simple Learning Management System menggunakan Django Ninja. Project ini adalah praktik modul 06 dari Pemrograman Sisi Server.

## Apa ini?

Ini project untuk belajar cara bikin REST API yang proper. Pake Django Ninja yang lebih modern dibanding DRF, dengan type hints dan otomatis documentation.

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

### Courses
- `GET /api/v1/courses/` - List semua courses
- `GET /api/v1/courses/?search=python` - Cari courses
- `GET /api/v1/courses/?min_price=50000&max_price=100000` - Filter harga
- `GET /api/v1/courses/{id}` - Detail course + contents
- `POST /api/v1/courses/` - Buat course baru
- `PUT /api/v1/courses/{id}` - Update course
- `DELETE /api/v1/courses/{id}` - Hapus course

### Contents
- `GET /api/v1/contents/` - List contents
- `GET /api/v1/contents/?course_id=1` - Filter by course
- `GET /api/v1/contents/{id}` - Detail content
- `POST /api/v1/contents/` - Buat content
- `PUT /api/v1/contents/{id}` - Update content
- `DELETE /api/v1/contents/{id}` - Hapus content

### Documentation
- `GET /api/v1/docs` - Swagger UI (best untuk testing)
- `GET /api/v1/openapi.json` - OpenAPI schema

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
│   ├── apiv1.py          # API endpoints definition
│   ├── schemas.py        # Pydantic schemas (input/output validation)
│   ├── models.py         # Django models (Course, Content, dll)
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
✅ **Auto Docs** - Swagger UI generated otomatis  
✅ **Validation** - Pydantic schemas handle validation  
✅ **CRUD Ready** - 10 endpoints siap pakai  
✅ **Query Params** - Search, filter, sorting built-in  
✅ **Error Handling** - Proper HTTP status codes  
✅ **Optimized** - select_related & prefetch_related  
✅ **Nested Data** - Relasi Course → Teacher, Course → Contents  

## Database

PostgreSQL running di container. Default credentials di `docker-compose.yml`:
- User: `postgres`
- Password: `postgres`
- Database: `lms_db`
- Port: `5436`

Sudah ada 100+ courses dengan teacher dan content data ready.

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

## Commits

Project ini dibuat step-by-step dengan jelas commit history:

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
