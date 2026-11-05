FROM python:3.11-slim

COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /usr/local/bin/uv
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PYTHONUNBUFFERED=1 \
    DB_PATH=/data/value_scanner.db

# dependencies first (cached layer); no dev tools, no browser
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev --no-install-project

COPY value_scanner ./value_scanner
COPY docs ./docs

# Railway mounts the volume at /data and sets PORT
VOLUME /data
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import os,urllib.request as u; u.urlopen('http://127.0.0.1:%s/api/health' % os.environ.get('PORT','8000'), timeout=4)"
CMD ["sh", "-c", ".venv/bin/python -m value_scanner serve --host 0.0.0.0 --port ${PORT:-8000}"]
