# RiskSure API image. Built from the repo root because the API needs config/,
# data/ (rule previews, seeding) and models/ (the trained auto model) as well
# as backend/.
FROM python:3.12.2-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dependencies first, so code changes don't reinstall them.
COPY backend/requirements.lock backend/requirements.lock
RUN pip install -r backend/requirements.lock

COPY config/ config/
COPY data/ data/
COPY models/ models/
COPY backend/ backend/

# Run as a non-root user; the SQLite file lives in backend/.
RUN useradd --create-home app && chown -R app /app/backend
USER app

WORKDIR /app/backend
EXPOSE 8000
# Render (and most hosts) set $PORT; default to 8000 locally.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
