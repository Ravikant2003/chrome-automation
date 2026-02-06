# app/Dockerfile

FROM python:3.11-slim

WORKDIR /app

# System deps (minimal)
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy project
COPY . /app

# Install Python deps
RUN pip install --no-cache-dir -r requirements.txt

# Output directory (only thing we really need)
RUN mkdir -p /app/output

# Environment variable (useful but optional)
ENV PYTHONUNBUFFERED=1

CMD ["python", "app/main.py"]
