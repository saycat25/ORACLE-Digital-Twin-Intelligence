# ORACLE API

FastAPI service for infrastructure inventory, dependency topology, deterministic failure simulations, telemetry samples and audit events.

## Run locally

```bash
pip install -e ".[dev]"
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

Set INGESTION_API_KEY to a strong secret to require an X-API-Key header for telemetry writes. Set X-Tenant-ID to label audit and telemetry records; the default is default.

**Important:** tenant labels do not yet isolate nodes, edges or simulations. This release does not provide enterprise authentication, SSO or RBAC. Do not expose it as a multi-tenant service.

## Optional DeepSeek assistance

Set DEEPSEEK_API_KEY, and explicitly set AI_DATA_SHARING_ENABLED=true to permit sending the selected saved simulation result to DeepSeek. The integration uses DEEPSEEK_BASE_URL (default https://api.deepseek.com), DEEPSEEK_MODEL (default deepseek-flash) and a configurable timeout. Without the opt-in flag, the endpoint returns 403 and sends no data. Review the data-sharing implications before enabling this feature.

## Validation

```bash
pytest
ruff check .
```
