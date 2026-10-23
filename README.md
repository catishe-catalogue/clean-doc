# Чистый документ

B2B микро-SaaS онлайн-конвертер PDF в Word и Excel с сохранением верстки и соответствием 152-ФЗ.

**Домен:** `clean-doc.ru` / `чистыйдокумент.рф`

## Быстрый старт

### Требования

- Docker Desktop
- Python 3.12+ и [uv](https://docs.astral.sh/uv/)
- Node.js 20+ и npm

### 1. Клонировать репозиторий и скопировать окружение

```bash
cp .env.example .env
```

### 2. Запустить локальный стек

```bash
make dev
```

Сервисы после запуска:

| Сервис | URL |
| :--- | :--- |
| API FastAPI | <http://localhost:8000/api/v1/docs> |
| MinIO Console | <http://localhost:9001> |
| Mailhog | <http://localhost:8025> |

### 3. Применить миграции базы данных

```bash
make migrate
```

### 4. Полная проверка качества (`make gate`)

```bash
make gate
```

## Команды Makefile

```bash
make help          # Вывести список всех команд
make dev           # Запустить локальный стек
make down          # Остановить контейнеры
make clean         # Остановить и удалить все тома
make migrate       # Применить миграции Alembic
make seed          # Наполнить тестовыми данными
make lint-py       # Линтинг Python (Ruff)
make format-py-fix # Автоисправление форматирования
make typecheck-py  # Проверка типов (mypy --strict)
make test-py       # Тесты Python (pytest)
make gate          # Полный пайплайн CI-качества
```

## Архитектура

```text
clean-doc/
  backend/   — FastAPI, SQLAlchemy 2.0, asyncpg, Redis, RQ
  frontend/  — Next.js 14, TypeScript, Tailwind CSS
  deploy/    — Docker Compose, Caddy
  docs/      — Техническая документация (TECH.md, SLICE-*.md)
  scripts/   — Вспомогательные скрипты
```

## Документация

- [TECH.md](docs/TECH.md) — Единый источник технической правды
- [AGENTS.md](AGENTS.md) — Регламент для AI-агентов разработки
- [SLICE-00.md](docs/SLICE-00.md) — Спецификация Foundation среза
