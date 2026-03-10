# AutoAdService

Сервис сбора автообъявлений с API, SPA и Telegram‑ботом.

## Быстрый старт

1. Скопируйте пример окружения:

```bash
cp .env.example .env
```

2. Укажите ключи для бота и LLM в `.env`:

- `TELEGRAM_BOT_TOKEN`
- `OPENAI_API_KEY`
- `OPENAI_BASE_URL` (если используете совместимый OpenAI API, например `https://vedai.by/api/v1`)

3. Запуск:

```bash
docker-compose up --build
```

Если команда `docker-compose` не доступна, используйте:

```bash
docker compose up --build
```

## Доступы

- Backend API: `http://localhost:3000`
- Frontend: `http://localhost:3001`
- Админ (по умолчанию):
  - email: `admin@example.com`
  - password: `admin123`

## API

- `POST /api/login` → `{ access_token }`
- `GET /api/cars` → защищённый список авто (JWT)

Пример запроса:

```bash
curl -X POST http://localhost:3000/api/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@example.com","password":"admin123"}'
```

## Архитектура

- `backend` — FastAPI + Alembic + JWT.
- `worker` — Python‑воркер парсинга `carsensor.net` с retry и upsert по `url`.
- `frontend` — Next.js SPA (логин + таблица авто).
- `bot` — Python Telegram бот с function calling (OpenAI) для фильтрации.
- `db` — PostgreSQL.

## Примечания

- Парсер использует HTML‑разметку и может требовать подстройки селекторов под фактическую структуру `carsensor.net`.
- Админ создаётся автоматически при старте backend на основе `.env`.
- Если нет доступа к LLM, укажите это в `.env` или запросите ключ.
  
Если `carsensor.net` отдаёт 404, проверьте `CARSENSOR_URL` и `CARSENSOR_LIST_URL` в `.env` (по умолчанию используется `https://www.carsensor.net`).
