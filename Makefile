.DEFAULT_GOAL := help

.PHONY: help
help: ## Вывести список доступных команд
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

.PHONY: dev
dev: ## Запустить локальный стек разработки в Docker Compose
	DOCKER_BUILDKIT=1 docker compose -f deploy/docker-compose.yml up -d
	@echo "Dev стек запущен: API -> http://localhost:8000, MinIO Console -> http://localhost:9001, Mailhog -> http://localhost:8025"

.PHONY: dev-fast
dev-fast: ## Запустить стек в режиме быстрой разработки (DEV_FAST_MODE=true, без лимитов, вход catishe@gmail.com)
	DEV_FAST_MODE=true DOCKER_BUILDKIT=1 docker compose -f deploy/docker-compose.yml up -d
	@echo "Dev-Fast стек запущен: автоматический вход catishe@gmail.com PRO, безлимитная загрузка"

.PHONY: dev-prod
dev-prod: ## Запустить стек в реалистичном Production-режиме (тарифы, 2-стр. превью, OTP на почту)
	DEV_FAST_MODE=false DOCKER_BUILDKIT=1 docker compose -f deploy/docker-compose.yml up -d
	@echo "Prod-Simulation стек запущен: гостевой лимит 2 стр., проверка OTP через Mailhog"

.PHONY: down
down: ## Остановить все локальные контейнеры
	docker compose -f deploy/docker-compose.yml down

.PHONY: clean
clean: ## Остановить контейнеры и удалить все постоянные тома данных (volumes)
	docker compose -f deploy/docker-compose.yml down -v

.PHONY: clean-all
clean-all: ## Остановить контейнеры, удалить тома и очистить кэш сборщика Docker
	docker compose -f deploy/docker-compose.yml down -v
	docker builder prune -af

.PHONY: build-fast
build-fast: ## Быстрая сборка Docker-образов с BuildKit и cache mount
	DOCKER_BUILDKIT=1 docker build -f backend/Dockerfile.api -t local/cleandoc-api:dev ./backend
	DOCKER_BUILDKIT=1 docker build -f backend/Dockerfile.worker -t local/cleandoc-worker:dev ./backend
	DOCKER_BUILDKIT=1 docker build -f frontend/Dockerfile -t local/cleandoc-frontend:dev ./frontend

.PHONY: migrate
migrate: ## Применить все миграции базы данных Alembic
	cd backend && uv run alembic upgrade head

.PHONY: migrate-create
migrate-create: ## Создать новую миграцию Alembic: make migrate-create name=migration_name
	cd backend && uv run alembic revision --autogenerate -m "$(name)"

.PHONY: seed
seed: ## Наполнить базу данных тестовыми данными для разработки (идемпотентно)
	cd backend && uv run python ../scripts/seed_dev_data.py

.PHONY: worker
worker: ## Запустить фоновый воркер RQ локально
	cd backend && uv run python -m app.workers.worker

.PHONY: lint-md
lint-md: ## Проверить markdown документацию
	npx markdownlint-cli "**/*.md" --ignore node_modules --ignore frontend/node_modules

.PHONY: lint-py
lint-py: ## Запустить линтинг Python кода (Ruff)
	cd backend && uv run ruff check app tests

.PHONY: format-py
format-py: ## Проверить форматирование Python кода (Ruff)
	cd backend && uv run ruff format --check app tests

.PHONY: format-py-fix
format-py-fix: ## Автоматически исправить форматирование Python кода
	cd backend && uv run ruff format app tests
	cd backend && uv run ruff check --fix app tests

.PHONY: typecheck-py
typecheck-py: ## Строгая проверка типов Python (mypy)
	cd backend && uv run mypy --strict app

.PHONY: test-py
test-py: ## Запустить тесты Python (pytest)
	cd backend && uv run pytest -v tests

.PHONY: lint-frontend
lint-frontend: ## Проверить линтинг фронтенда (Next.js ESLint)
	cd frontend && npm run lint

.PHONY: typecheck-frontend
typecheck-frontend: ## Проверить типизацию фронтенда (TypeScript)
	cd frontend && npm run typecheck

.PHONY: test-frontend
test-frontend: ## Запустить тесты фронтенда (Vitest / Jest)
	cd frontend && npm run test

.PHONY: build-frontend
build-frontend: ## Проверить продакшн сборку фронтенда
	cd frontend && npm run build

.PHONY: audit-fe
audit-fe: ## Проверить продакшн зависимости фронтенда на уязвимости (npm audit)
	cd frontend && npm run audit:check

.PHONY: check-compose
check-compose: ## Проверить валидность конфигураций Docker Compose
	docker compose -f deploy/docker-compose.yml config --quiet
	docker compose -f deploy/docker-compose.prod.yml config --quiet

.PHONY: gate
gate: ## Полный прогон пайплайна качества перед коммитом
	@echo "=== [1/7] Проверка Markdown документации ==="
	$(MAKE) lint-md
	@echo "=== [2/7] Статический анализ и форматирование Python ==="
	$(MAKE) lint-py
	$(MAKE) format-py
	@echo "=== [3/7] Строгая типизация Python (mypy --strict) ==="
	$(MAKE) typecheck-py
	@echo "=== [4/7] Юнит и интеграционные тесты Python ==="
	$(MAKE) test-py
	@echo "=== [5/7] Проверка, типизация и сборка Frontend ==="
	$(MAKE) lint-frontend
	$(MAKE) typecheck-frontend
	$(MAKE) test-frontend
	$(MAKE) build-frontend
	@echo "=== [6/7] Проверка безопасности зависимостей Frontend (npm audit) ==="
	$(MAKE) audit-fe
	@echo "=== [7/7] Валидация Docker Compose манифестов ==="
	$(MAKE) check-compose
	@echo "\033[32m>>> Все проверки make gate успешно пройдены! <<< \033[0m"
