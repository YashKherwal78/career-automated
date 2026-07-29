FROM mcr.microsoft.com/playwright/python:v1.45.0-jammy

WORKDIR /app

# Install system dependencies.
# texlive packages here are the minimal set covering Jake's Resume template's
# actual \usepackage list (latexsym, fullpage, titlesec, enumitem, hyperref,
# fancyhdr, babel, tabularx, xcolor) — not texlive-full, to keep the image
# reasonably sized and the build fast.
# DEBIAN_FRONTEND=noninteractive + TZ avoid tzdata (pulled in transitively by
# texlive) blocking the build on an interactive timezone prompt.
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC
RUN apt-get update && apt-get install -y \
    sqlite3 \
    texlive-latex-base \
    texlive-latex-recommended \
    texlive-latex-extra \
    texlive-fonts-recommended \
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
CMD ["python3", "src/workers/mass_scheduler.py"]
