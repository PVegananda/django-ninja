FROM python:3.11-slim

WORKDIR /code

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python packages
COPY code/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy Django project
COPY code /code/

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
