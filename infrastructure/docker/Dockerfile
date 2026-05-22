# MAGNATRIX Agentic OS — Production Dockerfile
FROM python:3.11-slim as builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

FROM python:3.11-slim as production
LABEL maintainer="MAGNATRIX-OS" version="1.0.0"
WORKDIR /app
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH
COPY . /app/
RUN groupadd -r magnatrix && useradd -r -g magnatrix magnatrix
RUN chown -R magnatrix:magnatrix /app
USER magnatrix
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')" || exit 1
EXPOSE 8080 8081 8082
ENV PYTHONPATH=/app MAGNATRIX_ENV=production MAGNATRIX_LOG_LEVEL=INFO
CMD ["python", "magnatrix_server.py"]
