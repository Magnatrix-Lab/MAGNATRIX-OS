FROM python:3.11-slim

WORKDIR /app

# Install minimal system deps
RUN apt-get update -qq && \
    apt-get install -y -qq curl git && \
    rm -rf /var/lib/apt/lists/*

# Copy source
COPY . /app/

# Set environment
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV MAGNATRIX_ENV=production

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8080/api/status || exit 1

EXPOSE 8080 8081

ENTRYPOINT ["python", "magnatrix.py"]
CMD ["start", "--port", "8080"]
