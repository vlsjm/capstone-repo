# ---------- Stage 1: Builder ----------
FROM python:3.10.13-slim AS builder

WORKDIR /app

# Install system dependencies required for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies into a virtual env so we can copy it cleanly
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---------- Stage 2: Runtime ----------
FROM python:3.10.13-slim

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install only the runtime system libraries (no compilers)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy pre-built Python packages from the builder stage
COPY --from=builder /install /usr/local

# Copy the entire project
COPY . .

# Collect static files (uses whitenoise, no DB needed)
RUN python manage.py collectstatic --noinput 2>/dev/null || true

# Create a non-root user for security
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser \
    && mkdir -p /app/media /app/staticfiles \
    && touch /app/debug.log \
    && chown -R appuser:appgroup /app/media /app/staticfiles /app/debug.log

# Make the entrypoint script executable
RUN chmod +x /app/entrypoint.sh

USER appuser

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
