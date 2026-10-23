.DEFAULT_GOAL := help

.PHONY: help
help: ## Вывести список доступных команд
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

.PHONY: dev
dev: ## Запустить локальный стек разработки в Docker Compose
	docker compose -f deploy/docker-compose.yml up -d
	@echo "Dev стек запущен: API -> http://localhost:8000, MinIO Console -> http://localhost:9001, Mailhog -> http://localhost:8025"

.PHONY: down
down: ## Остановить все локальные контейнеры
	docker compose -f deploy/docker-compose.yml down

.PHONY: clean
clean: ## Остановить контейнеры и удалить все постоянные тома данных (volumes)
	docker compose -f deploy/docker-compose.yml down -v

.PHONY: migrate
migrate: ## Применить все миграции базы данных Alembic
	cd backend && uv run alembic upgrade head

.PHONY: migrate-create
migrate-create: ## Создать новую миграцию Alembic: make migrate-create name=migration_name
	cd backend && uv run alembic revision --autogenerate -m "$(name)"

.PHONY: seed
seed: ## Наполнить базу данных тестовыми данными для разработки
	cd backend && uv run python ../scripts/seed_dev_data.py

.PHONY: lint-md
lint-md: ## Проверить markdown документацию
	markdownlint "**/*.md" --ignore node_modules

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

.PHONY: check-compose
check-compose: ## Проверить валидность конфигураций Docker Compose
	docker compose -f deploy/docker-compose.yml config --quiet
	docker compose -f deploy/docker-compose.prod.yml config --quiet

.PHONY: gate
gate: ## Полный прогон пайплайна качества перед коммитом
	@echo "=== [1/6] Проверка Markdown документации ==="
	$(MAKE) lint-md
	@echo "=== [2/6] Статический анализ и форматирование Python ==="
	$(MAKE) lint-py
	$(MAKE) format-py
	@echo "=== [3/6] Строгая типизация Python (mypy --strict) ==="
	$(MAKE) typecheck-py
	@echo "=== [4/6] Юнит и интеграционные тесты Python ==="
	$(MAKE) test-py
	@echo "=== [5/6] Проверка, типизация и сборка Frontend ==="
	$(MAKE) lint-frontend
	$(MAKE) typecheck-frontend
	$(MAKE) test-frontend
	$(MAKE) build-frontend
	@echo "=== [6/6] Валидация Docker Compose манифестов ==="
	$(MAKE) check-compose
	@echo "\033[32m>>> Все проверки make gate успешно пройдены! <<< \033[0m"
