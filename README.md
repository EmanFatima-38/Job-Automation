# ApplyPilot

Job discovery and application tracking with CV and portfolio based search planning,
structured vacancy enrichment, matching, and optional opportunity notifications.

## Stack

- Backend: FastAPI, PostgreSQL, SQLAlchemy/Alembic, APScheduler, NVIDIA LLM API, Playwright.
- Frontend: Next.js, TypeScript, Tailwind, React Query.
- Discovery: existing job boards and company adapters, plus Tavily web vacancy search.

## Local development (PowerShell)

Preserve existing `.env` files, JWT secrets, encryption keys, and database volumes.
For a new installation, copy the example environment files and configure them first.
NVIDIA credentials enable AI extraction and matching; Tavily enables general web
search. An email encryption key is required by the backend configuration.

From the project directory, start the database:

```powershell
docker compose up -d postgres
```

Back up any existing database before applying migrations. Then, from `backend`:

```powershell
# Create a virtual environment only if one does not already exist.
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe -m playwright install chromium
.\venv\Scripts\python.exe -m alembic upgrade head
.\venv\Scripts\python.exe -m uvicorn app.main:app --port 8010
```

From `frontend`:

```powershell
npm ci
npm run dev -- --port 3010
```

Set backend `CORS_ORIGINS=http://localhost:3010` and frontend
`NEXT_PUBLIC_API_URL=http://localhost:8010/api/v1`.
Backend API documentation: http://localhost:8010/docs
Frontend: http://localhost:3010

The additive discovery migration is `b7c8d9e0f123`. See `UPGRADE.md` for the
implementation, verification results, and deployment limitations. Starting the
backend also starts scheduled work, including existing opted-in email follow-ups.

## Checks

From `backend`: `.\venv\Scripts\python.exe -m unittest discover -s tests -q`.
From `frontend`: `npm run lint`, `npx tsc --noEmit`, and `npm run build`.
Live and paid integration tests are opt-in; ordinary tests mock external services.
