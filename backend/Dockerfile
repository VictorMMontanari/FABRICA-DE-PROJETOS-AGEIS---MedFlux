FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Processo sem privilégios de root.
RUN useradd --create-home --uid 10001 medflux
USER medflux

EXPOSE 5000

HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/healthz', timeout=3)"

# Migrations + seed idempotente antes de subir a API.
CMD ["sh", "-c", "alembic upgrade head && python -m app.seed && exec uvicorn app.main:create_app --factory --host 0.0.0.0 --port 5000 --proxy-headers"]
