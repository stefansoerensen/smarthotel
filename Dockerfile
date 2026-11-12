# syntax=docker/dockerfile:1

# ---------- stage 1: build the frontend ----------
FROM node:20-slim AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---------- stage 2: the runtime ----------
FROM python:3.11-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    STATIC_DIR=/app/static
WORKDIR /app

COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app
COPY backend/alembic ./alembic
COPY backend/alembic.ini ./alembic.ini
COPY --from=frontend /build/dist ./static

RUN useradd --create-home --uid 10001 --shell /usr/sbin/nologin app \
    && chown -R app:app /app
USER app

EXPOSE 8000
# The platform injects PORT. `sh -c` is needed to expand it; `exec` keeps uvicorn as PID 1 so
# SIGTERM reaches it.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
