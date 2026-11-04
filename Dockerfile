# syntax=docker/dockerfile:1@sha256:4edf897a3ffa55b89f906fc8cc78afdb3f1834cc9c7083565e611a8a7d5fe99e
FROM python:3.13-slim-bookworm@sha256:281d39ff02e3b389401586134ff9e6572954687822a58055ec07a60ded4e0b7f AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app
COPY requirements.lock ./
RUN pip install --no-cache-dir -r requirements.lock
COPY src/ ./src/
COPY scripts/container_model.py ./scripts/container_model.py
RUN python -m scripts.container_model --output /app/builtin/demo.joblib
COPY dashboard.py ./
COPY .streamlit/ ./.streamlit/
COPY reports/ ./reports/
ARG APP_UID=1000
RUN useradd --create-home --uid ${APP_UID} trustshield && mkdir /app/runtime && chown trustshield:trustshield /app/runtime
ENV TRUSTSHIELD_MODEL_PATH=/app/builtin/demo.joblib TRUSTSHIELD_DATA_DIR=/app/runtime
USER trustshield
EXPOSE 8000 8501
CMD ["python", "-m", "uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "8000", "--no-proxy-headers", "--no-access-log", "--limit-concurrency", "32"]

FROM base AS ci
COPY tests/ ./tests/
COPY config/ ./config/
COPY docs/ ./docs/
COPY scripts/ci_verify.py ./scripts/ci_verify.py
RUN python -m scripts.ci_verify

FROM base AS runtime
