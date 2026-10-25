FROM python:3.12-slim

# Don't write .pyc files, flush logs straight to the console
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies first so Docker can cache this layer
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Run as a non-root user (good DevOps practice)
RUN useradd -m appuser
USER appuser

EXPOSE 5000

# 1 worker + threads so the DB table is created only once at startup
CMD ["gunicorn", "-w", "1", "--threads", "4", "-b", "0.0.0.0:5000", "app:app"]
