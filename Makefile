# EDO-Adapter Enterprise — Developer Makefile
# Ports: API=8099, Postgres=5499, Redis=6399, Flower=5599, Grafana=3099

.PHONY: setup up down test lint format seed logs clean

COMPOSE = docker compose -f docker/docker-compose.yml
PYTHON   = python
APP_SRC  = src

# ─────────────────────────────────────────────────────────────────────────────
# setup — full project bootstrap after cloning
# ─────────────────────────────────────────────────────────────────────────────
setup:
	@echo "→ Creating virtualenv..."
	$(PYTHON) -m venv .venv
	@echo "→ Installing dependencies..."
	.venv/Scripts/pip install -e ".[dev]"
	@echo "→ Copying .env..."
	@powershell -Command "if (-not (Test-Path .env)) { Copy-Item .env.example .env }"
	@echo "→ Starting full stack (API, Worker, Postgres, Redis, Grafana, ...)..."
	$(COMPOSE) up -d
	@echo "→ Waiting for Postgres to be ready..."
	powershell -Command "Start-Sleep -Seconds 10"
	@echo "→ Running Alembic migrations..."
	.venv/Scripts/alembic upgrade head
	@echo "→ Seeding demo users..."
	.venv/Scripts/python -m src.scripts.seed_demo_users
	@echo ""
	@echo "✓ Setup complete — full stack is running!"
	@echo "  API:        http://localhost:8099/api/docs"
	@echo "  Grafana:    http://localhost:3099  (admin/admin)"
	@echo "  Flower:     http://localhost:5599"
	@echo "  Prometheus: http://localhost:9099"
	@echo "  Postgres:   localhost:5499"
	@echo "  Redis:      localhost:6399"

# ─────────────────────────────────────────────────────────────────────────────
# up / down — start and stop the full Docker stack
# ─────────────────────────────────────────────────────────────────────────────
up:
	$(COMPOSE) up -d
	@echo "✓ Stack is up"
	@echo "  API:        http://localhost:8099/api/docs"
	@echo "  Grafana:    http://localhost:3099  (admin/admin)"
	@echo "  Flower:     http://localhost:5599"
	@echo "  Prometheus: http://localhost:9099"

down:
	$(COMPOSE) down
	@echo "✓ Stack stopped"

# ─────────────────────────────────────────────────────────────────────────────
# test — run the full test suite with coverage
# ─────────────────────────────────────────────────────────────────────────────
test:
	.venv/Scripts/pytest tests/ -v --tb=short

# Run only unit tests (faster, no infra needed)
test-unit:
	.venv/Scripts/pytest tests/unit/ -v

# Run only integration tests
test-integration:
	.venv/Scripts/pytest tests/integration/ -v

# Run e2e tests
test-e2e:
	.venv/Scripts/pytest tests/e2e/ -v

# ─────────────────────────────────────────────────────────────────────────────
# lint / format
# ─────────────────────────────────────────────────────────────────────────────
lint:
	.venv/Scripts/ruff check $(APP_SRC) tests/
	.venv/Scripts/mypy $(APP_SRC)

format:
	.venv/Scripts/ruff format $(APP_SRC) tests/
	.venv/Scripts/ruff check --fix $(APP_SRC) tests/

# ─────────────────────────────────────────────────────────────────────────────
# migrations
# ─────────────────────────────────────────────────────────────────────────────
migrate:
	.venv/Scripts/alembic upgrade head

migration:
	@echo "Usage: make migration name='your migration message'"
	.venv/Scripts/alembic revision --autogenerate -m "$(name)"

# ─────────────────────────────────────────────────────────────────────────────
# seed
# ─────────────────────────────────────────────────────────────────────────────
seed:
	.venv/Scripts/python -m src.scripts.seed_demo_users

# ─────────────────────────────────────────────────────────────────────────────
# logs
# ─────────────────────────────────────────────────────────────────────────────
logs:
	$(COMPOSE) logs -f api worker

logs-api:
	$(COMPOSE) logs -f api

logs-worker:
	$(COMPOSE) logs -f worker

# ─────────────────────────────────────────────────────────────────────────────
# dev — run API locally (requires infra via make up)
# ─────────────────────────────────────────────────────────────────────────────
dev:
	.venv/Scripts/uvicorn src.main:app --host 0.0.0.0 --port 8099 --reload

dev-worker:
	.venv/Scripts/celery -A src.infrastructure.queue.celery_app worker \
		-Q edo.send,edo.sync,edo.webhooks,edo.dlq,edo.health \
		-c 4 --loglevel=info

# ─────────────────────────────────────────────────────────────────────────────
# clean — remove generated artefacts
# ─────────────────────────────────────────────────────────────────────────────
clean:
	$(COMPOSE) down -v
	@powershell -Command "if (Test-Path .venv) { Remove-Item -Recurse -Force .venv }"
	@powershell -Command "if (Test-Path .pytest_cache) { Remove-Item -Recurse -Force .pytest_cache }"
	@powershell -Command "if (Test-Path htmlcov) { Remove-Item -Recurse -Force htmlcov }"
	@echo "✓ Cleaned"
