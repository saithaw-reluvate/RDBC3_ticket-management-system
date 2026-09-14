# Build context is the REPOSITORY ROOT, not backend/ — see docker-compose.prod.yml.
# config/settings.py resolves REPO_ROOT as two directories above itself
# (config/ -> backend/ -> repo root) to find MEDIA_ROOT, STATIC_ROOT and the
# logs directory (docs/DEPLOYMENT.md §6). Preserving the same backend/
# nesting inside the image, instead of flattening it to /app, keeps that
# path math identical to local dev without touching settings.py.

FROM python:3.12-slim AS builder
WORKDIR /build
RUN python -m venv /venv
ENV PATH="/venv/bin:$PATH"
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/venv/bin:$PATH"
COPY --from=builder /venv /venv

WORKDIR /app/backend
COPY backend/ .

# media/ and staticfiles/ are volume mount points (docker-compose.prod.yml);
# creating them here means the image is self-consistent even if run without
# the named volumes attached (e.g. a one-off `docker run` for debugging).
RUN mkdir -p media staticfiles /app/logs

EXPOSE 8000
ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
