.DEFAULT_GOAL := help

.PHONY: help bootstrap up down restart destroy logs format lint test check

AIRFLOW_DIR := airflow
COMPOSE_FILE := infrastructure/docker/docker-compose.yml
DOCKER_COMPOSE := docker compose -f $(COMPOSE_FILE)

help:
	@echo ""
	@echo "Modern Data Platform"
	@echo ""
	@echo "Infrastructure"
	@echo "  make up         Start the platform"
	@echo "  make down       Stop containers"
	@echo "  make restart    Restart containers"
	@echo "  make destroy    Stop containers and remove volumes"
	@echo "  make logs       Follow container logs"
	@echo ""
	@echo "Development"
	@echo "  make format     Format code"
	@echo "  make lint       Run lint"
	@echo "  make test       Run tests"
	@echo "  make check      Run lint and tests"
	@echo ""

bootstrap:
	@echo "==> Preparing Airflow directories..."
	@mkdir -p $(AIRFLOW_DIR)/logs
	@chmod 775 $(AIRFLOW_DIR)/logs

up: bootstrap
	$(DOCKER_COMPOSE) up -d

down:
	$(DOCKER_COMPOSE) down

restart:
	$(DOCKER_COMPOSE) restart

destroy:
	$(DOCKER_COMPOSE) down -v

logs:
	$(DOCKER_COMPOSE) logs -f

format:
	uv run ruff format .

lint:
	uv run ruff check .

test:
	uv run pytest

check: lint test