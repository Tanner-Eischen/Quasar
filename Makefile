.PHONY: help install dev test lint format clean db-up db-down ingest run-api run-ui

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install production dependencies
	pip install -e .

dev: ## Install development dependencies
	pip install -e ".[dev]"
	pre-commit install

test: ## Run all tests
	pytest tests/ -v

test-cov: ## Run tests with coverage
	pytest tests/ --cov=src/legacylens --cov-report=html --cov-report=term

lint: ## Run linters (ruff, mypy)
	ruff check src/ tests/
	mypy src/

format: ## Format code (black, ruff)
	black src/ tests/
	ruff check src/ tests/ --fix

clean: ## Clean build artifacts
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov/ .coverage

db-up: ## Start database with Docker Compose
	docker-compose up -d db
	@echo "Database running on localhost:5432"
	@echo "Waiting for database to be ready..."
	@sleep 3

db-down: ## Stop database
	docker-compose down

db-reset: ## Reset database (WARNING: destroys data)
	docker-compose down -v
	docker-compose up -d db

db-migrate: ## Run database migrations
	alembic upgrade head

db-revision: ## Create new migration
	alembic revision --autogenerate -m "$(MSG)"

ingest: ## Ingest corpus (usage: make ingest TAG=nshm2014r1)
	python scripts/ingest_corpus.py --tag $(or $(TAG),nshm2014r1)

run-api: ## Run FastAPI server
	uvicorn src.legacylens.api.main:app --reload --host 0.0.0.0 --port 8000

run-ui: ## Run Streamlit UI
	streamlit run ui/app.py

docker-build: ## Build Docker images
	docker-compose build

docker-up: ## Start all services with Docker
	docker-compose up -d

docker-down: ## Stop all Docker services
	docker-compose down

docker-logs: ## Show Docker logs
	docker-compose logs -f

eval: ## Run evaluation suite
	python eval/run_eval.py

setup-corpus: ## Clone and checkout corpus repository
	git clone https://github.com/usgs/nshmp-haz-fortran.git corpus/
	cd corpus && git checkout nshm2014r1

check: lint test ## Run all checks (lint + test)
