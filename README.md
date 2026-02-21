# Respond.io → Odoo | Event-Driven ETL Pipeline

A lightweight, containerized **event-driven ETL pipeline** that captures real-time contact events from Respond.io, transforms and validates the data, then loads it into Odoo CRM via XML-RPC — ensuring data consistency through idempotent upsert operations.

## Pipeline Architecture

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────────┐     ┌───────────────┐
│  Respond.io  │────▶│   FastAPI Ingest  │────▶│  Celery + Redis  │────▶│  Odoo CRM     │
│  (Source)    │     │  (Extract/Valid.) │     │  (Queue/Buffer)  │     │  (Load/Sink)  │
└─────────────┘     └──────────────────┘     └─────────────────┘     └───────────────┘
     Event               Extract &                Transform &             Load
    Trigger              Validate                  Enqueue              (Upsert)
```

## ETL Breakdown

| Stage | Description |
|-------|-------------|
| **Extract** | Webhook ingestion layer captures contact events from Respond.io in real-time |
| **Transform** | Pydantic schema validation, phone normalization (E.164), name concatenation, ID type coercion |
| **Load** | Idempotent upsert into Odoo `res.partner` model via XML-RPC, deduplicated by `x_studio_respondio_id` |

## Key Data Engineering Patterns

- **Event-Driven Ingestion** — Real-time webhook capture instead of batch polling
- **Schema Validation** — Pydantic models enforce data contracts at ingestion boundary
- **Async Task Queue** — Celery decouples ingestion from processing, preventing backpressure
- **Idempotent Loads** — Upsert logic ensures exactly-once semantics for contact records
- **Auto-Retry with Backoff** — Transient failures (network, timeout) retry 3x with exponential backoff
- **Data Transformation** — Phone number normalization (E.164), flexible payload parsing (3 formats)

## Project Structure

```
respondio_odoo/
├── app/
│   ├── config.py          # Centralized config via pydantic-settings
│   ├── schemas.py         # Data contracts (Pydantic models)
│   ├── transform.py       # Transformation layer (E.164 phone formatting)
│   ├── odoo_client.py     # Load layer (XML-RPC client with idempotent upsert)
│   ├── tasks.py           # Async orchestration (Celery tasks)
│   └── main.py            # Ingestion layer (FastAPI webhook receiver)
├── .env                   # Pipeline credentials (not tracked)
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## Quick Start

1. **Clone**
   ```bash
   git clone git@github.com:zidanlf/respondio_to_odoo.git
   cd respondio_to_odoo
   ```

2. **Configure credentials** — create `.env`:
   ```env
   ODOO_URL=https://otca.odoo.com
   ODOO_DB=otca
   ODOO_USERNAME=your_username
   ODOO_API_KEY=your_api_key
   REDIS_URL=redis://redis:6379/0
   ```

3. **Deploy**
   ```bash
   docker-compose up --build -d
   ```

4. **Verify pipeline health**
   ```bash
   curl http://localhost:8000/health
   ```

## Sample Event Payload

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

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Ingestion | FastAPI 0.109 |
| Queue / Buffer | Celery 5.3 + Redis 7 |
| Validation | Pydantic v2 + pydantic-settings |
| Load | Odoo XML-RPC API |
| Containerization | Docker Compose |
| Runtime | Python 3.10 |

## License

MIT
