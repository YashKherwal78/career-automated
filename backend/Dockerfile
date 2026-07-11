FROM mcr.microsoft.com/playwright/python:v1.45.0-jammy

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Ensure playwright browsers are fully installed
RUN playwright install --with-deps chromium

# Copy the rest of the application
COPY . .
RUN mkdir -p /app/data

# Environment setup
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# API port
EXPOSE 8000

# The frontend is deployed separately. Runtime data is supplied via a mounted
# /app/data volume rather than included in this image.
CMD ["python3", "-m", "uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
