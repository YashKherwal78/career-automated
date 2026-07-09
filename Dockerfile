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

# Environment setup
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# By default, we expose Streamlit port
EXPOSE 8501

# The default command will be to run the health check, then start the cron loop
# Alternatively, users can override this to start the dashboard
CMD ["bash", "-c", "python3 src/system/health_check.py && python3 src/production/main_cron.py"]
