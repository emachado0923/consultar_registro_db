FROM python:3.11-slim

# Python runtime settings
ENV PYTHONDONTWRITEBYTECODE=1 \
	PYTHONUNBUFFERED=1 \
	PIP_NO_CACHE_DIR=1 \
	PORT=8080

WORKDIR /app

# Install system updates (no recommends) and clean up
RUN apt-get update \
	&& apt-get install -y --no-install-recommends \
	   ca-certificates \
	&& rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt ./
RUN python -m pip install --upgrade pip \
	&& pip install -r requirements.txt

# Copy application code
COPY . .

# Create non-root user and adjust permissions
RUN groupadd -r appuser && useradd -r -g appuser appuser \
	&& chown -R appuser:appuser /app
USER appuser

# Cloud Run will send traffic to $PORT
EXPOSE 8080

# Use uvicorn directly; enable proxy headers for Cloud Run. Use shell for $PORT expansion.
CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips '*'"]