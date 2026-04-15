FROM python:3.12-slim AS base

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# System deps for Pillow (libjpeg, zlib, etc. are in python:slim already)
RUN apt-get update && \
    apt-get install -y --no-install-recommends tini && \
    rm -rf /var/lib/apt/lists/*

# Non-root user
RUN groupadd -r hoppers && useradd -r -g hoppers -d /app -s /sbin/nologin hoppers

WORKDIR /app

# Install Python deps first (layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Copy application code
COPY hop_emote.py .
COPY web/ web/

# Temp directory for uploads/outputs – mountable as volume
# TMPDIR tells Python's stdlib tempfile to use this dir too (read-only FS compat)
ENV HOPPERS_TMP=/app/tmp \
    TMPDIR=/app/tmp
RUN mkdir -p /app/tmp && chown hoppers:hoppers /app/tmp

USER hoppers

EXPOSE 5000

# tini handles PID 1 + signal forwarding for clean shutdown
ENTRYPOINT ["tini", "--"]

CMD ["gunicorn", \
     "--bind", "0.0.0.0:5000", \
     "--workers", "2", \
     "--timeout", "120", \
     "--worker-tmp-dir", "/app/tmp", \
     "--access-logfile", "-", \
     "web.app:app"]
