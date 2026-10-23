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

### 4. Запустить фоновый воркер RQ (при локальной разработке)

```bash
make worker
```

Воркер выполняет превентивный разогрев (warmup) моделей и слушает очереди `priority`, `fast`, `heavy`.

### 5. Полная проверка качества (`make gate`)

```bash
make gate
```

## API конвертации (Slice 1: Processing)

| Метод | Эндпоинт | Описание |
| :--- | :--- | :--- |
| `POST` | `/api/v1/convert/upload` | Прием PDF, проверка Magic Bytes, дедупликация, лимиты, сохранение в S3 и постановка в RQ (`202 Accepted`) |
| `GET` | `/api/v1/convert/jobs/{id}` | Polling fallback: моментальный снимок задачи (статус, прогресс, ссылки на превью) |
| `GET` | `/api/v1/convert/jobs/{id}/stream` | Server-Sent Events (SSE) стриминг прогресса с keepalive-комментариями каждые 15 сек |
| `GET` | `/api/v1/convert/jobs/{id}/download` | Выдача временного S3 pre-signed URL на скачивание (`307 Temporary Redirect`, TTL 15 минут) |

## Команды Makefile

```bash
make help          # Вывести список всех команд
make dev           # Запустить локальный стек в Docker
make down          # Остановить контейнеры
make clean         # Остановить и удалить все тома
make migrate       # Применить миграции Alembic
make seed          # Наполнить тестовыми данными
make worker        # Запустить воркер RQ локально
make lint-md       # Проверить markdown документацию
make lint-py       # Линтинг Python (Ruff)
make format-py-fix # Автоисправление форматирования Python
make typecheck-py  # Строгая проверка типов Python (mypy --strict)
make test-py       # Тесты Python (pytest)
make gate          # Полный пайплайн CI-качества перед коммитом
```

## Архитектура

```text
clean-doc/
  backend/   — FastAPI, SQLAlchemy 2.0, asyncpg, Redis, RQ, PyMuPDF, S3
  frontend/  — Next.js 14, TypeScript, Tailwind CSS
  deploy/    — Docker Compose, Caddy v2
  docs/      — Техническая документация (TECH.md, SLICE-*.md)
  scripts/   — Вспомогательные скрипты
```

## Соответствие 152-ФЗ и безопасность

- **Шифрование при хранении:** все объекты в S3 шифруются по алгоритму `AES256` (`ServerSideEncryption="AES256"`).
- **Срок жизни данных:** временные файлы и задачи автоматически удаляются через 2 часа (`expires_at = now() + 2 hours`).
- **Защита от утечек:** в логи не попадают персональные данные, имена клиентских файлов и содержимое документов (только UUID, размер в байтах и время обработки).
- **Безопасное скачивание:** скачивание доступно только автору задачи (по пользователю или криптографической cookie-сессии гостя). Документы отдаются через pre-signed URL со сроком жизни не более 15 минут.

## Документация

- [TECH.md](docs/TECH.md) — Единый источник технической правды
- [AGENTS.md](AGENTS.md) — Регламент для AI-агентов разработки
- [SLICE-00.md](docs/SLICE-00.md) — Спецификация Foundation среза
- [SLICE-01.md](docs/SLICE-01.md) — Спецификация Processing среза
