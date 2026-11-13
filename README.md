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

Проект поддерживает **два режима запуска** приложения с удобным и понятным переключением:

#### Режим быстрой разработки (Fast Local Dev Mode) — Рекомендуется для разработки фич

```bash
make dev-fast
```

- Включается флагом `DEV_FAST_MODE=true` в файле `.env` или переменной окружения.
- Автоматически авторизует пользователя `catishe@gmail.com` с тарифом **PRO**.
- Отключает рутинные шаги ввода email, перехода в Mailhog за кодом подтверждения и оплаты.
- Снимает лимит 2 страниц: многостраничные документы конвертируются целиком без апселл-блокировки.
- Лимит размера файла расширен до 100 МБ, задачи сразу направляются в очередь `priority`.
- Скачивание готового файла работает напрямую без ошибок авторизации `403 ACCESS_DENIED`.

#### Реалистичный Production-режим (Production Simulation Mode) — Для проверки полного бизнес-цикла

```bash
make dev-prod
```

- Включается флагом `DEV_FAST_MODE=false` в файле `.env`.
- Полная эмуляция реального окружения: анонимный пользователь с ограничением в 2 страницы превью при объеме > 2 стр.
- Проверка суточных лимитов (1 конвертация для анонима, 3 для зарегистрированного Free-тарифа).
- Доставка одноразового 6-значного OTP-кода и ссылки Magic Link в веб-интерфейс Mailhog (<http://localhost:8025>).
- Апселл-модалка при попытке скачать полный многостраничный документ с предложением перейти на PRO-тариф.

Обычная команда `make dev` запускает стек с текущим значением `DEV_FAST_MODE` из файла `.env`.

Сервисы после запуска:

| Сервис | URL |
| :--- | :--- |
| Веб-интерфейс | <http://localhost:3000> |
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

## API аутентификации (Slice 2: Auth & UX)

| Метод | Эндпоинт | Описание |
| :--- | :--- | :--- |
| `POST` | `/api/v1/auth/magic-link` | Запрос 6-значного OTP кода и ссылки Magic Link на email |
| `POST` | `/api/v1/auth/verify-code` | Проверка OTP кода, выдача JWT и установка HttpOnly cookie |
| `POST` | `/api/v1/auth/telegram` | Аутентификация через Telegram Login Widget |
| `POST` | `/api/v1/auth/refresh` | Ротация refresh токена из cookie и обновление access токена |
| `POST` | `/api/v1/auth/logout` | Отзыв сессии в базе данных и очистка cookie |
| `GET` | `/api/v1/auth/me` | Данные текущего пользователя, тариф и остаток суточных конвертаций |

## API биллинга и B2B счетов (Slice 3: Billing & B2B)

| Метод | Эндпоинт | Описание |
| :--- | :--- | :--- |
| `GET` | `/api/v1/billing/plans` | Тарифная сетка с ценами и доступными периодами подписки |
| `POST` | `/api/v1/billing/create-checkout` | Инициализация платежа ЮKassa (карты/СБП) для физлиц и ИП |
| `POST` | `/api/v1/billing/webhook/yukassa` | Идемпотентная обработка вебхуков `payment.succeeded` от ЮKassa |
| `POST` | `/api/v1/billing/invoices/create` | Выставление официального B2B-счета с автозаполнением реквизитов по ИНН через DaData |
| `GET` | `/api/v1/billing/invoices/{id}/pdf` | Скачивание сгенерированного PDF-счета с факсимиле |
| `POST` | `/api/v1/billing/cancel-subscription` | Отмена автопродления активной подписки |

## Предпросмотр превью и скачивание файлов

1. **Предпросмотр превью первых страниц:**
   - Превью страниц генерируются воркером через `PyMuPDF` (150 DPI) и сохраняются в S3 по ключам `temp/<job_id>/preview_p1.jpg`.
   - Фронтенд обращается по пути `/temp/<job_id>/preview_p1.jpg`, который маршрутизируется через Route Handler Next.js 14 (`frontend/src/app/temp/[...path]/route.ts`) и бэкенд-эндпоинт `/api/v1/convert/preview/{path}` с отдачей `image/jpeg` и заголовками кэширования.
2. **Скачивание готовых результатов без ошибки 403:**
   - Эндпоинт `/api/v1/convert/jobs/{id}/download` принимает токен авторизации как через заголовок `Authorization: Bearer`, так и через Query-параметр `?token=...` и cookie `refresh_token`, что предотвращает ошибку `403 ACCESS_DENIED` при стандартном переходе по ссылке в браузере.
   - В dev-окружении файл отдается напрямую потоком через `StreamingResponse`, исключая ошибки несовпадения Docker-хостов `minio:9000` и `localhost:9000` (`SignatureDoesNotMatch`).

## Тестовые данные (`mock_data/`)

В директории `mock_data/` подготовлены эталонные PDF-документы для всестороннего тестирования бизнес-логики:

| Файл | Объем | Назначение |
| :--- | :--- | :--- |
| `test-data-memo.pdf` | 90 КБ, 1 стр. | Служебная записка. Укладывается в лимит анонимного и Free тарифа, быстрая очередь `fast`. |
| `test-data-resume.pdf` | 400 КБ, 3 стр. | Резюме на 3 страницах. В Production-режиме генерирует 2 страницы превью и требует перехода на PRO. |
| `test-data-report.pdf` | 22.9 МБ, скан | Большой отчет. Проверяет блокировку превышения Free-лимита 10 МБ и обработку в очереди `heavy`. |
| `test-data-contract.pdf` | 24.2 МБ, договор | Длинный контракт. Проверяет многостраничный парсинг, проверку целостности `qpdf` и B2B сценарии. |

## Команды Makefile

```bash
make help          # Вывести список всех команд
make dev           # Запустить локальный стек в Docker
make dev-fast      # Запустить стек в режиме быстрой разработки (DEV_FAST_MODE=true)
make dev-prod      # Запустить стек в реалистичном Production-режиме (DEV_FAST_MODE=false)
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
  backend/   — FastAPI, SQLAlchemy 2.0, asyncpg, Redis, RQ, PyMuPDF, S3, ЮKassa, DaData
  frontend/  — Next.js 14, TypeScript, Tailwind CSS, shadcn/ui
  deploy/    — Docker Compose, Caddy v2
  docs/      — Техническая документация (TECH.md, SLICE-*.md)
  mock_data/ — Набор эталонных PDF-файлов для тестирования
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
- [SLICE-02.md](docs/SLICE-02.md) — Спецификация Auth & UX среза
- [SLICE-03.md](docs/SLICE-03.md) — Спецификация Billing & B2B среза
