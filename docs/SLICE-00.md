# SLICE-00: Foundation — Спецификация реализации

> **Статус:** Действующий / Ready for Implementation
> **Версия:** v0.1
> **Дата:** 15 октября 2026 г.
> **Спринт:** 1 (Дни 1–14)
> **Зависимости:** [`docs/TECH.md`](./TECH.md) (SSOT), [`AGENTS.md`](../AGENTS.md) (Регламент)

---

## 0. Цель и Definition of Done (DoD)

**Цель Slice 0:** развернуть фундамент монорепозитория проекта «Чистый документ», единую локальную инфраструктуру в Docker Compose (PostgreSQL 18, Redis 7.2, MinIO, Mailhog), автоматизированный пайплайн контроля качества `make gate`, асинхронное ядро FastAPI со служебными эндпоинтами проверки жизнеспособности (`/health`, `/ready`), базовые ORM-модели данных SQLAlchemy 2.0 с миграцией Alembic и скелет клиентского приложения Next.js 14.

### Definition of Done (DoD)

- [ ] Монорепозиторий структурирован строго по [`docs/TECH.md`](./TECH.md) §3.
- [ ] Конфигурация `deploy/docker-compose.yml` успешно поднимает локальный стек: PostgreSQL 18, Redis 7.2, MinIO (с автоматическим созданием бакета), Mailhog, FastAPI сервис и заглушку воркера.
- [ ] Все сервисы в Docker Compose снабжены проверками работоспособности (`healthcheck`), запуск API ожидает готовности базы данных и кэша.
- [ ] Разработан единый `Makefile` с поддержкой команд `make dev`, `make gate`, `make test`, `make lint`, `make format`, `make typecheck`, `make migrate`, `make down`.
- [ ] Команда `make gate` выполняется локально без ошибок и завершается с кодом возврата `0`.
- [ ] Реализовано асинхронное ядро FastAPI (`backend/app/main.py`) с поддержкой lifespan, CORS, структурированного логирования в формате JSON (`structlog`) и метриками Prometheus.
- [ ] Реализованы служебные эндпоинты: `GET /api/v1/health` (liveness) и `GET /api/v1/ready` (readiness с проверкой PostgreSQL, Redis и S3/MinIO).
- [ ] Настроена конфигурация Alembic в асинхронном режиме (`asyncpg`) и сформирована начальная ревизия `0001_initial_schema.py` для всех базовых таблиц (`users`, `refresh_tokens`, `daily_usage`, `subscriptions`, `b2b_invoices`, `app_tokens`) с partial unique индексами.
- [ ] Реализованы декларативные модели SQLAlchemy 2.0 в `backend/app/models/`.
- [ ] Реализован сервис хранилища `backend/app/services/storage_service.py` для работы с S3/MinIO.
- [ ] Создан скелет клиентского приложения `frontend/` на Next.js 14 (App Router, TypeScript `strict: true`, Tailwind CSS), успешно проходящий шаги `npm run lint`, `npm run typecheck` и `npm run build`.
- [ ] Написаны юнит- и интеграционные тесты бэкенда (`pytest`), покрывающие проверку healthcheck, readiness, подключение к БД и CRUD-операции базовых моделей. Покрытие тестами кода Slice 0 составляет не менее 80%.
- [ ] Создан и актуализирован файл эталонных переменных окружения `.env.example`.

---

## 1. Компоненты и структура файлов (Slice 0)

В рамках Slice 0 создаются следующие директории и файлы:

```text
clean-doc/
  .env.example                  # Эталонный файл переменных окружения
  .gitignore                    # Правила игнорирования Git для всего монорепозитория
  .markdownlint.yml             # Конфигурация линтера Markdown документации
  AGENTS.md                     # Регламент разработки и правила для AI-агентов
  LICENSE                       # Лицензия проекта
  Makefile                      # Главный файл автоматизации команд и CI-гейта
  README.md                     # Описание проекта и инструкция по первому запуску
  backend/
    alembic/
      env.py                    # Асинхронный запуск миграций Alembic
      script.py.mako            # Шаблон создания новых ревизий
      versions/
        0001_initial_schema.py  # Начальная миграция базовых таблиц
    alembic.ini                 # Конфигурация Alembic
    app/
      api/
        v1/
          endpoints/
            health.py           # Эндпоинты /health и /ready
          router.py             # Главный роутер API v1
      core/
        config.py               # Валидация настроек окружения (Pydantic Settings)
        database.py             # Подключение asyncpg и сессии SQLAlchemy 2.0
        redis.py                # Клиент и пул подключений Redis
        security.py             # Утилиты хеширования SHA-256 и токены
      models/
        __init__.py
        base.py                 # Декларативная база и общие миксины
        invoice.py              # Модель b2b_invoices
        subscription.py         # Модель subscriptions
        token.py                # Модели refresh_tokens и app_tokens
        usage.py                # Модель daily_usage
        user.py                 # Модель users
      schemas/
        __init__.py
        health.py               # Pydantic схемы ответов health/ready
      services/
        __init__.py
        storage_service.py      # Асинхронный клиент S3 (Selectel / MinIO)
      workers/
        __init__.py
        worker.py               # Заглушка процесса воркера для проверки compose
      main.py                   # Точка входа FastAPI, lifespan, middleware
    tests/
      conftest.py               # Фикстуры pytest (клиент, тестовая БД, моки)
      test_database.py          # Тестирование моделей и индексов БД
      test_health.py            # Интеграционные тесты /health и /ready
      test_storage.py           # Тестирование S3 хранилища MinIO
    Dockerfile.api              # Dockerfile сервиса FastAPI
    Dockerfile.worker           # Dockerfile фонового воркера
    pyproject.toml              # Зависимости uv, конфигурации ruff, mypy, pytest
  deploy/
    Caddyfile                   # Конфигурация Caddy для локальной и прод среды
    docker-compose.yml          # Стек локальной разработки
    docker-compose.prod.yml     # Продакшн стек для VDS
    monitoring/
      grafana/
        provisioning/
          dashboards/
            dashboards.yml      # Автоматическая загрузка дашбордов Grafana
          datasources/
            prometheus.yml      # Источник данных Prometheus
      prometheus.yml            # Сбор метрик с FastAPI и системных экспортеров
  frontend/
    public/
      favicon.ico
    src/
      app/
        layout.tsx              # Корневой лейаут, подключение шрифтов Inter
        page.tsx                # Базовая страница-заглушка для проверки сборки
      lib/
        api-client.ts           # Базовый HTTP-клиент fetch
      styles/
        globals.css             # Глобальные стили Tailwind CSS
    package.json                # Зависимости и скрипты фронтенда
    postcss.config.js           # Конфигурация PostCSS
    tailwind.config.ts          # Конфигурация Tailwind CSS
    tsconfig.json               # Строгая конфигурация TypeScript (strict: true)
  scripts/
    check_migrations.py         # Проверка статуса миграций перед запуском
    seed_dev_data.py            # Скрипт наполнения dev-базы тестовыми данными
```

---

## 2. Локальная инфраструктура (`deploy/docker-compose.yml`)

Локальное окружение строится на базе Docker Compose и обеспечивает полную автономность без необходимости обращаться к внешним платным сервисам.

### 2.1. Спецификация сервисов

| Сервис | Образ / Сборка | Внутренний порт | Внешний порт | Назначение |
| :--- | :--- | :--- | :--- | :--- |
| `postgres` | `postgres:18-alpine` | 5432 | 5432 | Основная реляционная СУБД проекта |
| `redis` | `redis:7.2-alpine` | 6379 | 6379 | Брокер очередей RQ, кэш и Pub/Sub прогресса |
| `minio` | `minio/minio:RELEASE.2024-01-31T20-20-33Z` | 9000, 9001 | 9000, 9001 | Локальный S3-совместимый эмулятор объектного хранилища |
| `minio-init` | `minio/mc:latest` | — | — | Одноразовый контейнер создания бакета `cleandoc-dev` |
| `mailhog` | `mailhog/mailhog:latest` | 1025, 8025 | 1025, 8025 | Локальный SMTP-сервер и веб-интерфейс проверки писем |
| `api` | `Dockerfile.api` | 8000 | 8000 | Бэкенд API на FastAPI с live-reload |
| `worker` | `Dockerfile.worker` | — | — | Процесс воркера RQ (в Slice 0 в режиме ожидания) |

### 2.2. Полный манифест `deploy/docker-compose.yml`

```yaml
version: "3.8"

services:
  postgres:
    image: postgres:18-alpine
    container_name: cleandoc_postgres
    restart: unless-stopped
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-cleandoc}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-secure_pg_password}
      POSTGRES_DB: ${POSTGRES_DB:-cleandoc_db}
    ports:
      - "5432:5432"
    volumes:
      - pg_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-cleandoc} -d ${POSTGRES_DB:-cleandoc_db}"]
      interval: 5s
      timeout: 5s
      retries: 5
      start_period: 5s

  redis:
    image: redis:7.2-alpine
    container_name: cleandoc_redis
    restart: unless-stopped
    command: ["redis-server", "--appendonly", "yes"]
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5
      start_period: 3s

  minio:
    image: minio/minio:RELEASE.2024-01-31T20-20-33Z
    container_name: cleandoc_minio
    restart: unless-stopped
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: ${S3_ACCESS_KEY_ID:-minioadmin}
      MINIO_ROOT_PASSWORD: ${S3_SECRET_ACCESS_KEY:-minioadmin}
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - minio_data:/data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 5s
      timeout: 3s
      retries: 5
      start_period: 5s

  minio-init:
    image: minio/mc:latest
    container_name: cleandoc_minio_init
    depends_on:
      minio:
        condition: service_healthy
    entrypoint: >
      /bin/sh -c "
      /usr/bin/mc alias set local http://minio:9000 ${S3_ACCESS_KEY_ID:-minioadmin} ${S3_SECRET_ACCESS_KEY:-minioadmin};
      /usr/bin/mc mb --ignore-existing local/${S3_BUCKET_NAME:-cleandoc-dev};
      /usr/bin/mc anonymous set none local/${S3_BUCKET_NAME:-cleandoc-dev};
      exit 0;
      "

  mailhog:
    image: mailhog/mailhog:latest
    container_name: cleandoc_mailhog
    restart: unless-stopped
    ports:
      - "1025:1025"  # SMTP
      - "8025:8025"  # Web UI
    healthcheck:
      test: ["CMD-SHELL", "nc -z localhost 1025 || exit 1"]
      interval: 10s
      timeout: 5s
      retries: 3
      start_period: 5s

  api:
    build:
      context: ../backend
      dockerfile: Dockerfile.api
    container_name: cleandoc_api
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      ENVIRONMENT: dev
      DEBUG: "true"
      POSTGRES_SERVER: postgres
      POSTGRES_PORT: 5432
      POSTGRES_USER: ${POSTGRES_USER:-cleandoc}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-secure_pg_password}
      POSTGRES_DB: ${POSTGRES_DB:-cleandoc_db}
      REDIS_HOST: redis
      REDIS_PORT: 6379
      S3_ENDPOINT_URL: http://minio:9000
      S3_ACCESS_KEY_ID: ${S3_ACCESS_KEY_ID:-minioadmin}
      S3_SECRET_ACCESS_KEY: ${S3_SECRET_ACCESS_KEY:-minioadmin}
      S3_BUCKET_NAME: ${S3_BUCKET_NAME:-cleandoc-dev}
      S3_REGION: ru-1
      SMTP_HOST: mailhog
      SMTP_PORT: 1025
      SMTP_USE_TLS: "false"
    volumes:
      - ../backend/app:/app/app:ro
      - ../backend/alembic:/app/alembic:ro
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      minio:
        condition: service_healthy
      minio-init:
        condition: service_completed_successfully
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 10s

  worker:
    build:
      context: ../backend
      dockerfile: Dockerfile.worker
    container_name: cleandoc_worker
    restart: unless-stopped
    environment:
      ENVIRONMENT: dev
      DEBUG: "true"
      POSTGRES_SERVER: postgres
      POSTGRES_PORT: 5432
      POSTGRES_USER: ${POSTGRES_USER:-cleandoc}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-secure_pg_password}
      POSTGRES_DB: ${POSTGRES_DB:-cleandoc_db}
      REDIS_HOST: redis
      REDIS_PORT: 6379
      S3_ENDPOINT_URL: http://minio:9000
      S3_ACCESS_KEY_ID: ${S3_ACCESS_KEY_ID:-minioadmin}
      S3_SECRET_ACCESS_KEY: ${S3_SECRET_ACCESS_KEY:-minioadmin}
      S3_BUCKET_NAME: ${S3_BUCKET_NAME:-cleandoc-dev}
      S3_REGION: ru-1
    volumes:
      - ../backend/app:/app/app:ro
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      minio:
        condition: service_healthy

volumes:
  pg_data:
    name: cleandoc_pg_data
  redis_data:
    name: cleandoc_redis_data
  minio_data:
    name: cleandoc_minio_data
```

---

## 3. Makefile и регламент качества (`make gate`)

Файл `Makefile` в корне проекта служит единой точкой входа для разработчиков и скриптов CI.

```makefile
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
```

---

## 4. Конфигурация бэкенда (`backend/pyproject.toml`)

Управление зависимостями бэкенда выполняется пакетным менеджером `uv`.

```toml
[project]
name = "clean-doc-backend"
version = "0.1.0"
description = "Бэкенд B2B микро-SaaS онлайн-конвертера PDF в Word и Excel"
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.30.0",
    "pydantic>=2.8.0",
    "pydantic-settings>=2.4.0",
    "sqlalchemy[asyncio]>=2.0.34",
    "asyncpg>=0.29.0",
    "alembic>=1.13.2",
    "redis>=5.0.8",
    "rq>=2.0.0",
    "aioboto3>=13.1.0",
    "boto3>=1.35.0",
    "structlog>=24.4.0",
    "prometheus-fastapi-instrumentator>=7.0.0",
    "slowapi>=0.1.9",
    "python-multipart>=0.0.9",
    "httpx>=0.27.0",
    "cryptography>=43.0.0",
]

[dependency-groups]
dev = [
    "pytest>=8.3.0",
    "pytest-asyncio>=0.24.0",
    "pytest-cov>=5.0.0",
    "pytest-mock>=3.14.0",
    "respx>=0.21.1",
    "ruff>=0.6.4",
    "mypy>=1.11.2",
    "types-redis>=4.6.0",
    "types-boto3>=1.35.0",
]

[tool.ruff]
line-length = 100
target-version = "py312"
exclude = [
    ".git",
    "alembic/versions",
    "__pycache__",
]

[tool.ruff.lint]
select = [
    "E",   # pycodestyle errors
    "W",   # pycodestyle warnings
    "F",   # pyflakes
    "I",   # isort
    "B",   # flake8-bugbear
    "C4",  # flake8-comprehensions
    "UP",  # pyupgrade
    "ARG", # flake8-unused-arguments
]
ignore = [
    "E501", # Длина строки контролируется форматтером
]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"

[tool.mypy]
python_version = "3.12"
strict = true
ignore_missing_imports = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
disallow_untyped_decorators = false
warn_redundant_casts = true
warn_unused_ignores = true
warn_return_any = true
no_implicit_optional = true

[[tool.mypy.overrides]]
module = "alembic.*"
ignore_errors = true

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
python_files = ["test_*.py"]
filterwarnings = [
    "ignore::DeprecationWarning",
]
```

---

## 5. Архитектурное ядро бэкенда (`core/`)

### 5.1. `backend/app/core/config.py`

Конфигурационный модуль считывает переменные окружения и осуществляет валидацию типов через Pydantic v2 Settings.

```python
from functools import lru_cache
from typing import Literal
from pydantic import Field, PostgresDsn, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Системные параметры
    ENVIRONMENT: Literal["dev", "test", "prod"] = "dev"
    DEBUG: bool = False
    PROJECT_NAME: str = "Чистый документ"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = Field(default="dev_secret_key_insecure_replace_in_prod_64_characters_min_len")
    ALLOWED_HOSTS: list[str] = ["*"]

    # PostgreSQL 18
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "cleandoc"
    POSTGRES_PASSWORD: str = "secure_pg_password"
    POSTGRES_DB: str = "cleandoc_db"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def async_database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def sync_database_url(self) -> str:
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # Redis 7.2
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    @computed_field  # type: ignore[prop-decorator]
    @property
    def redis_url(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # S3 Хранилище (MinIO dev / Selectel prod)
    S3_ENDPOINT_URL: str = "http://localhost:9000"
    S3_REGION: str = "ru-1"
    S3_BUCKET_NAME: str = "cleandoc-dev"
    S3_ACCESS_KEY_ID: str = "minioadmin"
    S3_SECRET_ACCESS_KEY: str = "minioadmin"

    # SMTP для Magic Link
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 1025
    SMTP_USE_TLS: bool = False
    SMTP_USER: str = "no-reply@clean-doc.ru"
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "no-reply@clean-doc.ru"

    # Мониторинг
    PROMETHEUS_ENABLED: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

### 5.2. `backend/app/core/database.py`

Пул соединений к PostgreSQL 18 строится на базе драйвера `asyncpg` и асинхронного движка SQLAlchemy 2.0.

```python
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from app.core.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.async_database_url,
    echo=settings.DEBUG,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
```

### 5.3. `backend/app/core/redis.py`

Подключение к Redis для очередей RQ и Pub/Sub прогресса задач.

```python
from redis.asyncio import ConnectionPool, Redis
from app.core.config import get_settings

settings = get_settings()

redis_pool = ConnectionPool.from_url(
    settings.redis_url,
    max_connections=20,
    decode_responses=True,
)


def get_redis_client() -> Redis:
    return Redis(connection_pool=redis_pool)
```

### 5.4. `backend/app/core/security.py`

Вспомогательные криптографические функции: вычисление SHA-256 хешей для токенов беспарольного входа и генерация криптографически стойких случайных строк.

```python
import hashlib
import secrets


def hash_token(raw_token: str) -> str:
    """Вычисляет SHA-256 хеш строки для безопасного хранения в БД."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def generate_secure_token(length_bytes: int = 32) -> str:
    """Генерирует криптографически стойкий URL-safe токен."""
    return secrets.token_urlsafe(length_bytes)
```

---

## 6. Базовые модели SQLAlchemy (`models/`) и Alembic

### 6.1. Декларативная база: `backend/app/models/base.py`

```python
from datetime import datetime
from uuid import UUID
from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class UUIDPrimaryKeyMixin:
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
```

### 6.2. Модели пользователей и токенов: `backend/app/models/user.py` и `token.py`

```python
# backend/app/models/__init__.py
from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.invoice import B2BInvoice
from app.models.subscription import Subscription
from app.models.token import AppToken, RefreshToken
from app.models.usage import DailyUsage
from app.models.user import User

__all__ = [
    "Base",
    "TimestampMixin",
    "UUIDPrimaryKeyMixin",
    "User",
    "RefreshToken",
    "AppToken",
    "DailyUsage",
    "Subscription",
    "B2BInvoice",
]
```

```python
# backend/app/models/user.py
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import BigInteger, Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.token import AppToken, RefreshToken
    from app.models.usage import DailyUsage


class User(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "users"

    email: Mapped[str | None] = mapped_column(String, unique=True, index=True, nullable=True)
    telegram_id: Mapped[int | None] = mapped_column(BigInteger, unique=True, index=True, nullable=True)
    telegram_username: Mapped[str | None] = mapped_column(String, nullable=True)
    plan: Mapped[str] = mapped_column(String, default="free", nullable=False)
    
    # Magic Link / Email OTP (хеш SHA-256 кода, TTL 15 минут)
    magic_code_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    magic_code_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Защита от брутфорса и административная блокировка
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    magic_code_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        "RefreshToken", back_populates="user", cascade="all, delete-orphan"
    )
    app_tokens: Mapped[list["AppToken"]] = relationship(
        "AppToken", back_populates="user", cascade="all, delete-orphan"
    )
    daily_usages: Mapped[list["DailyUsage"]] = relationship(
        "DailyUsage", back_populates="user", cascade="all, delete-orphan"
    )
```

```python
# backend/app/models/token.py
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class RefreshToken(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "refresh_tokens"

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="refresh_tokens")

    __table_args__ = (
        Index("idx_refresh_tokens_hash", "token_hash", postgresql_where=(revoked.is_(False))),
    )


class AppToken(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "app_tokens"

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    token_hash: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    scopes: Mapped[list[str]] = mapped_column(ARRAY(String), default=["convert"], nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="app_tokens")

    __table_args__ = (
        Index("idx_app_tokens_hash", "token_hash", postgresql_where=(revoked.is_(False))),
    )
```

### 6.3. Модели учета лимитов, подписок и счетов

```python
# backend/app/models/usage.py
from datetime import date
from typing import TYPE_CHECKING
from uuid import UUID
from sqlalchemy import Date, ForeignKey, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class DailyUsage(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "daily_usage"

    user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
    )
    fingerprint: Mapped[str | None] = mapped_column(String, nullable=True)
    ip_subnet: Mapped[str] = mapped_column(String, nullable=False)
    usage_date: Mapped[date] = mapped_column(Date, server_default=func.current_date(), nullable=False)
    conversion_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    user: Mapped["User | None"] = relationship("User", back_populates="daily_usages")

    __table_args__ = (
        UniqueConstraint("user_id", "usage_date", name="uq_daily_user"),
        Index("idx_daily_usage_date", "usage_date"),
        Index(
            "uq_daily_guest_fp",
            "fingerprint",
            "ip_subnet",
            "usage_date",
            unique=True,
            postgresql_where=(fingerprint.isnot(None)),
        ),
        Index(
            "uq_daily_guest_ip",
            "ip_subnet",
            "usage_date",
            unique=True,
            postgresql_where=(fingerprint.is_(None)),
        ),
    )
```

```python
# backend/app/models/subscription.py
from datetime import datetime
from uuid import UUID
from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Subscription(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "subscriptions"

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    plan: Mapped[str] = mapped_column(String, nullable=False)
    billing_period: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, default="active", nullable=False)
    yukassa_payment_id: Mapped[str | None] = mapped_column(String, unique=True, nullable=True)
    yukassa_payment_method_id: Mapped[str | None] = mapped_column(String, nullable=True)
    amount_rub: Mapped[int] = mapped_column(Integer, nullable=False)
    current_period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    current_period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    next_billing_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    __table_args__ = (
        Index("idx_subscriptions_user", "user_id", "status"),
        Index(
            "idx_subscriptions_billing",
            "next_billing_at",
            postgresql_where=(status.in_(["active", "past_due"])),
        ),
    )
```

```python
# backend/app/models/invoice.py
from datetime import datetime
from uuid import UUID
from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class B2BInvoice(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "b2b_invoices"

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    invoice_number: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    inn: Mapped[str] = mapped_column(String, nullable=False)
    kpp: Mapped[str | None] = mapped_column(String, nullable=True)
    company_name: Mapped[str] = mapped_column(String, nullable=False)
    company_address: Mapped[str] = mapped_column(String, nullable=False)
    amount_rub: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String, default="pending", nullable=False)
    pdf_s3_key: Mapped[str] = mapped_column(String, nullable=False)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_invoices_user", "user_id", "status"),
    )
```

### 6.4. Начальная миграция Alembic: `backend/alembic/versions/0001_initial_schema.py`

Миграция создает таблицы и частичные уникальные индексы в строгом соответствии с PostgreSQL 18.

```python
"""initial_schema

Revision ID: 0001
Revises: 
Create Date: 2026-10-15 00:00:00.000000

"""
from collections.abc import Sequence
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')

    # 1. users
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("email", sa.Text(), nullable=True),
        sa.Column("telegram_id", sa.BigInteger(), nullable=True),
        sa.Column("telegram_username", sa.Text(), nullable=True),
        sa.Column("plan", sa.Text(), server_default="free", nullable=False),
        sa.Column("magic_code_hash", sa.Text(), nullable=True),
        sa.Column("magic_code_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_blocked", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("magic_code_attempts", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("plan IN ('free', 'pro')", name="check_users_plan"),
        sa.UniqueConstraint("email", name="uq_users_email"),
        sa.UniqueConstraint("telegram_id", name="uq_users_telegram_id"),
    )
    op.create_index("idx_users_email", "users", ["email"])
    op.create_index("idx_users_telegram", "users", ["telegram_id"])

    # 2. refresh_tokens
    op.create_table(
        "refresh_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("token_hash", name="uq_refresh_tokens_hash"),
    )
    op.create_index(
        "idx_refresh_tokens_hash",
        "refresh_tokens",
        ["token_hash"],
        postgresql_where=sa.text("revoked = FALSE"),
    )

    # 3. daily_usage
    op.create_table(
        "daily_usage",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
        sa.Column("fingerprint", sa.Text(), nullable=True),
        sa.Column("ip_subnet", sa.Text(), nullable=False),
        sa.Column("usage_date", sa.Date(), server_default=sa.text("CURRENT_DATE"), nullable=False),
        sa.Column("conversion_count", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("user_id", "usage_date", name="uq_daily_user"),
    )
    op.create_index("idx_daily_usage_date", "daily_usage", ["usage_date"])
    op.create_index(
        "uq_daily_guest_fp",
        "daily_usage",
        ["fingerprint", "ip_subnet", "usage_date"],
        unique=True,
        postgresql_where=sa.text("fingerprint IS NOT NULL"),
    )
    op.create_index(
        "uq_daily_guest_ip",
        "daily_usage",
        ["ip_subnet", "usage_date"],
        unique=True,
        postgresql_where=sa.text("fingerprint IS NULL"),
    )

    # 4. subscriptions
    op.create_table(
        "subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("plan", sa.Text(), nullable=False),
        sa.Column("billing_period", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), server_default="active", nullable=False),
        sa.Column("yukassa_payment_id", sa.Text(), nullable=True),
        sa.Column("yukassa_payment_method_id", sa.Text(), nullable=True),
        sa.Column("amount_rub", sa.Integer(), nullable=False),
        sa.Column("current_period_start", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("next_billing_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retry_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("plan IN ('pro')", name="check_subscriptions_plan"),
        sa.CheckConstraint("billing_period IN ('month', 'year')", name="check_subscriptions_period"),
        sa.CheckConstraint("status IN ('active', 'past_due', 'cancelled')", name="check_subscriptions_status"),
        sa.UniqueConstraint("yukassa_payment_id", name="uq_subscriptions_payment_id"),
    )
    op.create_index("idx_subscriptions_user", "subscriptions", ["user_id", "status"])
    op.create_index(
        "idx_subscriptions_billing",
        "subscriptions",
        ["next_billing_at"],
        postgresql_where=sa.text("status IN ('active', 'past_due')"),
    )

    # 5. b2b_invoices
    op.create_table(
        "b2b_invoices",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("invoice_number", sa.Text(), nullable=False),
        sa.Column("inn", sa.Text(), nullable=False),
        sa.Column("kpp", sa.Text(), nullable=True),
        sa.Column("company_name", sa.Text(), nullable=False),
        sa.Column("company_address", sa.Text(), nullable=False),
        sa.Column("amount_rub", sa.Integer(), nullable=False),
        sa.Column("status", sa.Text(), server_default="pending", nullable=False),
        sa.Column("pdf_s3_key", sa.Text(), nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("status IN ('pending', 'paid', 'cancelled')", name="check_invoices_status"),
        sa.UniqueConstraint("invoice_number", name="uq_invoices_number"),
    )
    op.create_index("idx_invoices_user", "b2b_invoices", ["user_id", "status"])

    # 6. app_tokens
    op.create_table(
        "app_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("token_hash", sa.Text(), nullable=False),
        sa.Column("scopes", postgresql.ARRAY(sa.Text()), server_default=sa.text("'{convert}'"), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("token_hash", name="uq_app_tokens_hash"),
    )
    op.create_index(
        "idx_app_tokens_hash",
        "app_tokens",
        ["token_hash"],
        postgresql_where=sa.text("revoked = FALSE"),
    )


def downgrade() -> None:
    op.drop_table("app_tokens")
    op.drop_table("b2b_invoices")
    op.drop_table("subscriptions")
    op.drop_table("daily_usage")
    op.drop_table("refresh_tokens")
    op.drop_table("users")
```

### 6.5. Конфигурация Alembic (`backend/alembic.ini`)

```ini
[alembic]
script_location = alembic
prepend_sys_path = .
version_path_separator = os

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

### 6.6. Асинхронный запуск миграций (`backend/alembic/env.py`)

Модуль обеспечивает бесшовную интеграцию с `asyncpg` и автоматическое обнаружение всех моделей SQLAlchemy 2.0:

```python
import asyncio
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context

from app.core.config import get_settings
from app.models.base import Base
import app.models  # noqa: F401 - регистрирует все модели для autogenerate

config = context.config
settings = get_settings()

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata
config.set_main_option("sqlalchemy.url", settings.async_database_url)


def run_migrations_offline() -> None:
    """Запуск миграций в offline-режиме (генерация SQL-скрипта)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Асинхронный коннектор для asyncpg."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    """Запуск миграций в online-режиме."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

### 6.7. Шаблон ревизий (`backend/alembic/script.py.mako`)

```mako
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from collections.abc import Sequence
import sqlalchemy as sa
from alembic import op
${imports if imports else ""}

revision: str = ${repr(up_revision)}
down_revision: str | None = ${repr(down_revision)}
branch_labels: str | Sequence[str] | None = ${repr(branch_labels)}
depends_on: str | Sequence[str] | None = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
```

---

## 7. Сервисный слой хранилища S3 (`storage_service.py`)

Сервис обеспечивает единый фасад взаимодействия с S3-хранилищем (Selectel S3 в продакшне и MinIO локально). Согласно проектному регламенту, в веб-сервисе используется асинхронный клиент `aioboto3` (либо `boto3` с выполнением в пуле потоков через `asyncio.to_thread`):

```python
import asyncio
from botocore.client import Config
import boto3
from app.core.config import get_settings

settings = get_settings()


class StorageService:
    def __init__(self) -> None:
        self.bucket = settings.S3_BUCKET_NAME
        self.endpoint_url = settings.S3_ENDPOINT_URL
        self._s3_client = boto3.client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=settings.S3_ACCESS_KEY_ID,
            aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
            region_name=settings.S3_REGION,
            config=Config(signature_version="s3v4"),
        )

    async def ensure_bucket_exists(self) -> None:
        """Проверяет существование бакета и создает его при отсутствии (для dev окружения)."""
        def _check() -> None:
            try:
                self._s3_client.head_bucket(Bucket=self.bucket)
            except Exception:
                self._s3_client.create_bucket(Bucket=self.bucket)

        await asyncio.to_thread(_check)

    async def check_health(self) -> bool:
        """Проверяет доступность S3 сервиса."""
        def _ping() -> bool:
            try:
                self._s3_client.head_bucket(Bucket=self.bucket)
                return True
            except Exception:
                return False

        return await asyncio.to_thread(_ping)

    async def upload_bytes(self, data: bytes, s3_key: str, content_type: str = "application/octet-stream") -> None:
        def _upload() -> None:
            self._s3_client.put_object(
                Bucket=self.bucket,
                Key=s3_key,
                Body=data,
                ContentType=content_type,
            )

        await asyncio.to_thread(_upload)

    async def download_bytes(self, s3_key: str) -> bytes:
        def _download() -> bytes:
            response = self._s3_client.get_object(Bucket=self.bucket, Key=s3_key)
            return response["Body"].read()  # type: ignore[no-any-return]

        return await asyncio.to_thread(_download)

    async def generate_presigned_url(self, s3_key: str, expires_in_seconds: int = 900) -> str:
        def _presign() -> str:
            return self._s3_client.generate_presigned_url(  # type: ignore[no-any-return]
                "get_object",
                Params={"Bucket": self.bucket, "Key": s3_key},
                ExpiresIn=expires_in_seconds,
            )

        return await asyncio.to_thread(_presign)


storage_service = StorageService()
```

---

## 8. Приложение FastAPI (`main.py`) и служебные эндпоинты

### 8.1. `backend/app/schemas/health.py`

```python
from typing import Literal
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"


class ReadinessChecks(BaseModel):
    database: bool
    redis: bool
    storage: bool


class ReadinessResponse(BaseModel):
    status: Literal["ok", "unhealthy"]
    checks: ReadinessChecks
```

### 8.2. `backend/app/api/v1/endpoints/health.py`

Эндпоинты проверки жизнеспособности для мониторинга, Docker healthcheck и балансировщика Caddy:

```python
from fastapi import APIRouter, Response, status
from redis.asyncio import Redis
from sqlalchemy import text
from app.core.database import AsyncSessionLocal
from app.core.redis import get_redis_client
from app.schemas.health import HealthResponse, ReadinessChecks, ReadinessResponse
from app.services.storage_service import storage_service

router = APIRouter()


@router.get("/health", response_model=HealthResponse, summary="Liveness probe")
async def health_check() -> HealthResponse:
    """Liveness probe: возвращает 200 OK, пока сервис запущен."""
    return HealthResponse(status="ok")


@router.get("/ready", response_model=ReadinessResponse, summary="Readiness probe")
async def readiness_check(response: Response) -> ReadinessResponse:
    """Readiness probe: проверяет доступность PostgreSQL, Redis и S3."""
    db_ok = False
    redis_ok = False
    storage_ok = False

    # 1. Проверка PostgreSQL
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
            db_ok = True
    except Exception:
        db_ok = False

    # 2. Проверка Redis
    try:
        redis_client: Redis = get_redis_client()
        await redis_client.ping()
        redis_ok = True
    except Exception:
        redis_ok = False

    # 3. Проверка S3 хранилища
    storage_ok = await storage_service.check_health()

    all_ready = db_ok and redis_ok and storage_ok
    if not all_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return ReadinessResponse(
        status="ok" if all_ready else "unhealthy",
        checks=ReadinessChecks(
            database=db_ok,
            redis=redis_ok,
            storage=storage_ok,
        ),
    )
```

### 8.3. `backend/app/main.py`

```python
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
import structlog
from app.api.v1.router import api_v1_router
from app.core.config import get_settings
from app.services.storage_service import storage_service

settings = get_settings()
logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Инициализация при старте
    logger.info("startup", project=settings.PROJECT_NAME, env=settings.ENVIRONMENT)
    try:
        await storage_service.ensure_bucket_exists()
    except Exception as exc:
        logger.warning("s3_init_warning", error=str(exc))
    yield
    # Очистка при завершении
    logger.info("shutdown", project=settings.PROJECT_NAME)


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="0.1.0",
    docs_url=f"{settings.API_V1_STR}/docs" if settings.DEBUG else None,
    redoc_url=f"{settings.API_V1_STR}/redoc" if settings.DEBUG else None,
    openapi_url=f"{settings.API_V1_STR}/openapi.json" if settings.DEBUG else None,
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_HOSTS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus метрики
if settings.PROMETHEUS_ENABLED:
    Instrumentator().instrument(app).expose(app, endpoint="/metrics")

# Подключение маршрутов API v1
app.include_router(api_v1_router, prefix=settings.API_V1_STR)


# Централизованная обработка непредвиденных ошибок
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("unhandled_server_error", path=request.url.path, error=str(exc))
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Внутренняя ошибка сервера. Пожалуйста, повторите попытку позже.",
            "code": "INTERNAL_SERVER_ERROR",
        },
    )
```

### 8.4. Главный роутер API v1 (`backend/app/api/v1/router.py`)

Модуль агрегирует контроллеры API v1 и содержит точку подключения для маршрутов конвертации Slice 1:

```python
from fastapi import APIRouter
from app.api.v1.endpoints import health

api_v1_router = APIRouter()

# Служебные маршруты Slice 0
api_v1_router.include_router(health.router, tags=["health"])

# Точка расширения Slice 1:
# from app.api.v1.endpoints import convert
# api_v1_router.include_router(convert.router, prefix="/convert", tags=["convert"])
```

### 8.5. Процесс воркера (`backend/app/workers/worker.py`)

Для Slice 0 воркер исполняет роль легковесной заглушки (daemon), проверяющей доступность Redis и переходящей в спящий режим. Это предотвращает падение контейнера `cleandoc_worker` и подготавливает его к запуску `rq worker` в Slice 1:

```python
# backend/app/workers/__init__.py
# Пакет фоновых задач и воркеров RQ

# backend/app/workers/worker.py
import asyncio
import signal
import sys
import structlog
from app.core.config import get_settings
from app.core.redis import get_redis_client

logger = structlog.get_logger()
settings = get_settings()


async def run_worker_stub() -> None:
    """Заглушка воркера для Slice 0.
    
    В Slice 0 проверяет связь с Redis и находится в цикле ожидания,
    обеспечивая стабильную работу контейнера cleandoc_worker.
    В Slice 1 этот модуль замещается точкой входа rq worker с Docling warmup.
    """
    logger.info("worker_stub_starting", environment=settings.ENVIRONMENT)
    try:
        redis_client = get_redis_client()
        await redis_client.ping()
        logger.info("worker_redis_connected", host=settings.REDIS_HOST)
    except Exception as exc:
        logger.error("worker_redis_connection_failed", error=str(exc))

    stop_event = asyncio.Event()

    def _signal_handler() -> None:
        logger.info("worker_stub_stopping")
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _signal_handler)
        except NotImplementedError:
            pass

    logger.info("worker_stub_ready_idle")
    while not stop_event.is_set():
        await asyncio.sleep(1)


if __name__ == "__main__":
    try:
        asyncio.run(run_worker_stub())
    except (KeyboardInterrupt, SystemExit):
        sys.exit(0)
```

### 8.6. Докерфайлы бэкенда (`backend/Dockerfile.api`, `backend/Dockerfile.worker`)

```dockerfile
# backend/Dockerfile.api
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_SYSTEM_PYTHON=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.4.18 /uv /uvx /bin/

COPY pyproject.toml ./
RUN uv pip install --no-cache -r pyproject.toml

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

```dockerfile
# backend/Dockerfile.worker
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_SYSTEM_PYTHON=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    qpdf \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.4.18 /uv /uvx /bin/

COPY pyproject.toml ./
RUN uv pip install --no-cache -r pyproject.toml

COPY . .

CMD ["python", "-m", "app.workers.worker"]
```

### 8.7. Скрипты инициализации и проверки (`scripts/`)

```python
#!/usr/bin/env python3
# scripts/check_migrations.py
"""Скрипт проверки применения всех миграций Alembic перед стартом."""
import asyncio
import sys
from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic.runtime.migration import MigrationContext
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import get_settings


async def check_db_migrations() -> None:
    settings = get_settings()
    engine = create_async_engine(settings.async_database_url)

    alembic_cfg = Config("alembic.ini")
    script = ScriptDirectory.from_config(alembic_cfg)
    head_revision = script.get_current_head()

    async with engine.connect() as conn:
        def _get_rev(sync_conn):
            context = MigrationContext.configure(sync_conn)
            return context.get_current_revision()

        current_rev = await conn.run_sync(_get_rev)

    await engine.dispose()

    if current_rev != head_revision:
        print(f"ERROR: DB revision ({current_rev}) does not match Alembic head ({head_revision})")
        sys.exit(1)
    print(f"OK: DB revision is up to date ({current_rev})")


if __name__ == "__main__":
    asyncio.run(check_db_migrations())
```

```python
#!/usr/bin/env python3
# scripts/seed_dev_data.py
"""Скрипт наполнения dev-базы тестовыми пользователями и данными."""
import asyncio
from datetime import date, datetime, timezone
import structlog
from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.models.subscription import Subscription
from app.models.usage import DailyUsage

logger = structlog.get_logger()


async def seed() -> None:
    async with AsyncSessionLocal() as session:
        user_free = User(
            email="free@clean-doc.local",
            telegram_username="test_free_user",
            plan="free",
        )
        user_pro = User(
            email="pro@clean-doc.local",
            telegram_username="test_pro_user",
            plan="pro",
        )
        session.add_all([user_free, user_pro])
        await session.flush()

        subscription = Subscription(
            user_id=user_pro.id,
            plan="pro",
            billing_period="month",
            status="active",
            amount_rub=1490,
            current_period_start=datetime.now(timezone.utc),
            current_period_end=datetime.now(timezone.utc),
        )
        usage = DailyUsage(
            user_id=user_free.id,
            ip_subnet="127.0.0.0/24",
            usage_date=date.today(),
            conversion_count=1,
        )
        session.add_all([subscription, usage])
        await session.commit()
        logger.info("seed_completed", free_user_id=str(user_free.id), pro_user_id=str(user_pro.id))


if __name__ == "__main__":
    asyncio.run(seed())
```

---

## 9. Скелет фронтенда (`frontend/`)

Для обеспечения сквозного прохождения пайплайна `make gate` на этапе Foundation создается минимальный скелет приложения Next.js 14.

### 9.1. `frontend/package.json`

```json
{
  "name": "clean-doc-frontend",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint",
    "typecheck": "tsc --noEmit",
    "test": "vitest run"
  },
  "dependencies": {
    "@tanstack/react-query": "^5.56.2",
    "clsx": "^2.1.1",
    "lucide-react": "^0.441.0",
    "next": "14.2.10",
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "tailwind-merge": "^2.5.2",
    "zustand": "^4.5.5"
  },
  "devDependencies": {
    "@types/node": "^20.16.5",
    "@types/react": "^18.3.5",
    "@types/react-dom": "^18.3.0",
    "eslint": "^8.57.0",
    "eslint-config-next": "14.2.10",
    "postcss": "^8.4.45",
    "tailwindcss": "^3.4.11",
    "typescript": "^5.5.4",
    "vitest": "^2.0.5"
  }
}
```

### 9.2. `frontend/tsconfig.json`

Строгий режим компиляции TypeScript, исключающий использование типа `any`:

```json
{
  "compilerOptions": {
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [
      {
        "name": "next"
      }
    ],
    "paths": {
      "@/*": ["./src/*"]
    }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
```

### 9.3. Конфигурация стилей (`postcss.config.js`, `tailwind.config.ts`, `globals.css`)

```js
// frontend/postcss.config.js
module.exports = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};
```

```ts
// frontend/tailwind.config.ts
import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: "#2563EB",
      },
      borderRadius: {
        xl: "0.75rem",
      },
    },
  },
  plugins: [],
};
export default config;
```

```css
/* frontend/src/styles/globals.css */
@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  --foreground-rgb: 15, 23, 42;
  --background-start-rgb: 255, 255, 255;
  --background-end-rgb: 248, 250, 252;
}

body {
  color: rgb(var(--foreground-rgb));
  background: linear-gradient(
      to bottom,
      transparent,
      rgb(var(--background-end-rgb))
    )
    rgb(var(--background-start-rgb));
}
```

### 9.4. Базовые страницы (`src/app/layout.tsx`, `src/app/page.tsx`)

```tsx
// frontend/src/app/layout.tsx
import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "@/styles/globals.css";

const inter = Inter({ subsets: ["latin", "cyrillic"] });

export const metadata: Metadata = {
  title: "Чистый документ — онлайн-конвертер PDF в Word и Excel",
  description: "Конвертация PDF документов с сохранением верстки и соответствием 152-ФЗ",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ru">
      <body className={inter.className}>{children}</body>
    </html>
  );
}
```

```tsx
// frontend/src/app/page.tsx
export default function HomePage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-8 bg-slate-50 text-slate-900">
      <div className="max-w-xl w-full text-center space-y-4">
        <h1 className="text-3xl font-bold tracking-tight text-slate-900 sm:text-4xl">
          Чистый документ
        </h1>
        <p className="text-base text-slate-600">
          B2B микро-SaaS онлайн-конвертер PDF в Word и Excel с сохранением верстки и соответствием 152-ФЗ.
        </p>
        <div className="inline-flex items-center rounded-full border border-blue-200 bg-blue-50 px-3 py-1 text-sm font-medium text-blue-700">
          Срез 0: Foundation готов к интеграции
        </div>
      </div>
    </main>
  );
}
```

### 9.5. Базовый API-клиент (`frontend/src/lib/api-client.ts`)

```ts
// frontend/src/lib/api-client.ts
export interface ApiErrorResponse {
  error: string;
  code: string;
  upgrade_url?: string;
}

export class ApiClientError extends Error {
  code: string;
  status: number;
  upgradeUrl?: string;

  constructor(status: number, message: string, code: string, upgradeUrl?: string) {
    super(message);
    this.name = "ApiClientError";
    this.status = status;
    this.code = code;
    this.upgradeUrl = upgradeUrl;
  }
}

export async function apiClient<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const url = `${baseUrl}${endpoint}`;

  const defaultHeaders: HeadersInit = {
    "Content-Type": "application/json",
  };

  const response = await fetch(url, {
    ...options,
    headers: {
      ...defaultHeaders,
      ...options.headers,
    },
  });

  if (!response.ok) {
    let errorData: ApiErrorResponse;
    try {
      errorData = await response.json();
    } catch {
      errorData = {
        error: "Неизвестная ошибка сервера",
        code: "UNKNOWN_ERROR",
      };
    }
    throw new ApiClientError(
      response.status,
      errorData.error || "Ошибка запроса",
      errorData.code || "REQUEST_FAILED",
      errorData.upgrade_url
    );
  }

  return response.json() as Promise<T>;
}
```

### 9.6. Конфигурация тестов Vitest (`vitest.config.ts`, `src/app/page.test.tsx`)

Обеспечивает успешное выполнение шага `npm run test` в пайплайне `make gate`:

```ts
// frontend/vitest.config.ts
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
});
```

```tsx
// frontend/src/app/page.test.tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import HomePage from "./page";

describe("HomePage", () => {
  it("renders main heading correctly", () => {
    render(<HomePage />);
    expect(screen.getByRole("heading", { level: 1 })).toBeDefined();
    expect(screen.getByText("Чистый документ")).toBeDefined();
  });
});
```

---

## 10. Эталонный файл окружения (`.env.example`)

```bash
# Системные настройки
ENVIRONMENT=dev
DEBUG=true
PROJECT_NAME="Чистый документ"
API_V1_STR="/api/v1"
SECRET_KEY=dev_insecure_random_secret_key_minimum_length_of_64_characters_for_hash
ALLOWED_HOSTS=["*"]

# PostgreSQL 18
POSTGRES_SERVER=localhost
POSTGRES_PORT=5432
POSTGRES_USER=cleandoc
POSTGRES_PASSWORD=secure_pg_password
POSTGRES_DB=cleandoc_db

# Redis 7.2
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Хранилище S3 (MinIO для локальной разработки)
S3_ENDPOINT_URL=http://localhost:9000
S3_REGION=ru-1
S3_BUCKET_NAME=cleandoc-dev
S3_ACCESS_KEY_ID=minioadmin
S3_SECRET_ACCESS_KEY=minioadmin

# ЮKassa (заполняется в Slice 3)
YUKASSA_SHOP_ID=test_shop_id
YUKASSA_SECRET_KEY=test_secret_key
YUKASSA_RETURN_URL=http://localhost:3000/dashboard

# DaData API (заполняется в Slice 3)
DADATA_API_KEY=test_dadata_key

# Telegram Bot (заполняется в Slice 2)
TELEGRAM_BOT_TOKEN=test_telegram_token
TELEGRAM_BOT_USERNAME=CleanDocDevBot
TELEGRAM_ADMIN_CHAT_ID=0

# Email (Mailhog для локальной разработки)
SMTP_HOST=localhost
SMTP_PORT=1025
SMTP_USE_TLS=false
SMTP_USER=no-reply@clean-doc.ru
SMTP_PASSWORD=
SMTP_FROM_EMAIL=no-reply@clean-doc.ru

# Prometheus
PROMETHEUS_ENABLED=true

# Docling / HuggingFace офлайн параметры
HF_HUB_OFFLINE=1
TRANSFORMERS_OFFLINE=1
HUGGINGFACE_HUB_VERBOSITY=error
```

---

## 11. Требования к тестированию (Slice 0)

В Slice 0 покрываются юнит- и интеграционными тестами базовые компоненты системы.

### 11.1. Тестовые сценарии

1. **`test_health.py`**:
   - `GET /api/v1/health` возвращает статус `200 OK` и тело `{"status": "ok"}`.
   - `GET /api/v1/ready` при работающих сервисах возвращает `200 OK` со всеми флагами `true`.
   - `GET /api/v1/ready` при сбое БД или Redis возвращает `503 Service Unavailable` с корректной детализацией по компонентам.
2. **`test_database.py`**:
   - Успешное создание записи `User` с дефолтным тарифом `free` и автогенерацией `UUIDv4`.
   - Проверка каскадного удаления связанных `RefreshToken` и `AppToken` при удалении `User`.
   - Проверка ограничения уникальности `daily_usage`:
     - Разрешена одна запись в сутки для зарегистрированного `user_id`.
     - Частичный индекс `uq_daily_guest_fp`: запрещены дубликаты `(fingerprint, ip_subnet, usage_date)` при наличии отпечатка.
     - Частичный индекс `uq_daily_guest_ip`: запрещены дубликаты `(ip_subnet, usage_date)` при пустом отпечатке.
3. **`test_storage.py`**:
   - Проверка генерации корректного pre-signed URL.
   - Загрузка байт в бакет MinIO и последующее скачивание с проверкой контрольной суммы.

### 11.2. Тестовый харнес (`backend/tests/conftest.py`)

Харнес предоставляет изолированное окружение для тестирования: мокирование внешних вызовов (S3, Redis) в соответствии с правилом 7.2 [`AGENTS.md`](../AGENTS.md), транзакционный откат сессий БД и конфигурирование тестового HTTP-клиента.

```python
# backend/tests/conftest.py
import asyncio
from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import get_settings
from app.core.database import get_db
from app.main import app
from app.models.base import Base

settings = get_settings()

# Тестовый асинхронный движок БД
test_engine = create_async_engine(
    settings.async_database_url,
    poolclass=NullPool,
    echo=False,
)

TestingSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


@pytest.fixture(scope="session")
def event_loop() -> Any:
    """Создает единый event loop для тестовой сессии."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
async def prepare_test_db() -> AsyncGenerator[None, None]:
    """Создает схему БД перед прогоном тестов и удаляет после."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Предоставляет изолированную сессию БД с автоматическим откатом транзакции."""
    async with TestingSessionLocal() as session:
        await session.begin()
        try:
            yield session
        finally:
            await session.rollback()
            await session.close()


@pytest.fixture
def mock_redis() -> MagicMock:
    """Мок клиента Redis для изоляции юнит-тестов."""
    client = MagicMock()
    client.ping = AsyncMock(return_value=True)
    client.get = AsyncMock(return_value=None)
    client.set = AsyncMock(return_value=True)
    client.delete = AsyncMock(return_value=1)
    return client


@pytest.fixture
def mock_storage() -> MagicMock:
    """Мок хранилища S3 (StorageService) без реальных сетевых вызовов."""
    storage = MagicMock()
    storage.check_health = AsyncMock(return_value=True)
    storage.ensure_bucket_exists = AsyncMock(return_value=None)
    storage.upload_bytes = AsyncMock(return_value=None)
    storage.download_bytes = AsyncMock(return_value=b"%PDF-1.4 test document content")
    storage.generate_presigned_url = AsyncMock(
        return_value="http://localhost:9000/cleandoc-dev/temp/test.pdf?signature=valid"
    )
    return storage


@pytest.fixture
async def async_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Асинхронный тестовый клиент FastAPI с подмененной зависимостью get_db."""
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client

    app.dependency_overrides.clear()
```

### 11.3. Тесты проверки жизнеспособности (`backend/tests/test_health.py`)

```python
# backend/tests/test_health.py
from unittest.mock import AsyncMock, patch
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_liveness(async_client: AsyncClient) -> None:
    """Проверка liveness probe: эндпоинт всегда возвращает 200 OK."""
    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_readiness_all_healthy(async_client: AsyncClient) -> None:
    """Проверка readiness probe: когда БД, Redis и S3 доступны, возвращается 200 OK."""
    with (
        patch("app.api.v1.endpoints.health.get_redis_client") as mock_get_redis,
        patch("app.api.v1.endpoints.health.storage_service.check_health", new_callable=AsyncMock) as mock_s3_health,
    ):
        mock_redis = AsyncMock()
        mock_redis.ping.return_value = True
        mock_get_redis.return_value = mock_redis
        mock_s3_health.return_value = True

        response = await async_client.get("/api/v1/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["checks"]["database"] is True
        assert data["checks"]["redis"] is True
        assert data["checks"]["storage"] is True


@pytest.mark.asyncio
async def test_readiness_redis_down(async_client: AsyncClient) -> None:
    """Проверка readiness probe: сбой Redis приводит к статусу 503 Service Unavailable."""
    with (
        patch("app.api.v1.endpoints.health.get_redis_client") as mock_get_redis,
        patch("app.api.v1.endpoints.health.storage_service.check_health", new_callable=AsyncMock) as mock_s3_health,
    ):
        mock_redis = AsyncMock()
        mock_redis.ping.side_effect = ConnectionError("Redis unreachable")
        mock_get_redis.return_value = mock_redis
        mock_s3_health.return_value = True

        response = await async_client.get("/api/v1/ready")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["checks"]["redis"] is False
        assert data["checks"]["database"] is True


@pytest.mark.asyncio
async def test_readiness_storage_down(async_client: AsyncClient) -> None:
    """Проверка readiness probe: сбой S3 приводит к статусу 503 Service Unavailable."""
    with (
        patch("app.api.v1.endpoints.health.get_redis_client") as mock_get_redis,
        patch("app.api.v1.endpoints.health.storage_service.check_health", new_callable=AsyncMock) as mock_s3_health,
    ):
        mock_redis = AsyncMock()
        mock_redis.ping.return_value = True
        mock_get_redis.return_value = mock_redis
        mock_s3_health.return_value = False

        response = await async_client.get("/api/v1/ready")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["checks"]["storage"] is False
```

### 11.4. Тесты моделей БД и индексов (`backend/tests/test_database.py`)

```python
# backend/tests/test_database.py
from datetime import date, datetime, timedelta, timezone
from uuid import UUID
import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.invoice import B2BInvoice
from app.models.subscription import Subscription
from app.models.token import AppToken, RefreshToken
from app.models.usage import DailyUsage
from app.models.user import User


@pytest.mark.asyncio
async def test_user_creation_and_defaults(db_session: AsyncSession) -> None:
    """Проверяет создание пользователя, генерацию UUIDv4 и дефолтный тариф free."""
    user = User(
        email="client@clean-doc.local",
        telegram_id=987654321,
        telegram_username="test_client",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    assert isinstance(user.id, UUID)
    assert user.plan == "free"
    assert user.is_blocked is False
    assert user.magic_code_attempts == 0
    assert user.magic_code_hash is None
    assert isinstance(user.created_at, datetime)
    assert isinstance(user.updated_at, datetime)


@pytest.mark.asyncio
async def test_cascade_delete_user_related_records(db_session: AsyncSession) -> None:
    """Проверяет каскадное удаление токенов и записей использования при удалении пользователя."""
    user = User(email="cascade@clean-doc.local")
    db_session.add(user)
    await db_session.flush()

    token = RefreshToken(
        user_id=user.id,
        token_hash="dummy_refresh_hash_12345",
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    app_token = AppToken(
        user_id=user.id,
        name="1C-Integration",
        token_hash="dummy_app_hash_67890",
    )
    usage = DailyUsage(
        user_id=user.id,
        ip_subnet="192.168.1.0/24",
        usage_date=date.today(),
        conversion_count=1,
    )
    db_session.add_all([token, app_token, usage])
    await db_session.commit()

    # Удаляем пользователя
    await db_session.delete(user)
    await db_session.commit()

    # Проверяем каскадное удаление
    res_token = await db_session.scalar(select(RefreshToken).where(RefreshToken.user_id == user.id))
    res_app = await db_session.scalar(select(AppToken).where(AppToken.user_id == user.id))
    res_usage = await db_session.scalar(select(DailyUsage).where(DailyUsage.user_id == user.id))

    assert res_token is None
    assert res_app is None
    assert res_usage is None


@pytest.mark.asyncio
async def test_daily_usage_registered_user_constraint(db_session: AsyncSession) -> None:
    """Проверяет ограничение unique(user_id, usage_date) для авторизованных пользователей."""
    user = User(email="limit@clean-doc.local")
    db_session.add(user)
    await db_session.flush()

    today = date.today()
    usage1 = DailyUsage(user_id=user.id, ip_subnet="10.0.0.0/24", usage_date=today, conversion_count=1)
    db_session.add(usage1)
    await db_session.commit()

    usage2 = DailyUsage(user_id=user.id, ip_subnet="10.0.0.0/24", usage_date=today, conversion_count=2)
    db_session.add(usage2)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_daily_usage_guest_partial_indexes(db_session: AsyncSession) -> None:
    """Проверяет работу частичных уникальных индексов для анонимных пользователей."""
    today = date.today()

    # 1. Гость с fingerprint
    u_fp1 = DailyUsage(user_id=None, fingerprint="fp_abc", ip_subnet="1.1.1.0/24", usage_date=today)
    db_session.add(u_fp1)
    await db_session.commit()

    u_fp2_duplicate = DailyUsage(user_id=None, fingerprint="fp_abc", ip_subnet="1.1.1.0/24", usage_date=today)
    db_session.add(u_fp2_duplicate)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()

    # 2. Гость без fingerprint (фолбэк по ip_subnet)
    u_ip1 = DailyUsage(user_id=None, fingerprint=None, ip_subnet="2.2.2.0/24", usage_date=today)
    db_session.add(u_ip1)
    await db_session.commit()

    u_ip2_duplicate = DailyUsage(user_id=None, fingerprint=None, ip_subnet="2.2.2.0/24", usage_date=today)
    db_session.add(u_ip2_duplicate)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_subscription_check_constraints(db_session: AsyncSession) -> None:
    """Проверяет CHECK constraint на plan ('pro') и billing_period ('month', 'year')."""
    user = User(email="sub@clean-doc.local")
    db_session.add(user)
    await db_session.flush()

    # Валидная подписка
    sub_valid = Subscription(
        user_id=user.id,
        plan="pro",
        billing_period="month",
        status="active",
        amount_rub=1490,
        current_period_start=datetime.now(timezone.utc),
        current_period_end=datetime.now(timezone.utc) + timedelta(days=30),
    )
    db_session.add(sub_valid)
    await db_session.commit()

    # Невалидный план
    sub_invalid = Subscription(
        user_id=user.id,
        plan="enterprise_invalid",
        billing_period="month",
        status="active",
        amount_rub=5000,
        current_period_start=datetime.now(timezone.utc),
        current_period_end=datetime.now(timezone.utc) + timedelta(days=30),
    )
    db_session.add(sub_invalid)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()
```

### 11.5. Тесты сервиса хранилища (`backend/tests/test_storage.py`)

```python
# backend/tests/test_storage.py
from unittest.mock import MagicMock, patch
import pytest
from app.services.storage_service import StorageService


@pytest.mark.asyncio
async def test_storage_health_success() -> None:
    """Проверяет положительный результат проверки доступности S3."""
    storage = StorageService()
    with patch.object(storage._s3_client, "head_bucket", return_value={}):
        is_healthy = await storage.check_health()
        assert is_healthy is True


@pytest.mark.asyncio
async def test_storage_health_failure() -> None:
    """Проверяет корректную обработку недоступности бакета S3."""
    storage = StorageService()
    with patch.object(storage._s3_client, "head_bucket", side_effect=Exception("Connection refused")):
        is_healthy = await storage.check_health()
        assert is_healthy is False


@pytest.mark.asyncio
async def test_storage_upload_and_download_bytes() -> None:
    """Проверяет методы загрузки и скачивания бинарных данных."""
    storage = StorageService()
    test_data = b"%PDF-1.4 sample file content"
    test_key = "temp/test_job/input.pdf"

    mock_body = MagicMock()
    mock_body.read.return_value = test_data

    with (
        patch.object(storage._s3_client, "put_object", return_value={}) as mock_put,
        patch.object(storage._s3_client, "get_object", return_value={"Body": mock_body}) as mock_get,
    ):
        await storage.upload_bytes(test_data, test_key, content_type="application/pdf")
        mock_put.assert_called_once_with(
            Bucket=storage.bucket,
            Key=test_key,
            Body=test_data,
            ContentType="application/pdf",
        )

        downloaded = await storage.download_bytes(test_key)
        assert downloaded == test_data
        mock_get.assert_called_once_with(Bucket=storage.bucket, Key=test_key)


@pytest.mark.asyncio
async def test_storage_generate_presigned_url() -> None:
    """Проверяет формирование подписанной ссылки на скачивание."""
    storage = StorageService()
    expected_url = "https://s3.selcloud.ru/cleandoc-prod/temp/doc.docx?X-Amz-Signature=abc"
    test_key = "temp/test_job/result.docx"

    with patch.object(storage._s3_client, "generate_presigned_url", return_value=expected_url) as mock_presign:
        url = await storage.generate_presigned_url(test_key, expires_in_seconds=900)
        assert url == expected_url
        mock_presign.assert_called_once_with(
            "get_object",
            Params={"Bucket": storage.bucket, "Key": test_key},
            ExpiresIn=900,
        )
```

---

## 12. Порядок реализации Slice 0

Реализация фундамента ведется строго последовательно:

```text
Шаг 1: Конфигурация монорепозитория
  ├── pyproject.toml, package.json, Makefile, .gitignore, .markdownlint.yml, .env.example
  └── Инициализация зависимостей через uv sync и npm install

Шаг 2: Развертывание локальной инфраструктуры
  ├── deploy/docker-compose.yml (PostgreSQL 18, Redis 7.2, MinIO, Mailhog, api, worker)
  └── Проверка запуска контейнеров: make dev

Шаг 3: Ядро бэкенда и настройки
  ├── backend/app/core/config.py
  ├── backend/app/core/database.py
  ├── backend/app/core/redis.py
  └── backend/app/core/security.py

Шаг 4: Модели данных и миграция Alembic
  ├── backend/app/models/ (base, __init__, user, token, usage, subscription, invoice)
  ├── backend/alembic/ (alembic.ini, env.py, script.py.mako, versions/0001_initial_schema.py)
  └── Применение миграции к PostgreSQL: make migrate

Шаг 5: Сервис хранилища S3
  └── backend/app/services/storage_service.py

Шаг 6: Приложение FastAPI, роутер и служебные эндпоинты
  ├── backend/app/schemas/health.py
  ├── backend/app/api/v1/endpoints/health.py
  ├── backend/app/api/v1/router.py
  ├── backend/app/workers/worker.py (stub daemon)
  └── backend/app/main.py (lifespan, CORS, prometheus)

Шаг 7: Скелет клиентской части
  ├── frontend/tsconfig.json, postcss.config.js, tailwind.config.ts, globals.css
  ├── frontend/src/lib/api-client.ts
  └── frontend/src/app/layout.tsx, page.tsx, page.test.tsx

Шаг 8: Запуск тестового харнеса
  ├── backend/tests/ (conftest.py, test_health.py, test_database.py, test_storage.py)
  └── Запуск: make test-py

Шаг 9: Сквозная валидация качества
  └── Запуск make gate и достижение чистого вывода без ошибок
```

---

## 13. Плавное перетекание в Slice 1 (Slice 1 Seams & Extension Points)

Slice 0 спроектирован так, чтобы начало реализации Slice 1 (Processing) не требовало переделки фундамента. Архитектурные стыки (Seams) зафиксированы контрактами:

### 13.1. Стык базы данных (Database Seam)

В Slice 0 создается таблица `users` с первичным ключом `UUIDv4`.
В Slice 1 миграция `0002_conversion_jobs.py` объявляет таблицу `conversion_jobs`:

```sql
CREATE TABLE IF NOT EXISTS conversion_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,  -- Чистый FK на users(id) из Slice 0
    ...
);
CREATE INDEX idx_jobs_dedup ON conversion_jobs(user_id, sha256_checksum, usage_date)
    WHERE sha256_checksum IS NOT NULL AND status IN ('processing', 'completed');
```

- Модель `ConversionJob` в `backend/app/models/job.py` наследует `Base, UUIDPrimaryKeyMixin, TimestampMixin` из `app.models.base`.
- Обратная связь `user.jobs = relationship("ConversionJob", back_populates="user")` добавляется без изменения существующих полей `User`.

### 13.2. Стык фонового воркера (Worker Seam)

- В Slice 0 контейнер `cleandoc_worker` и `backend/Dockerfile.worker` уже настроены: они монтируют общий исходный код, подключены к сети `cleandoc_network` и зависят от `postgres`, `redis` и `minio`.
- В Slice 1 заглушка `backend/app/workers/worker.py` заменяется на полноценную точку входа RQ:
  - Инициализация и прогрев (warmup) тяжелых моделей `Docling` при старте процесса воркера.
  - Запуск `rq worker priority fast heavy --max-jobs=50`.
  - Модуль `backend/app/workers/tasks.py` реализует функции задач `parse_and_convert` и `render_preview`.

### 13.3. Стык хранилища S3 (Storage Seam)

- Сервис `backend/app/services/storage_service.py` из Slice 0 предоставляет все необходимые интерфейсы:
  - `upload_bytes(data, key, content_type)` — используется в `converter_service` для загрузки входящего PDF (`temp/{job_id}/input.pdf`) и воркером для сохранения результата (`temp/{job_id}/result.docx`).
  - `download_bytes(key)` — используется воркером для получения исходного PDF из S3 перед обработкой `qpdf` и `Docling`.
  - `generate_presigned_url(key, expires_in_seconds=900)` — используется в эндпоинте `GET /convert/jobs/{id}/download` для генерации временной ссылки со сроком жизни 15 минут.
- Не требуется написание нового клиента S3 в Slice 1 — сервис уже протестирован и готов к работе.

### 13.4. Стык очередей и SSE стриминга (Redis & SSE Seam)

- Модуль `backend/app/core/redis.py` предоставляет пул соединений `redis_pool` и фабрику `get_redis_client()`.
- В Slice 1:
  - Эндпоинт `POST /convert/upload` ставит задачи в очередь через `Queue(queue_name, connection=sync_redis)`.
  - Эндпоинт `GET /convert/jobs/{id}/stream` открывает асинхронную подписку `pubsub = redis_client.pubsub(); await pubsub.subscribe(f"job:{job_id}:progress")` и пересылает события клиенту в формате SSE с отправкой комментария `: keepalive` каждые 15 секунд.

### 13.5. Стык API маршрутизации (Router Seam)

- Модуль `backend/app/api/v1/router.py` содержит единую точку агрегации `api_v1_router`.
- В Slice 1 добавление всех эндпоинтов конвертации выполняется в одну строку:

```python
from app.api.v1.endpoints import convert
api_v1_router.include_router(convert.router, prefix="/convert", tags=["convert"])
```

### 13.6. Стык клиентского приложения (Frontend Seam)

- В Slice 0 развернут Next.js 14 с Tailwind CSS, Inter шрифтами и типизированным HTTP-клиентом `frontend/src/lib/api-client.ts`.
- В Slice 1 создаются:
  - Zustand-стор `useConverterStore.ts` для управления состоянием загрузки и прогресса.
  - Компоненты UI: `Dropzone` с валидацией Drag & Drop, `ProgressBar` и модальное окно превью `PreviewModal`.
  - Клиентский хук подписки на SSE стрим статуса.

---

## 14. Связанные документы

- [Single Source of Truth (`docs/TECH.md`)](./TECH.md) — полная техническая спецификация проекта.
- [Регламент разработки (`AGENTS.md`)](../AGENTS.md) — архитектурные правила, чеклисты и запреты.
- [Спецификация Slice 1: Processing (`docs/SLICE-01.md`)](./SLICE-01.md) — спецификация пайплайна конвертации PDF.
