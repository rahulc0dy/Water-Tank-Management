# Water Tank Backend

Minimal FastAPI backend designed for a Raspberry Pi to expose Arduino telemetry.

The `automation.py` script streams readings from the Arduino, persists them to
`var/telemetry.json`, and this service serves the stored data to your Next.js
dashboard.

## Quick start (uv)

```bash
# From the backend/ directory
uv sync
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Alternative (pip)

```bash
# From the backend/ directory
python -m venv .venv
source .venv/bin/activate  # PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Environment variables

- `WATERTANK_DATA_FILE` – JSON file path for telemetry history (default `backend/var/telemetry.json`).
- `WATERTANK_HISTORY_SIZE` – limit of telemetry samples to keep (set `0` for unlimited history).
- `WATERTANK_DB_FILE` – SQLite file path for auth data (default `backend/var/app.db`).
- `WATERTANK_CAPACITY_LITERS` – optional tank capacity to translate usage percent into litres.
- `WATERTANK_DEFAULT_USER` / `WATERTANK_DEFAULT_PASSWORD` – optional credentials to auto-create an initial user at startup.

### Authentication

Dashboard and telemetry endpoints require HTTP Basic authentication. Create a user via:

```bash
curl -X POST http://localhost:8000/auth/register \
	-H "Content-Type: application/json" \
	-d '{"username":"admin","password":"strongpass"}'
```

Subsequent requests must include the `Authorization: Basic ...` header. The `/auth/login`
endpoint is available for simple credential checks.

### API overview

- `GET /health` – quick status including telemetry file and database paths.
- `POST /auth/register` – create a new dashboard user.
- `POST /auth/login` – validate credentials.
- `GET /telemetry/latest` – most recent telemetry reading.
- `GET /telemetry/history?limit=100` – historical readings (default unlimited).
- `POST /telemetry/ingest` – manual telemetry ingestion (authenticated).
- `GET /dashboard/metrics` – aggregated usage (past 24h, all-time, hourly/day breakdown, latest status).
