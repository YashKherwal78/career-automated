FROM python:3.11-slim

# Prevent interactive prompts during apt installations
ENV DEBIAN_FRONTEND=noninteractive

# Install LaTeX and timezone data
RUN apt-get update && apt-get install -y \
    texlive-latex-base \
    texlive-fonts-recommended \
    texlive-latex-extra \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# Set local timezone so that schedule triggers at the correct time in IST
ENV TZ="Asia/Kolkata"

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all source files
COPY . .

# Run the autonomous scheduler
CMD ["python3", "src/autonomous.py"]
