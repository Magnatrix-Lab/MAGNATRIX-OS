"""
infrastructure/ci-cd/full_automation.py
========================================
MAGNATRIX CI/CD Full Automation Pipeline

GitHub Actions workflows + pre-commit hooks + release automation.
"""

CI_YAML = r"""
name: MAGNATRIX CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 0 * * *'  # Daily at midnight

env:
  PYTHON_VERSION: '3.11'
  REGISTRY: ghcr.io
  IMAGE_NAME: magnatrix/os

jobs:
  # ====== Stage 1: Lint & Format ======
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with: {python-version: '${{ env.PYTHON_VERSION }}'}
      - run: pip install ruff black mypy
      - run: ruff check . --select E,W,F,I
      - run: black --check .
      - run: mypy collective-brain/ api-router/ trading/ knowledge/ --ignore-missing-imports

  # ====== Stage 2: Unit Tests ======
  test:
    runs-on: ubuntu-latest
    needs: lint
    services:
      postgres:
        image: ankane/pgvector:latest
        env:
          POSTGRES_PASSWORD: testpass
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports: ['5432:5432']
      redis:
        image: redis:7-alpine
        ports: ['6379:6379']
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with: {python-version: '${{ env.PYTHON_VERSION }}'}
      - run: pip install -r requirements.txt pytest pytest-asyncio pytest-cov
      - run: pytest tests/ --cov=. --cov-report=xml -v
      - uses: codecov/codecov-action@v3
        with: {files: ./coverage.xml}

  # ====== Stage 3: Integration Tests ======
  integration:
    runs-on: ubuntu-latest
    needs: test
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with: {python-version: '${{ env.PYTHON_VERSION }}'}
      - run: pip install -r requirements.txt
      - run: python tests/integration/layer_integration_orchestrator.py
      - run: python tests/comprehensive_test_suite.py

  # ====== Stage 4: Security Scan ======
  security:
    runs-on: ubuntu-latest
    needs: test
    steps:
      - uses: actions/checkout@v4
      - run: pip install bandit safety
      - run: bandit -r . -f json -o bandit-report.json || true
      - run: safety check --json || true

  # ====== Stage 5: Build Docker Image ======
  build:
    runs-on: ubuntu-latest
    needs: [lint, test, integration, security]
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - uses: docker/build-push-action@v5
        with:
          context: .
          file: infrastructure/docker/Dockerfile
          push: ${{ github.ref == 'refs/heads/main' }}
          tags: |
            ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:latest
            ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

  # ====== Stage 6: Deploy ke Hostinger ======
  deploy:
    runs-on: ubuntu-latest
    needs: build
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4
      - name: Deploy ke Hostinger VPS
        run: |
          ssh -o StrictHostKeyChecking=no ${{ secrets.HOSTINGER_USER }}@${{ secrets.HOSTINGER_HOST }} << 'EOF'
            cd /opt/magnatrix
            docker-compose -f infrastructure/docker/docker-compose.prod.yml pull
            docker-compose -f infrastructure/docker/docker-compose.prod.yml up -d
            docker system prune -f
          EOF
        env:
          HOSTINGER_USER: ${{ secrets.HOSTINGER_USER }}
          HOSTINGER_HOST: ${{ secrets.HOSTINGER_HOST }}
          DB_PASSWORD: ${{ secrets.DB_PASSWORD }}
"""

RELEASE_YAML = r"""
name: Release Automation

on:
  push:
    tags: ['v*']

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Generate Release Notes
        run: |
          echo "## MAGNATRIX Release ${{ github.ref_name }}" > release_notes.md
          echo "" >> release_notes.md
          git log $(git describe --tags --abbrev=0 HEAD^)..HEAD --oneline >> release_notes.md
      - uses: softprops/action-gh-release@v1
        with:
          body_path: release_notes.md
          files: |
            LICENSE
            README.md
"""

if __name__ == "__main__":
    import os
    os.makedirs('/mnt/agents/MAGNATRIX-OS/.github/workflows', exist_ok=True)

    with open('/mnt/agents/MAGNATRIX-OS/.github/workflows/magnatrix-full-ci.yml', 'w') as f:
        f.write(CI_YAML)
    print("CI/CD workflow written")

    with open('/mnt/agents/MAGNATRIX-OS/.github/workflows/release.yml', 'w') as f:
        f.write(RELEASE_YAML)
    print("Release workflow written")
