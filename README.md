# Ledgerly AI

AI-native invoice-to-pay automation for mid-market finance teams: upload an invoice, OCR + Claude extract its fields, a deterministic three-way match engine checks it against PO/GRN data from your ERP, and exceptions route to the right human with a plain-language explanation of what's wrong.

## How it works

1. **Ingest** — an invoice (PDF/image) is uploaded to object storage and queued for processing.
2. **Extract** — Tesseract OCR reads the document locally; only the extracted *text* (never the raw image) is sent to Claude to structure into fields. If no API key is configured, the invoice is held in `needs_review` instead of failing.
3. **Match** — a deterministic engine checks price/quantity against configurable tolerances, flags duplicates, and pulls PO/GRN data from whichever ERP connector the tenant has configured (Dynamics 365 Business Central today; Oracle/Odoo/ERPNext/SAP/NetSuite stubbed as "coming soon").
4. **Resolve** — exceptions get a Claude-generated plain-language explanation and route to a bookkeeper/accountant/approver based on role and a value threshold, with an audit trail of every system and human action.

## Stack

- **Backend:** FastAPI (Python), Celery + Redis for async OCR/matching, SQLAlchemy/Alembic over Postgres
- **Frontend:** React + TypeScript + Vite, TanStack Query, Tailwind
- **Auth:** self-hosted Keycloak (OIDC), multi-tenant via a `tenant_id` JWT claim
- **Storage:** MinIO (S3-compatible)
- **AI:** Anthropic Claude, for field extraction and exception explanations

## Local development

Requires Docker and Docker Compose.

```bash
cp .env.example .env
# fill in POSTGRES_PASSWORD, MINIO_ROOT_PASSWORD, KEYCLOAK_ADMIN_PASSWORD,
# SECRETS_ENCRYPTION_KEY (see the comment in .env.example for how to generate it),
# and ANTHROPIC_API_KEY if you want real extraction instead of needs_review fallback

docker compose up --build
```

This starts Postgres, Redis, MinIO, Keycloak, the backend API, a Celery worker, the frontend dev server, and Mailhog (catches outgoing email locally), plus a disposable Odoo instance used to validate the three-way-match flow against a real ERP.

| Service | URL |
|---|---|
| Frontend | http://localhost:5174 |
| Backend API | http://localhost:8000 |
| Keycloak | http://localhost:8081 |
| MinIO console | http://localhost:9001 |
| Mailhog | http://localhost:8025 |
| Odoo (test ERP) | http://localhost:8069 |

## Production deployment

`docker-compose.prod.yml` runs the same services single-origin behind a reverse proxy, with no source bind-mounts and no dev-mode flags:

- `/api/*` → backend
- `/auth/*` → Keycloak (`KC_HTTP_RELATIVE_PATH=/auth`)
- `/<bucket-name>/*` → MinIO (path-style, matches its own presigned-URL addressing)
- everything else → the built frontend, served as static files by Caddy

The frontend's `VITE_*` values are baked in at build time via Docker build args (`frontend/Dockerfile.prod`) since Vite inlines them into the bundle. The Odoo test fixture is intentionally left out of the production stack. `infra/keycloak/realm-export.prod.json` is the one-time realm import for a fresh deployment — import it once via `docker compose run --rm keycloak start --import-realm`, then run the service permanently with the default `start` (no `--import-realm`), since re-importing on every restart wipes users.

## Repository layout

```
backend/    FastAPI app, Celery workers, ERP connectors, DB migrations
frontend/   React app (Vite)
infra/      Keycloak realm exports, Postgres init scripts
```
