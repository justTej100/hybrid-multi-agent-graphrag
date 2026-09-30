.PHONY: help run app backend install venv stop test test-integration frontend frontend-dev

APP_PORT := 8000
APP_URL := http://localhost:$(APP_PORT)

ifeq ($(OS),Windows_NT)
VENV_BIN := .venv/Scripts
PY := py -3
else
VENV_BIN := .venv/bin
PY := python3
endif

PYTHON := $(VENV_BIN)/python
PIP := $(VENV_BIN)/pip
UVICORN := $(VENV_BIN)/uvicorn
PYTEST := $(VENV_BIN)/pytest
NPM := npm

help:
	@echo "Argus Study Buddy"
	@echo "make install            - Python venv + pip dependencies"
	@echo "make frontend           - npm install + build React UI"
	@echo "make frontend-dev       - Vite dev server (proxies API to :8000)"
	@echo "make app                - build frontend + run FastAPI ($(APP_URL))"
	@echo "make test               - fast pytest suite (no Docker)"
	@echo "make test-integration   - Docker Postgres+Neo4j, then integration tests"
	@echo "make stop               - stop services on port $(APP_PORT)"

$(PYTHON):
	@echo "Creating virtualenv in .venv..."
	@$(PY) -m venv .venv
	@$(PYTHON) -m pip install --upgrade pip

venv: $(PYTHON)

install: venv
	@echo "Installing Python dependencies..."
	@$(PIP) install -r src/backend/requirements.txt

frontend:
	@echo "Building React frontend..."
	@cd src/frontend && $(NPM) install && $(NPM) run build

frontend-dev:
	@cd src/frontend && $(NPM) install && $(NPM) run dev

app: install frontend
	@echo "Starting Argus on $(APP_URL)..."
	@$(UVICORN) api.main:app --app-dir src/backend --reload --port $(APP_PORT)

backend: app
run: app

test: venv
	@$(PYTEST) -v

test-integration: venv
	docker compose -f docker-compose.test.yml up -d --wait
	@$(PYTEST) -m integration -o addopts= -v; status=$$?; docker compose -f docker-compose.test.yml down -v; exit $$status

stop:
	@-lsof -ti :$(APP_PORT) | xargs kill -9 2>/dev/null || true
