FROM python:3.11-slim

# System dependencies for PyMuPDF and other packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# NOTE: LaTeX compiler (tectonic/pdflatex) is intentionally NOT installed.
# The /api/tailor-latex endpoint code is preserved but will return a 500
# error if called. This feature is disabled in this build by design.

WORKDIR /app

# Install production Python dependencies
# gunicorn is installed separately — it's not in requirements.txt
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir gunicorn \
    && pip install --no-cache-dir -r requirements.txt

# Copy backend source (excludes venv, .env, __pycache__ via .dockerignore)
COPY . .

EXPOSE 8001

# Production server: gunicorn with 4 async uvicorn workers
CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "main:app", "--bind", "0.0.0.0:8001", "--timeout", "120", "--access-logfile", "-"]
