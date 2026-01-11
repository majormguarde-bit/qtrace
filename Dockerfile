# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    python3-dev \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy project
COPY . /app/

# Create staticfiles directory
RUN mkdir -p /app/staticfiles

# Make entrypoint script executable
COPY entrypoint.sh /app/
RUN chmod +x /app/entrypoint.sh

# Run entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]
