# ORACLE API

FastAPI service for infrastructure inventory, dependency topology, deterministic failure simulations, telemetry samples and audit events.

## Run locally

```bash
pip install -e ".[dev]"
alembic upgrade head
uvicorn oracle_api.main:app --reload
```

API documentation: http://127.0.0.1:8000/docs

## Main endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | /health | Service health |
| POST/GET | /api/v1/nodes | Infrastructure components |
| POST/GET | /api/v1/edges | Directed dependency edges |
| GET | /api/v1/topology | Graph snapshot (nodes and edges) |
| POST | /api/v1/scenarios/compare | Compare impacted components and impact-score deltas across two failure scenarios |
| POST | /api/v1/ai/explain | Generate an optional DeepSeek explanation for a saved simulation |
| POST/GET | /api/v1/simulations, /api/v1/simulations/{id} | Failure impact simulations and result retrieval |
| POST/GET | /api/v1/telemetry | Ingest and query metric samples |
| GET | /api/v1/audit | Query audit events |

## Telemetry ingestion

Set ORACLE_API_KEYS to a semicolon-separated list of API credentials in the format token|tenant-id|role. Supported roles are viewer, operator, admin and ingestor. Send the token with X-API-Key or Authorization: Bearer. The tenant is taken from the credential; an optional X-Tenant-ID must match it. A credential cannot select another tenant.

Viewer: read inventory/topology, simulations and telemetry. Operator: viewer access plus inventory changes, simulations, scenario comparison and AI explanation. Ingestor: read access plus telemetry ingestion. Admin: all operations including audit events.

In development/test mode only, when ORACLE_API_KEYS is empty, requests are treated as an admin in the tenant supplied by X-Tenant-ID (or default). In production, ORACLE_API_KEYS is mandatory and the API refuses to start without it. Do not use development mode on a public deployment.

Run alembic upgrade head before starting the service. The migration assigns existing legacy records to tenant default, then enables tenant-local node names and dependency uniqueness.

## Optional DeepSeek assistance

Set DEEPSEEK_API_KEY, and explicitly set AI_DATA_SHARING_ENABLED=true to permit sending the selected saved simulation result to DeepSeek. The integration uses DEEPSEEK_BASE_URL (default https://api.deepseek.com), DEEPSEEK_MODEL (default deepseek-flash) and a configurable timeout. Without the opt-in flag, the endpoint returns 403 and sends no data. Review the data-sharing implications before enabling this feature.

## Validation

```bash
pytest
ruff check .
```
