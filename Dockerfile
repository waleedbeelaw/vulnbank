# VulnBank Flask application — development/demo image
FROM python:3.12-slim

# Run as a dedicated non-root user (not root).
RUN groupadd --gid 1000 vulnbank \
    && useradd --uid 1000 --gid vulnbank --create-home --shell /bin/bash vulnbank

WORKDIR /app

# Install dependencies first for better layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application source (secrets and .env are excluded via .dockerignore).
COPY . .

RUN chmod +x docker/entrypoint.sh \
    && chown -R vulnbank:vulnbank /app

USER vulnbank

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/health', timeout=3)" || exit 1

ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["python", "run.py"]
