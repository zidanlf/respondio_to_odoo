# Respond.io → Odoo Contact Sync Bridge

Lean containerized Python bridge to sync Respond.io contacts into Odoo SaaS (OTCA) via webhook — powered by FastAPI, Celery, and XML-RPC.

## Architecture

```
Respond.io Webhook → FastAPI → Celery (Redis) → OdooClient (XML-RPC) → Odoo SaaS
```

## Features

- **Webhook Receiver** — Accepts Respond.io contact payloads (flat, nested, or root-level)
- **Pydantic Validation** — Strict schema validation with automatic integer-to-string ID coercion
- **Celery Task Queue** — Async processing with auto-retry (3x, exponential backoff)
- **Idempotent Upsert** — Deduplication via `x_studio_respondio_id` field in Odoo
- **Phone Formatting** — Auto-normalizes phone numbers to E.164 format
- **Health Check** — `/health` endpoint for Docker readiness probes

## Project Structure

```
respondio_odoo/
├── app/
│   ├── __init__.py        # Package marker
│   ├── config.py          # pydantic-settings (env loading)
│   ├── schemas.py         # Pydantic models for webhook payload
│   ├── transform.py       # Phone → E.164 formatting
│   ├── odoo_client.py     # Class-based XML-RPC client
│   ├── tasks.py           # Celery tasks (auto-retry)
│   └── main.py            # FastAPI entry point
├── .env                   # Credentials (not tracked by git)
├── .gitignore
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## Setup

1. **Clone the repo**
   ```bash
   git clone git@github.com:zidanlf/respondio_to_odoo.git
   cd respondio_to_odoo
   ```

2. **Create `.env`** file in the project root:
   ```env
   ODOO_URL=https://otca.odoo.com
   ODOO_DB=otca
   ODOO_USERNAME=your_username
   ODOO_API_KEY=your_api_key
   REDIS_URL=redis://redis:6379/0
   ```

3. **Run with Docker Compose**
   ```bash
   docker-compose up --build -d
   ```

4. **Verify**
   ```bash
   curl http://localhost:8000/health
   ```

## Usage

### Webhook Endpoint

```
POST /webhook
Content-Type: application/json
```

### Sample Payload

```json
{
  "contact": {
    "id": 1,
    "firstName": "John",
    "lastName": "Doe",
    "phone": "+628123456789"
  },
  "event_type": "contact.created"
}
```

### Test

```bash
curl -X POST http://localhost:8000/webhook \
     -H "Content-Type: application/json" \
     -d '{"id":"test_001","firstName":"John","lastName":"Doe","phoneNumber":"+628123456789"}'
```

## Tech Stack

| Component | Technology |
|-----------|-----------|
| API | FastAPI 0.109 |
| Task Queue | Celery 5.3 + Redis 7 |
| Validation | Pydantic + pydantic-settings |
| Odoo API | XML-RPC |
| Container | Docker Compose |
| Runtime | Python 3.10 |

## License

MIT
