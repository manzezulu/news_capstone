FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
 PYTHONUNBUFFERED=1
WORKDIR /app
# System libraries needed to build the MariaDB driver (mysqlclient)
RUN apt-get update && apt-get install -y --no-install-recommends \
 build-essential pkg-config default-libmysqlclient-dev \
 && rm -rf /var/lib/apt/lists/*
# Install dependencies first so Docker can cache this layer
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["sh", "-c", "python manage.py migrate && python manage.py runserver 0.0.0.0:8000"]