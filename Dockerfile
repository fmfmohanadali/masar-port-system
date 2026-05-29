FROM python:3.12-slim AS builder
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --prefix=/install -r /app/requirements.txt

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
RUN groupadd -r masar && useradd -r -g masar masar
WORKDIR /app
COPY --from=builder /install /usr/local
COPY . /app
RUN chown -R masar:masar /app && \
    mkdir -p /app/backend/media/qr_codes && \
    mkdir -p /app/backend/staticfiles && \
    chown -R masar:masar /app/backend/media && \
    chown -R masar:masar /app/backend/staticfiles
WORKDIR /app/backend
RUN python manage.py collectstatic --noinput 2>/dev/null || true
USER masar
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health/')" || exit 1
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120"]
