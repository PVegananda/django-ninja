#!/bin/bash

# Docker setup script untuk Modul 07
# Jalankan setelah docker-compose up -d

echo "🐘 Membuat migration untuk Comment model..."
docker-compose exec -T django python manage.py makemigrations courses

echo "🗄️ Menjalankan migrations..."
docker-compose exec -T django python manage.py migrate

echo "👤 Membuat superuser (admin / admin123)..."
docker-compose exec -T django python manage.py shell << EOF
from django.contrib.auth.models import User
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@localhost', 'admin123')
    print("✅ Superuser created: admin / admin123")
else:
    print("✅ Superuser sudah ada")
EOF

echo "🌾 Menjalankan seed data..."
docker-compose exec -T django python manage.py seed_data

echo "✅ Setup selesai! API siap di http://localhost:8000/api/v1/docs"
